#!/usr/bin/env python3
"""Offline, occurrence-aware rewrite coverage for UTF-8 text and Markdown."""
import os, re, sys, tempfile
import argparse
import bisect
from collections import Counter, defaultdict
import html
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

PUNCT = re.compile(r"[\s*＋+：:～~「」『』\"“”（）()【】\[\]、，,。.／/·⭐⚠️✅❌〔〕=＝→>＞<＜|｜~\-`_]")
TAGS = ("[renamed]", "[merged]", "[restored]", "[dropped]")
ROWNUM = re.compile(r"^(\d{1,4})[.)]?$")           # a count cell: 1, 2., 3)


def norm(s):
    return PUNCT.sub("", s).lower()


def items(old, min_len):
    out = {}
    for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", old, re.M):
        out.setdefault(m.group(1).strip(), "heading")
    for m in re.finditer(r"\*\*(.+?)\*\*", old):
        out.setdefault(m.group(1).strip(), "bold")
    for block in table_blocks(old):
        rows = [[c.strip().strip("*_` ") for c in line.strip().strip("|").split("|")] for line in block]
        sep = next((i for i, r in enumerate(rows) if all(set(c) <= set("-: ") for c in r)), None)
        body = rows[sep + 1:] if sep is not None else rows
        skip = counts_rows(body)                         # the first column is 1, 2, 3 …: compare the next cell instead
        for i, cells in enumerate(rows):
            if i == sep:
                continue
            cell = cells[1] if skip and len(cells) > 1 else cells[0]
            if cell and not set(cell) <= set("-: "):
                out.setdefault(cell, "table-cell")
    return {k: v for k, v in out.items() if len(norm(k)) >= max(2, min_len)}


def table_blocks(text):
    """Runs of consecutive lines that start with a pipe and hold a second one."""
    block = []
    for line in text.splitlines() + [""]:
        if re.match(r"^\|[^|]*\|", line):
            block.append(line)
        elif block:
            yield block
            block = []


def counts_rows(body):
    """True when every body row starts with a number and the numbers count up by one from 0 or 1."""
    nums = []
    for cells in body:
        m = ROWNUM.match(cells[0]) if cells else None
        if not m:
            return False
        nums.append(int(m.group(1)))
    return bool(nums) and nums[0] in (0, 1) and all(b == a + 1 for a, b in zip(nums, nums[1:]))


def structure(text):
    return {"headings": len(re.findall(r"^#{1,6} ", text, re.M)), "table_rows": len(re.findall(r"^\|", text, re.M)),
            "quote_lines": len(re.findall(r"^> ", text, re.M)), "chars": len(re.sub(r"\s", "", text))}


def coverage(old, new, min_len=3):
    its = items(old, min_len)
    nn = norm(new)
    unaccounted = [(k, kind) for k, kind in its.items() if norm(k) not in nn]
    return its, unaccounted, structure(old), structure(new)


def ledger_verdicts(ledger_text):
    v = {}
    for line in ledger_text.splitlines():
        for t in TAGS:
            if t in line:
                key = line.split(t)[0].strip(" -*|`")
                v[norm(key)] = t
    return v


def legacy_report(old_p, new_p, min_len=3, ledger_p=None, out_p=None):
    if os.path.realpath(old_p) == os.path.realpath(new_p):
        return 2, ["old and new are the same file — nothing to compare (a 100% result here would be meaningless)"]
    old, new = open(old_p, encoding="utf-8").read(), open(new_p, encoding="utf-8").read()
    if not old.strip() or not new.strip():
        return 2, ["one of the files is empty"]
    ledger_text = open(ledger_p, encoding="utf-8").read() if ledger_p else None
    return legacy_text_report(old, new, min_len, ledger_text, out_p)


def legacy_text_report(old, new, min_len=3, ledger_text=None, out_p=None):
    """The original structural stdout, also included verbatim by the new CLI."""
    its, un, so, sn = coverage(old, new, min_len)
    lines = [f"old: {len(its)} item{'' if len(its) == 1 else 's'} (headings, bold terms, table cells) · unaccounted in new: {len(un)}"]
    lines.append("structure  " + "  ".join(f"{k} {so[k]}→{sn[k]}" for k in so))
    ratio = sn["chars"] / max(1, so["chars"])
    if ratio < 0.6:
        lines.append(f"⚠️ new text has {ratio:.0%} of the old characters — check for truncation before anything else")
    if sn["headings"] == 0 and so["headings"] > 2:
        lines.append("⚠️ new text has no headings while the old had several — a term dump keeps words and loses structure")
    verdicts = ledger_verdicts(ledger_text) if ledger_text is not None else {}
    missing_verdict = []
    for k, kind in un:
        tag = verdicts.get(norm(k))
        lines.append(f"  {tag or '[      ]'} {kind:<10} {k}")
        if tag is None:
            missing_verdict.append(k)
    if out_p:
        open(out_p, "w", encoding="utf-8").write("\n".join(f"- {k}  ({kind})  [ ]" for k, kind in un) + "\n")
    if not un:
        lines.append("✔ every old item occurs in the new text (this does not prove nothing was lost: see the hints and the ledger rule)")
        return 0, lines
    if ledger_text is not None and not missing_verdict:
        lines.append(f"✔ all {len(un)} unaccounted items have a ledger verdict")
        return 0, lines
    lines.append(f"✘ {len(missing_verdict) if ledger_text is not None else len(un)} unaccounted item(s) without a verdict — decide each: {', '.join(TAGS)}")
    return 1, lines


OLD = """# Title
## Setup
The **frobnicator** needs a **cold start** every time.
## Results
| metric | value |
|---|---|
| latency | 3 ms |
| **throughput** | 9 |
> quoted line
## Caveats
Only on **weekdays**.
"""
NUMBERED_OLD = """## Rules
| # | Rule | Why |
|---|---|---|
| 1 | Keep one token file | cheapest consistency |
| 2 | Totals are computed on the page | a typed total can drift |
"""
NUMBERED_NEW = NUMBERED_OLD.replace("Totals are computed on the page", "Totals may be typed in")
NO_TRAILING_PIPE = "| name | value\n|---|---\n| latency | 3 ms\n"
CODES_OLD = "| code | meaning |\n|---|---|\n| 200 | OK |\n| 404 | Not found |\n"
CODES_NEW = "| code | meaning |\n|---|---|\n| 404 | Not found |\n"

NEW = """# Title
## Setup
The frobnicator needs a cold start every time.
## Results
| metric | value |
|---|---|
| latency | 3 ms |
> quoted line
"""


def legacy_selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as d:
        o, n, l = os.path.join(d, "old.md"), os.path.join(d, "new.md"), os.path.join(d, "ledger.md")
        open(o, "w").write(OLD); open(n, "w").write(NEW)
        its, un, so, sn = coverage(OLD, NEW)
        names = {k for k, _ in un}
        chk(names == {"Caveats", "throughput", "weekdays"}, f"unaccounted = Caveats (heading), throughput (table cell), weekdays (bold): {sorted(names)}")
        chk("frobnicator" not in names, "a term that lost its bold but is still present is accounted")
        rc, out = legacy_report(o, n)
        chk(rc == 1 and any("without a verdict" in x for x in out), "no ledger → exit 1 with the list")
        open(l, "w").write("- Caveats [merged] into Setup\n- throughput [dropped] duplicate of a chart\n- weekdays [restored]\n")
        rc, out = legacy_report(o, n, ledger_p=l)
        chk(rc == 0 and any("all 3 unaccounted items have a ledger verdict" in x for x in out), "complete ledger → exit 0")
        open(l, "w").write("- Caveats [merged]\n- weekdays [restored]\n")
        rc, out = legacy_report(o, n, ledger_p=l)
        chk(rc == 1 and any("1 unaccounted item(s) without a verdict" in x for x in out), "ledger missing one verdict → exit 1 naming the count")
        open(n, "w").write(OLD)
        rc, out = legacy_report(o, n)
        chk(rc == 0 and any(x.startswith("✔ every old item") for x in out), "identical content → exit 0 (with the caveat printed)")
        open(n, "w").write(OLD[:len(OLD) // 3])
        rc, out = legacy_report(o, n)
        chk(any("truncation" in x for x in out), "a much shorter new file prints the truncation hint")
        open(n, "w").write("Title Setup Results Caveats frobnicator cold start metric latency throughput weekdays quoted line " * 3 + "\n")
        rc, out = legacy_report(o, n)
        chk(rc == 0 and any("term dump" in x for x in out), "a term dump passes the existence test but prints the structure hint (the known limit)")
        rc, out = legacy_report(o, o)
        chk(rc == 2, "old == new file → exit 2 (a meaningless 100%)")
        its2, un2, _, _ = coverage(NUMBERED_OLD, NUMBERED_NEW)
        chk([k for k, _ in un2] == ["Totals are computed on the page"] and "Keep one token file" in its2,
            f"a numbered table's rule text is compared, not its row number: {[k for k, _ in un2]}")
        its4, un4, _, _ = coverage(CODES_OLD, CODES_NEW)
        chk([k for k, _ in un4] == ["200"], f"a first column of codes is not a row count: deleting the 200 row is reported ({[k for k, _ in un4]})")
        its3, un3, _, _ = coverage(NO_TRAILING_PIPE, "nothing here")
        chk({k for k, _ in un3} == {"name", "latency"}, f"rows without a closing pipe are still read: {sorted(k for k, _ in un3)}")
    return ok, lines


# Width folding is one character to one character, so offsets stay in the source.
WIDTH = str.maketrans({chr(i): chr(i - 0xFEE0) for i in range(0xFF01, 0xFF5F)})
SMART = str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'"})
KINDS = ('number', 'link', 'code', 'quoted-string', 'name')
COMMON_OPENERS = frozenset(('The', 'This', 'These', 'Those', 'An', 'It', 'We', 'You', 'They',
                           'He', 'She', 'If', 'When', 'While', 'And', 'Or', 'But', 'Each', 'Every',
                           'After', 'Thanks'))
TITLES = frozenset(('dr', 'mr', 'ms', 'mrs', 'prof'))
MONTHS = frozenset(('january february march april may june july august september october november december '
                    'jan feb mar apr jun jul aug sep sept oct nov dec').split())
UNITS = frozenset(('b kb mb gb tb pb kib mib gib tib ms s sec min h hz khz mhz ghz '
                   'mm cm m km mg g kg ml l mv v ma a w kw mw kwh c f am pm '
                   'cad eur usd gbp cny jpy aud chf hkd nzd csv').split())
SMALL_EN = dict(zip(('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                     'fifteen sixteen seventeen eighteen nineteen twenty').split(), map(str, range(21))))
SMALL_ZH = {'零':'0', '〇':'0', '一':'1', '二':'2', '两':'2', '三':'3', '四':'4', '五':'5',
            '六':'6', '七':'7', '八':'8', '九':'9', '十':'10', '二十':'20'}
SMALL_ZH.update({'十'+c: str(10+int(n)) for c,n in list(SMALL_ZH.items()) if 1 <= int(n) <= 9 and c != '两'})
# One/一 have common non-quantity uses; prefer missing a count to inventing one.
SMALL_EN.pop('one')
SMALL_ZH.pop('一')
LABELS = {'number': 'numbers', 'link': 'links', 'code': 'code items',
          'quoted-string': 'quoted strings', 'name': 'tentative names', 'heading': 'headings',
          'bold': 'bold terms', 'table-cell': 'table cells'}
LIMITS = ('This checks literal facts, not reasoning or rephrased sentences. Kept digits may have changed meaning. '
          'Names are the least certain kind: single names only at sentence/heading openings and month names are missed. '
          'Number words above twenty and standalone one/一 are not counted. '
          'Lowercase names and Chinese personal names are not detected. Table checks compare one cell per row. '
          'For fewer items, every old occurrence is marked because the missing location cannot be inferred.')


class Refusal(ValueError):
    pass


def width(text):
    return text.translate(WIDTH)


def number_key(value):
    return width(value).replace(',', '')


def link_key(value):
    try:
        p = urlsplit(value)
    except ValueError:
        return value
    # Do not lowercase credentials, path, query or fragment.
    authority = p.netloc
    if '@' in authority:
        user, host = authority.rsplit('@', 1)
        authority = user + '@' + host.lower()
    else:
        authority = authority.lower()
    return urlunsplit((p.scheme.lower(), authority, p.path.rstrip('/'), p.query, p.fragment))


def literal_key(value):
    return width(value).translate(SMART).replace('\r\n', '\n').replace('\r', '\n')


def quote_key(value):
    return literal_key(value).rstrip('.,。，')


def list_markers(text):
    folded = width(text)
    pattern = r'^[ \t]*(?:#{1,6}[ \t]+)?(?:[0-9]+[.)][ \t]+|[0-9]+、|\([0-9]+\)[ \t]*|[一二三四五六七八九十]+、)'
    return [m.span() for m in re.finditer(pattern, folded, re.M)]


def small_number_spans(text):
    """Zero through twenty except one/一; Chinese requires a quantity suffix."""
    folded = width(text)
    result = []
    words = '|'.join(sorted(set(SMALL_EN) | {'one','hundred','thousand','million','billion'}, key=len, reverse=True))
    atom = r'(?:'+words+r')'
    phrase = atom + r'(?:[ -]+(?:and[ -]+)?'+atom+r')*'
    for m in re.finditer(r'(?<![A-Za-z0-9_-])'+phrase+r'(?![A-Za-z0-9_-])', folded, re.I):
        word = m[0].lower()
        if word not in SMALL_EN:
            continue
        result.append((m.start(), m.end(), text[m.start():m.end()], SMALL_EN[word]))
    units = r'(?:小时|分钟|秒钟|秒|次|天|周|月|年|日|点|人|张|本|页|台|元|楼|个|包|位|份)'
    han = '零〇一二两三四五六七八九十百千万点'
    for m in re.finditer(r'(?<![第'+han+r'0-9])['+han+r']+(?=[ \t]*'+units+r')', folded):
        if m[0] in SMALL_ZH:
            result.append((m.start(), m.end(), text[m.start():m.end()], SMALL_ZH[m[0]]))
    return result


def name_spans(text, occupied):
    """Keep evidence-backed candidates and all their literal old mentions."""
    folded = width(text)
    latin = 'A-Za-z\u00c0-\u024f\u1e00-\u1eff'
    tokens = re.finditer(r'(?<![' + latin + r'0-9_])[' + latin + r']+(?:[\x27’-][' + latin + r']+)*(?![' + latin + r'0-9_])', folded)
    candidates = []
    for m in tokens:
        if (not m[0][0].isupper() or len(m[0]) < 2 or m[0] in COMMON_OPENERS
                or m[0].casefold() in MONTHS | UNITS | TITLES | set(SMALL_EN) | {'one'}
                or literal_key(m[0]).casefold() in {"i'm", "i'll"}):
            continue
        if candidates and re.fullmatch(r'[ \t]+', folded[candidates[-1][1]:m.start()]):
            candidates[-1] = (candidates[-1][0], m.end())
        else:
            candidates.append(m.span())
    lines = list(re.finditer(r'[^\r\n]+', folded))
    excluded = []
    for i, line in enumerate(lines):
        heading = re.match(r'^[ \t]*#{1,6}[ \t]+', line[0])
        next_line = lines[i+1][0] if i+1 < len(lines) else ''
        cells = next_line.strip().strip('|').split('|')
        header = line[0].startswith('|') and next_line.startswith('|') and all(c and set(c.strip()) <= set('-: ') for c in cells)
        if heading or header:
            excluded.append(line.span())
    approved, eligible = set(), []
    for a,b in candidates:
        if any(a < y and b > x for x,y in occupied):
            continue
        key = literal_key(text[a:b])
        if any(a < y and b > x for x,y in excluded):
            eligible.append((a,b,key))
            continue
        start = max(folded.rfind('\n',0,a), folded.rfind('\r',0,a)) + 1
        prefix = folded[start:a]
        # Honorific dots are not sentence boundaries; the title is evidence for
        # the surname, while the title token itself is excluded above.
        prefix = re.sub(r'\b(?:Dr|Mr|Ms|Mrs|Prof)\.', lambda m: m[0][:-1] + ' ', prefix, flags=re.I)
        boundaries = list(re.finditer(r'[.!?](?:[ \t]+|$)|[。！？]', prefix))
        if boundaries:
            prefix = prefix[boundaries[-1].end():]
        prefix = re.sub(r'^[ \t]*(?:[-+*][ \t]+|[0-9]+[.)][ \t]+|[0-9]+、)', '', prefix)
        interior = bool(prefix.strip(' \t|>*_`(（[【"“‘「『《'))
        multiword = bool(re.search(r'[ \t]', folded[a:b]))
        if not multiword and re.search(r'[:：][ \t]*$', prefix):
            continue
        eligible.append((a,b,key))
        acronym = bool(re.fullmatch(r'[A-Z]{2,10}', folded[a:b]))
        if interior or multiword or acronym:
            approved.add(key)
    return [(a,b,text[a:b]) for a,b,key in eligible if key in approved]


def code_key(value):
    return value.replace('\r\n', '\n').replace('\r', '\n')


def code_spans(text):
    """Markdown fenced, indented and matching-run inline code; contents only."""
    spans, occupied, opened = [], [], None
    for m in re.finditer(r'[^\r\n]*(?:\r\n|\r|\n|$)', text):
        line = m[0].rstrip('\r\n')
        if not m[0]:
            continue
        fence = re.match(r'^[ \t]*(`{3,}|~{3,})(.*)$', line)
        if opened:
            char, size, start, content, indent = opened
            if fence and fence[1][0] == char and len(fence[1]) >= size and not fence[2].strip():
                end = m.start()
                if end > content:
                    # The final newline belongs to the fence, not the code item.
                    if text[:end].endswith('\r\n'):
                        end -= 2
                    elif text[:end].endswith(('\r', '\n')):
                        end -= 1
                    if end > content:
                        value = ''.join(ln[len(indent):] if indent and ln.startswith(indent) else ln
                                        for ln in text[content:end].splitlines(keepends=True))
                        spans.append((content, end, value))
                occupied.append((start, m.end()))
                opened = None
        elif fence:
            indent = line[:line.index(fence[1])]
            opened = (fence[1][0], len(fence[1]), m.start(), m.end(), indent)
    if opened:
        start, content, indent = opened[2:]
        end = len(text.rstrip('\r\n'))
        if end > content:
            value = ''.join(ln[len(indent):] if indent and ln.startswith(indent) else ln
                            for ln in text[content:end].splitlines(keepends=True))
            spans.append((content, end, value))
        occupied.append((start, len(text)))
    def covered(a, b):
        return any(a < y and b > x for x, y in occupied)
    # Indented blocks are one piece; remove exactly four spaces or one tab per line.
    block, values = [], []
    for m in re.finditer(r'[^\r\n]+(?:\r\n|\r|\n|$)|(?:\r\n|\r|\n)', text):
        line = m[0].rstrip('\r\n')
        if (line.startswith('    ') or line.startswith('\t')) and not covered(m.start(), m.end()):
            block.append(m)
            values.append(line[1:] if line.startswith('\t') else line[4:])
        else:
            if block:
                a, b = block[0].start(), block[-1].end() - len(block[-1][0]) + len(block[-1][0].rstrip('\r\n'))
                spans.append((a, b, '\n'.join(values)))
                occupied.append((a, b))
            block, values = [], []
    if block:
        a, b = block[0].start(), len(text.rstrip('\r\n'))
        spans.append((a, b, '\n'.join(values)))
        occupied.append((a, b))
    runs = list(re.finditer(r'`+', text))
    i = 0
    while i < len(runs):
        first = runs[i]
        if covered(first.start(), first.end()):
            i += 1
            continue
        j = i + 1
        while j < len(runs) and (runs[j][0] != first[0] or covered(runs[j].start(), runs[j].end())):
            j += 1
        if j < len(runs):
            a, b = first.end(), runs[j].start()
            if b > a:
                spans.append((a, b, text[a:b]))
            i = j + 1
        else:
            i += 1
    return sorted(spans)


def fact_spans(text):
    """Overlapping kinds are intentional: a quote can also contain a number."""
    result = []
    def add(kind, a, b, value, key):
        result.append({'kind': kind, 'start': a, 'end': b, 'value': value, 'key': key(value)})
    folded = width(text)
    markers = list_markers(text)
    # Signs only at a token boundary, not a hyphen inside a date; all digit runs
    # count, including digits in identifiers. Matching uses entire tokens.
    num = r'(?<![0-9])(?:(?<![A-Za-z0-9])[-+])?(?:(?:[0-9]{1,3}(?:,[0-9]{3})+(?![0-9])|[0-9]+)(?:\.[0-9]+)*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?%?'
    for m in re.finditer(num, folded):
        if not any(m.start() < b and m.end() > a for a,b in markers):
            add('number', m.start(), m.end(), text[m.start():m.end()], number_key)
    for a,b,value,key in small_number_spans(text):
        if not any(a < y and b > x for x,y in markers):
            result.append({'kind':'number','start':a,'end':b,'value':value,'key':key})
    # Delimiters and sentence punctuation are outside the URL; balanced URL
    # parentheses remain part of the address.
    for m in re.finditer(r'(?:https?://|ftp://|mailto:|tel:)[^\s<>"“”「」『』《》\x27`\u3000-\u303f\uff00-\uffef\u3400-\u9fff]+', text, re.I):
        value = m[0].rstrip('.,;:!?')
        while value.endswith(')') and value.count(')') > value.count('('):
            value = value[:-1]
        while value.endswith(']') and value.count(']') > value.count('['):
            value = value[:-1]
        add('link', m.start(), m.start() + len(value), value, link_key)
    for m in re.finditer(r'(?<![A-Za-z0-9_.+%-])[A-Za-z0-9_+%-]+(?:\.[A-Za-z0-9_+%-]+)*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', text):
        if not any(s['kind']=='link' and m.start() < s['end'] and m.end() > s['start'] for s in result):
            add('link', m.start(), m.end(), m[0], link_key)
    def destination(a, b, value):
        if not value:
            return
        if any(s['kind']=='link' and s['start']==a and s['end']==b and s['value']==value for s in result):
            return
        # An explicit destination can continue beyond a bare URL's CJK boundary.
        result[:] = [s for s in result if not (s['kind']=='link' and a < s['end'] and b > s['start'])]
        add('link', a, b, value, link_key)
    # Inline Markdown destinations, including relative paths and fragment links.
    for m in re.finditer(r'!?\[[^\]\r\n]*\]\(\s*', text):
        a, i, depth = m.end(), m.end(), 0
        if i < len(text) and text[i] == '<':
            b = text.find('>', i + 1)
            if b >= 0:
                destination(i+1, b, text[i+1:b])
            continue
        while i < len(text):
            c = text[i]
            if c.isspace() or (c == ')' and depth == 0):
                break
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            i += 1
        destination(a, i, text[a:i])
    # A reference definition is a literal destination; resolved reference uses
    # are additional links, located at their bracketed text.
    definitions, definition_starts = {}, set()
    for m in re.finditer(r'^ {0,3}\[([^\]\r\n]+)\]:[ \t]*(?:<([^>\r\n]+)>|([^\s]+))', text, re.M):
        group = 2 if m[2] is not None else 3
        value = m[group]
        definitions.setdefault(' '.join(m[1].split()).casefold(), value)
        definition_starts.add(m.start() + len(m[0]) - len(m[0].lstrip()))
        destination(m.start(group), m.end(group), value)
    for m in re.finditer(r'!?\[([^\]\r\n]+)\](?:\[([^\]\r\n]*)\])?', text):
        if m.start() in definition_starts or text[m.end():m.end()+1] == '(':
            continue
        label = ' '.join((m[2] or m[1]).split()).casefold()
        if label in definitions:
            add('link', m.start(), m.end(), definitions[label], link_key)
    code = code_spans(text)
    for a, b, value in code:
        add('code', a, b, value, code_key)
    for m in re.finditer(r'"([^"]+)"|“([^”]+)”|「([^」]+)」|『([^』]+)』|《([^》]+)》|(?<![A-Za-z])\x27([^\x27]+)\x27(?![A-Za-z])|(?<![A-Za-z])‘([^’]+)’(?![A-Za-z])', text):
        group = next(i for i in range(1, 8) if m[i] is not None)
        if quote_key(m[group]):
            add('quoted-string', m.start(group), m.end(group), m[group], quote_key)
    occupied = [(s['start'],s['end']) for s in result if s['kind'] in ('link','code')]
    for a,b,value in name_spans(text, occupied):
        add('name', a, b, value, literal_key)
    return sorted(result, key=lambda s: (s['start'], s['end'], s['kind']))


def literal_count(key, text, boundary=False):
    pattern = re.escape(key)
    if boundary:
        latin = 'A-Za-z\u00c0-\u024f\u1e00-\u1eff'
        pattern = r'(?<![' + latin + r'0-9_])' + pattern + r'(?![' + latin + r'0-9_])'
    return len(re.findall(pattern, literal_key(text)))


def status_for(old_count, new_count):
    return 'kept' if new_count >= old_count else ('fewer' if new_count else 'lost')


def structural_spans(text, min_len):
    """Locate the same unique structural items that the legacy check selected."""
    candidates = defaultdict(list)
    for m in re.finditer(r'^#{1,6}\s+(.+?)\s*#*\s*$', text, re.M):
        a, b = m.span(1)
        candidates[m[1].strip()].append((a, b))
    for m in re.finditer(r'\*\*(.+?)\*\*', text):
        candidates[m[1].strip()].append(m.span(1))
    block, offset = [], 0
    for line in text.splitlines(keepends=True) + ['']:
        raw_line = line.rstrip('\r\n')
        if re.match(r'^\|[^|]*\|', raw_line):
            block.append((offset, raw_line))
        elif block:
            rows = [[c.strip().strip('*_` ') for c in ln.strip().strip('|').split('|')] for _, ln in block]
            sep = next((i for i,r in enumerate(rows) if all(set(c) <= set('-: ') for c in r)), None)
            skip = counts_rows(rows[sep+1:] if sep is not None else rows)
            for i, ((pos, ln), cells) in enumerate(zip(block, rows)):
                if i == sep:
                    continue
                index = 1 if skip and len(cells)>1 else 0
                value = cells[index]
                if value and not set(value) <= set('-: '):
                    content = ln.strip().strip('|')
                    raw_cells = content.split('|')
                    a = pos + ln.index(content) + sum(len(c)+1 for c in raw_cells[:index]) + raw_cells[index].index(value)
                    candidates[value].append((a,a+len(value)))
            block = []
        offset += len(line)
    return [(value, kind, candidates[value][0]) for value, kind in items(text, min_len).items()]


def location(text, start, end, starts):
    line = bisect.bisect_right(starts, start) - 1
    last = bisect.bisect_right(starts, end - 1) - 1
    return {'start': start, 'end': end, 'line': line + 1, 'column': start - starts[line] + 1,
            'end_line': last + 1, 'end_column': end - starts[last], 'text': text[start:end]}


def analyze(old, new, min_len=3):
    starts = [0] + [m.end() for m in re.finditer(r'\r\n|\r|\n', old)]
    old_spans, new_spans = fact_spans(old), fact_spans(new)
    new_counts = Counter((s['kind'], s['key']) for s in new_spans)
    lost_parents = [(s['start'], s['end']) for s in old_spans if s['kind'] in ('link','code')
                    and new_counts[(s['kind'],s['key'])] == 0]
    quote_counts = Counter(s['key'] for s in old_spans if s['kind'] == 'quoted-string')
    reduced_quotes = {key for key, count in quote_counts.items()
                      if literal_count(key, new, boundary=True) < count}
    covered_names = [(s['start'], s['end']) for s in old_spans
                     if s['kind'] == 'quoted-string' and s['key'] in reduced_quotes]
    groups = {}
    for s in old_spans:
        if s['kind'] == 'number' and any(s['start'] >= a and s['end'] <= b for a,b in lost_parents):
            continue
        if s['kind'] == 'name' and any(s['start'] >= a and s['end'] <= b for a,b in covered_names):
            continue
        token = (s['kind'], s['key'])
        group = groups.setdefault(token, {'kind': s['kind'], 'value': s['value'], 'key': s['key'], 'locations': []})
        group['locations'].append(location(old, s['start'], s['end'], starts))
    result = []
    for token, group in groups.items():
        kind, key = token
        count = literal_count(key, new, boundary=True) if kind in ('name', 'quoted-string') else new_counts[token]
        before = len(group['locations'])
        group.update(old_count=before, new_count=count, status=status_for(before, count), missing_count=max(0, before-count))
        result.append(group)
    for value, kind, (a, b) in structural_spans(old, min_len):
        kept = norm(value) in norm(new)
        result.append({'kind': kind, 'value': value, 'key': norm(value), 'old_count': 1,
                       'new_count': int(kept), 'missing_count': int(not kept), 'status': 'kept' if kept else 'lost',
                       'locations': [location(old, a, b, starts)]})
    counts = {}
    for kind in KINDS + ('heading', 'bold', 'table-cell'):
        rows = [r for r in result if r['kind'] == kind]
        counts[kind] = {'old': len(rows),
                        'kept': sum(r['status'] == 'kept' for r in rows),
                        'lost': sum(r['status'] == 'lost' for r in rows),
                        'fewer': sum(r['status'] == 'fewer' for r in rows),
                        'missing': sum(r['missing_count'] for r in rows)}
    for i, row in enumerate(result, 1):
        row['id'] = f'I{i:04d}'
    return {'schema_version': 2, 'counts': counts, 'items': result,
            'structure': {'old': structure(old), 'new': structure(new)}, 'limits': LIMITS}


def summary(data):
    c = data['counts']
    line = 'distinct items · kept ' + ', '.join(f"{c[k]['kept']} of {c[k]['old']} {LABELS[k]}" for k in KINDS)
    singular = {'number': 'number', 'link': 'link', 'code': 'code item', 'quoted-string': 'quoted string', 'name': 'tentative name',
                'heading': 'heading', 'bold': 'bold term', 'table-cell': 'table cell'}
    lost = ', '.join(f"{c[k]['lost']} {singular[k] if c[k]['lost'] == 1 else LABELS[k]}" for k in c if c[k]['lost'])
    fewer_parts = []
    for k in KINDS:
        groups = [r for r in data['items'] if r['kind'] == k and r['status'] == 'fewer']
        if groups:
            after = sum(r['new_count'] for r in groups)
            before = sum(r['old_count'] for r in groups)
            fewer_parts.append(f"{len(groups)} {singular[k] if len(groups) == 1 else LABELS[k]} ({before}→{after} occurrences)")
    fewer = ', '.join(fewer_parts)
    return line + '; lost: ' + (lost or 'none') + ('; fewer: ' + fewer if fewer else '')


def read_text(path):
    label = Path(path).name or str(path) or '.'
    if Path(path).is_dir():
        raise Refusal(f'{label}: give a UTF-8 text file, not a directory.')
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise Refusal(f'{label}: could not read this file.')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise Refusal(f'{Path(path).name}: save it as UTF-8 text.')
    if any(ord(c) < 32 and c not in '\t\n\r' for c in text) or '\x7f' in text:
        raise Refusal(f'{Path(path).name}: save it as UTF-8 text.')
    if not text.strip():
        raise Refusal(f'{Path(path).name}: the file is empty.')
    return text


CSS = '''
:root{color-scheme:light dark}*{box-sizing:border-box}
body{margin:0;font:16px/1.5 system-ui,sans-serif}
.shell{--ink:#24302e;--muted:#64716c;--line:#dbe3dd;--paper:#fff;--bg:#f3f5f0;--accent:#315f50;--mark:#a93920;--on-mark:#f9f6ee;--fewer:#f6e7be;--fewer-line:#7e5800;background:var(--bg);color:var(--ink);min-height:100vh;padding:28px max(16px,calc((100vw - 1120px)/2)) 48px}
@media(prefers-color-scheme:dark){.shell{--ink:#e5ede8;--muted:#afbeb4;--line:#43544a;--paper:#202b26;--bg:#16201b;--accent:#b1d8c3;--mark:#da7b66;--on-mark:#0d0c12;--fewer:#635329;--fewer-line:#d9ad60}}
#dark:checked~.shell{--ink:#e5ede8;--muted:#afbeb4;--line:#43544a;--paper:#202b26;--bg:#16201b;--accent:#b1d8c3;--mark:#da7b66;--on-mark:#0d0c12;--fewer:#635329;--fewer-line:#d9ad60;color-scheme:dark}
#light:checked~.shell{--ink:#24302e;--muted:#64716c;--line:#dbe3dd;--paper:#fff;--bg:#f3f5f0;--accent:#315f50;--mark:#a93920;--on-mark:#f9f6ee;--fewer:#f6e7be;--fewer-line:#7e5800;color-scheme:light}
.theme-input{position:absolute;width:1px;height:1px;clip-path:inset(50%)}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
.themes{display:flex;gap:12px;font-size:13px}.themes label{cursor:pointer;text-decoration:underline;text-underline-offset:3px;padding:8px 0}
#auto:focus-visible~.shell label[for=auto],#light:focus-visible~.shell label[for=light],#dark:focus-visible~.shell label[for=dark]{outline:2px solid var(--accent);outline-offset:3px}
#auto:checked~.shell label[for=auto],#light:checked~.shell label[for=light],#dark:checked~.shell label[for=dark]{font-weight:750}
h1{font-size:27px;line-height:1.2;margin:10px 0 14px;letter-spacing:-.03em}h2{font-size:21px;margin:26px 0 12px}h3{font-size:16px;margin:0 0 10px}
a{color:var(--accent);text-underline-offset:3px}a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.coverage{font-size:18px;margin:12px 0}.limit,.location,footer{font-size:13px;color:var(--muted)}
.card{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:18px;margin:12px 0;overflow-wrap:anywhere}
.preview{font-size:18px;white-space:pre-wrap}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}
.stat{border:1px solid var(--line);border-radius:8px;padding:12px;background:var(--paper)}.stat strong{display:block}.stat span{font-size:13px;color:var(--muted)}
.documents{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px}.document{min-width:0}.document+.document{border-left:1px solid var(--line);padding-left:24px}
pre{font:15px/1.65 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0;tab-size:4}
mark{background:var(--mark);color:var(--on-mark);border-bottom:2px solid var(--ink);-webkit-box-decoration-break:clone;box-decoration-break:clone;-webkit-print-color-adjust:exact;print-color-adjust:exact}mark.fewer{background:var(--fewer);color:var(--ink);border-bottom:2px dashed var(--fewer-line)}.source-anchor{scroll-margin-top:24px}.source-anchor:target+mark{outline:2px solid var(--accent)}
.group{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}.group li{margin:10px 0}.value{white-space:pre-wrap;overflow-wrap:anywhere}.badge{font-size:12px;font-weight:650;margin-right:7px;color:var(--accent)}
nav{display:flex;gap:18px;flex-wrap:wrap;margin:16px 0}.structure{font-size:13px;color:var(--muted);overflow-wrap:anywhere}.shell,p,li{overflow-wrap:anywhere}
@media(max-width:600px){.shell{padding:19px 16px 40px}h1{font-size:24px}.coverage{font-size:17px}.card{padding:13px}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.documents{grid-template-columns:minmax(0,1fr);gap:17px}.document+.document{border-left:0;border-top:1px solid var(--line);padding:17px 0 0}pre{font-size:14px}}
@media print{.shell{background:#fff;color:#24302e;padding:0}.themes{display:none}.documents{display:block}.document+.document{border:0;padding:0}.card{break-inside:avoid}}
'''


def marked_source(text, rows):
    """Sweep overlapping spans without nested or invalid mark elements."""
    events, anchors = defaultdict(list), defaultdict(list)
    for row in rows:
        if row['status'] == 'kept':
            continue
        for i, loc in enumerate(row['locations'], 1):
            token = (row['id'], i)
            events[loc['start']].append((True, token, row))
            events[loc['end']].append((False, token, row))
            anchors[loc['start']].append(f'{row["id"]}-{i}')
    active, out, last = {}, [], 0
    for pos in sorted(set(events) | {0, len(text)}):
        chunk = html.escape(text[last:pos])
        if active:
            title = '; '.join(f'{r["status"]}: {r["kind"]}' for r in active.values())
            cls = ' class="fewer"' if any(r['status'] == 'fewer' for r in active.values()) else ''
            out.append(f'<mark{cls} title="{html.escape(title, quote=True)}">{chunk}</mark>')
        else:
            out.append(chunk)
        for name in anchors[pos]:
            out.append(f'<span class="source-anchor" id="{name}"></span>')
        for entering, token, row in events[pos]:
            if entering:
                active[token] = row
            else:
                active.pop(token, None)
        last = pos
    return ''.join(out)


def text_language(text):
    return 'zh' if len(re.findall(r'[\u3400-\u9fff]', text)) > len(re.findall(r'[A-Za-z]', text)) else 'en'


def render_html(data, old, new):
    esc = html.escape
    rows = [r for r in data['items'] if r['status'] != 'kept']
    bits = [f'<!doctype html><html lang="{text_language(old+new)}"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
            f'<title>Rewrite coverage · {esc(data["old_file"])}</title><style>{CSS}</style></head><body>',
            '<input class="theme-input" type="radio" name="theme" id="auto" aria-label="System theme" checked>',
            '<input class="theme-input" type="radio" name="theme" id="light" aria-label="Light theme">',
            '<input class="theme-input" type="radio" name="theme" id="dark" aria-label="Dark theme">',
            '<main class="shell"><div class="top"><span class="eyebrow">Your rewrite, with its missing details</span>',
            '<div class="themes" aria-label="Theme"><label for="auto">System</label><label for="light">Light</label><label for="dark">Dark</label></div></div>',
            '<h1>Rewrite coverage</h1>', f'<p class="coverage">{esc(summary(data))}.</p>',
            f'<p class="location">{esc(data["old_file"])} → {esc(data["new_file"])}</p>',
            f'<p class="limit">{esc(LIMITS)}</p>']
    if rows:
        first = rows[0]
        loc = first['locations'][0]
        bits.append(f'<article class="card"><h3>First item to check · {esc(first["kind"])} · {first["status"]}</h3>'
                    f'<p class="location">Old line {loc["line"]}, column {loc["column"]} · {first["old_count"]} before → {first["new_count"]} after</p>'
                    f'<p class="preview"><mark{" class=" + chr(34) + "fewer" + chr(34) if first["status"] == "fewer" else ""}>{esc(first["value"])}</mark></p>'
                    f'<a href="#{first["id"]}-1">See its place in the old text</a></article>')
    else:
        bits.append('<p class="card">Every extracted item is kept; this does not prove the rewrite is complete or correct.</p>')
    bits.append('<section aria-label="Counts by kind" class="stats">')
    for kind, c in data['counts'].items():
        bits.append(f'<div class="stat"><strong>{esc(LABELS[kind])}</strong><span>{c["kept"]} kept / {c["old"]} before<br>{c["lost"]} lost · {c["fewer"]} fewer</span></div>')
    bits.append('</section><nav aria-label="Report sections"><a href="#findings">Lost and fewer items</a><a href="#old">Old text</a><a href="#new">New text</a></nav>')
    so, sn = data['structure']['old'], data['structure']['new']
    bits.append('<p class="structure">Structure: ' + ' · '.join(f'{k} {so[k]} → {sn[k]}' for k in so) + '</p>')
    if sn['chars'] < .6 * so['chars']:
        bits.append('<p class="limit">The new text has less than 60% of the old characters; check for truncation.</p>')
    if sn['headings'] == 0 and so['headings'] > 2:
        bits.append('<p class="limit">The old text had several headings; the new has none. A term dump can keep words and lose structure.</p>')
    bits.append('<section id="findings"><h2>Lost and fewer items</h2>')
    for kind in data['counts']:
        group = [r for r in rows if r['kind'] == kind]
        if not group:
            continue
        bits.append(f'<div class="group"><h3>{esc(LABELS[kind].capitalize())}</h3><ul>')
        for r in group:
            links = ' · '.join(f'<a href="#{r["id"]}-{i}">line {loc["line"]}:{loc["column"]}</a>' for i, loc in enumerate(r['locations'], 1))
            verdict = f' · ledger: {esc(r["verdict"])}' if r.get('verdict') else ''
            bits.append(f'<li><span class="badge">{r["status"].upper()}</span><span class="value">{esc(r["value"])}</span>'
                        f'<div class="location">{r["old_count"]} before → {r["new_count"]} after · {r["missing_count"]} missing{verdict}<br>{links}</div></li>')
        bits.append('</ul></div>')
    if not rows:
        bits.append('<p>No lost or fewer items were found.</p>')
    bits.append('</section><h2>Both documents</h2><div class="card documents">')
    bits.append(f'<section class="document" id="old"><h3>Old text · {esc(data["old_file"])}</h3>'
                '<p class="location">Red with a solid underline: lost · amber with a dashed underline: fewer (all old occurrences).</p>'
                f'<pre>{marked_source(old, data["items"])}</pre></section>')
    bits.append(f'<section class="document" id="new"><h3>New text · {esc(data["new_file"])}</h3><pre>{esc(new)}</pre></section></div>')
    bits.append('<footer>Local UTF-8 text comparison. No outside requests. Counts are evidence to review, not a quality score.</footer></main></body></html>')
    return ''.join(bits)


def same_file(a, b):
    if Path(a).resolve() == Path(b).resolve():
        return True
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def exit_status(data):
    return int(any(r['status'] != 'kept' for r in data['items']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', nargs='?')
    parser.add_argument('new', nargs='?')
    parser.add_argument('--html', metavar='REPORT.html', help='offline page (default: rewrite-coverage.html; refuses an existing default)')
    parser.add_argument('--json', action='store_true', help='print every item and source location as JSON')
    parser.add_argument('--out', metavar='LIST.md', help='also write the legacy structural list')
    parser.add_argument('--ledger', help='annotate items with human verdicts; does not override the exit code')
    parser.add_argument('--min-len', type=int, default=3, help='minimum structural item length; hard facts are never filtered')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.old or not args.new:
        parser.error('give the old and new files')
    try:
        implicit_html = args.html is None
        args.html = args.html or 'rewrite-coverage.html'
        if same_file(args.old, args.new):
            raise Refusal('Old and new are the same file; give two different files.')
        old, new = read_text(args.old), read_text(args.new)
        if implicit_html and (Path(args.html).exists() or Path(args.html).is_symlink()):
            raise Refusal('rewrite-coverage.html already exists; choose an explicit --html path.')
        outputs = [p for p in (args.html, args.out) if p]
        inputs = [p for p in (args.old, args.new, args.ledger) if p]
        if any(same_file(p, q) for p in outputs for q in inputs) or (len(outputs) == 2 and same_file(*outputs)):
            raise Refusal('Choose output files different from the inputs and each other.')
        data = analyze(old, new, args.min_len)
        data.update(old_file=Path(args.old).name, new_file=Path(args.new).name, report=str(args.html))
        ledger_text = None
        if args.ledger:
            ledger_text = read_text(args.ledger)
            verdicts = ledger_verdicts(ledger_text)
            for row in data['items']:
                row['verdict'] = verdicts.get(norm(row['value']))
        with Path(args.html).open('x' if implicit_html else 'w', encoding='utf-8') as output:
            output.write(render_html(data, old, new))
        # Preserve the three-check list and its order, including its original format.
        its, un, so, sn = coverage(old, new, args.min_len)
        if args.out:
            Path(args.out).write_text('\n'.join(f'- {k}  ({kind})  [ ]' for k, kind in un) + '\n', encoding='utf-8')
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(summary(data))
            structural_lines = legacy_text_report(old, new, args.min_len, ledger_text)[1]
            structural_lines = [line.replace('✔ every old item occurs in the new text',
                                             '✔ every structural item (heading, bold term or table cell) occurs in the new text')
                                for line in structural_lines]
            print('\n'.join(structural_lines))
            for row in data['items']:
                if row['kind'] in KINDS and row['status'] != 'kept':
                    loc = row['locations'][0]
                    value = row['value'].replace('\r', '\\r').replace('\n', '\\n')
                    print(f'  {row["status"]:<5} {row["kind"]:<13} {value} ({row["old_count"]}→{row["new_count"]}; old {loc["line"]}:{loc["column"]})')
            print('Report: ' + str(args.html))
        return exit_status(data)
    except (Refusal, OSError) as exc:
        print(str(exc) if isinstance(exc, Refusal) else 'Could not write the output; choose a writable file path.', file=sys.stderr)
        return 2


# Self-contained regression inputs; checker artifacts are not installed.
BLIND_FIXTURES = {'en-new': '# Lantern Desk cutover runbook\n'
           '\n'
           'Owner: Priya Okafor (reviewed by Tomas Lindqvist, 2027-03-04).\n'
           '\n'
           '## Preconditions\n'
           '\n'
           '- Window: 12 March, 21:30, four hours.\n'
           '- Lantern Desk holds 1480 open tickets; start only when the queue is under 250.\n'
           '- Read the checklist (https://example.com/lantern/checklist) and the rollback notes '
           'first. Questions: ops@example.com.\n'
           '\n'
           '## Procedure\n'
           '\n'
           '1. Freeze the old system with `lanternctl freeze --all`; wait for “queue frozen”.\n'
           '2. Export:\n'
           '\n'
           '   ```\n'
           '   lanternctl export --since 2019-01-01 --out /tmp/lantern.tar\n'
           '   ```\n'
           '\n'
           '3. The archive should be about 2.5 GB. Under 1 GB, stop and call the owner.\n'
           '4. On Beacon Hub, run `beacon import /tmp/lantern.tar --workers 8`.\n'
           "5. After 'import complete', the dashboard (https://example.com/beacon/status) must "
           'show 1,480 open tickets.\n'
           '6. Tell the support leads they may log in.\n'
           '\n'
           '## Rollback\n'
           '\n'
           'Roll back if totals differ by more than 0.5%: `lanternctl thaw --all`, then purge '
           'Beacon Hub. Allow 15 minutes, then write to Priya Okafor.\n'
           '\n'
           '## Known problems\n'
           '\n'
           '- Attachments over 25 MB are skipped and logged.\n'
           '- Tickets from the old Parcel Bot have no author (fix by Tomas Lindqvist: '
           'https://example.com/beacon/issues/412).\n'
           '- The search index needs roughly 40 minutes; users see a banner meanwhile.\n'
           '\n'
           '## Afterwards\n'
           '\n'
           '| Task | Who | Due |\n'
           '|---|---|---|\n'
           '| Archive the export file | Tomas Lindqvist | 14 March |\n'
           '| Survey the support team | Priya Okafor | 2 April |\n'
           '\n'
           'The old login page has a grace period of 30 days; the read-only mirror stays for 90.\n',
 'email-new': 'see https://example.com/help .\n',
 'zh-new': '# 「青屿书店」秋季会员日：筹备要点\n'
           '\n'
           '负责人周既白，协办 Lena Hoffmann（Paper Kite Studio）。2027年9月3日更新。\n'
           '\n'
           '## 时间与规模\n'
           '\n'
           '- １０月１６日（周六）１０点至晚９点。\n'
           '- 预计到场 1200 人，目标比去年增长２５％。\n'
           '- 场地上限３５０人，超出时分批放行。\n'
           '\n'
           '## 分工\n'
           '\n'
           '| 事项 | 负责人 | 截止 |\n'
           '|---|---|---|\n'
           '| 海报与易拉宝 | Lena Hoffmann | １０月９日 |\n'
           '| 名单导出 | 周既白 | １０月１６日 |\n'
           '\n'
           '## 流程\n'
           '\n'
           '1. 后台运行 `shelfctl tag --event autumn`，出现「标签已写入」即完成。\n'
           '2. 把报名页 https://example.com/qingyu/signup 发到会员群。\n'
           '3. 当天早上导出名单：\n'
           '\n'
           '```\n'
           'shelfctl export --list members --format csv\n'
           '```\n'
           '\n'
           '4. 每满５００元送《雾中灯塔》一本，每人限领１本。\n'
           '5. 结束后把销售额填表。\n'
           '\n'
           '## 注意\n'
           '\n'
           '- 收银台３台。周既白的原则是“宁可慢，不要错”。\n'
           '- 海报须在１０月９日前送到。\n'
           '- 雨天签售改到二楼「云室」（４０人）。\n'
           '- 规则变动以 https://example.com/qingyu/rules 为准。\n',
 'opener-old': 'Before the cutover, check the queue. Run the freeze. Mara Fen signs.\n',
 'listmarker-new': 'what to do:\n\n1. upload\n2. wait\n3. upload again\n4. check\n5. report\n',
 'fence-indent-old': 'steps:\n\n1. export:\n\n   ```\n   lanternctl export --all\n   ```\n',
 'email-old': 'write to duty@example.com or see https://example.com/help .\n',
 'en-old': '# Lantern Desk migration: runbook for the March cutover\n'
           '\n'
           'Owner: Priya Okafor. Reviewed by Tomas Lindqvist on 2027-03-04.\n'
           '\n'
           '## Before you start\n'
           '\n'
           'The cutover window opens on 12 March at 21:30 and lasts 4 hours. Lantern Desk '
           'currently holds 1,480 open tickets and 36,200 archived ones. Do not begin unless the '
           'queue is below 250 tickets, because the importer handles roughly 90 tickets per '
           'minute. The last rehearsal, on 26 February, finished in 3 hours 10 minutes.\n'
           '\n'
           'Read the checklist at https://example.com/lantern/checklist/ and the rollback notes at '
           'https://example.com/lantern/rollback before touching anything. Questions go to '
           'ops@example.com or, out of hours, to duty@example.com. Bring the paper copy of the '
           "'red binder' procedure in case the VPN drops, and post progress in the leads' "
           'channel.\n'
           '\n'
           '## Steps\n'
           '\n'
           '1. Freeze the old system. Run `lanternctl freeze --all` and wait for the message '
           '"queue frozen".\n'
           '2. Export the data:\n'
           '\n'
           '   ```\n'
           '   lanternctl export --since 2019-01-01 --out /tmp/lantern.tar\n'
           '   ```\n'
           '\n'
           '3. Check the archive size. It should be close to 2.5 GB. If it is under 1 GB, stop and '
           'call Priya Okafor.\n'
           '4. Start the importer on Beacon Hub with `beacon import /tmp/lantern.tar --workers '
           '8`.\n'
           '5. When the importer prints "import complete", compare the totals. The dashboard at '
           'https://example.com/beacon/status must show 1,480 open tickets.\n'
           '6. Tell the support leads in the channel that they may log in.\n'
           '\n'
           '## Known problems\n'
           '\n'
           '- Attachments larger than 25 MB are skipped. The importer logs the line "attachment '
           'skipped" for each one. Last rehearsal skipped 14 files.\n'
           '- Tickets created by the old Parcel Bot have no author. Tomas Lindqvist wrote a fix; '
           'see https://example.com/beacon/issues/412.\n'
           '- The search index takes about 40 minutes to rebuild. Users will see the banner '
           '"search is catching up" until it finishes.\n'
           '- The dashboard (https://example.com/beacon/status) lags by about 2 minutes, so do not '
           'panic at the first reading.\n'
           '\n'
           '## Rollback\n'
           '\n'
           'If the totals differ by more than 0.5%, roll back. Run `lanternctl thaw --all`, then '
           '`beacon purge --confirm`. Rollback takes 15 minutes. After a rollback, write to Priya '
           'Okafor and to Mei-Ling Castellanos, who decides whether to retry on 19 March.\n'
           '\n'
           '## After the cutover\n'
           '\n'
           '| Task | Who | Due |\n'
           '|---|---|---|\n'
           '| Close the old billing account | Mei-Ling Castellanos | 31 March |\n'
           '| Archive the export file | Tomas Lindqvist | 14 March |\n'
           '| Survey the support team | Priya Okafor | 2 April |\n'
           '\n'
           'The **grace period** for the old login page is 30 days. The **read-only mirror** stays '
           'up for 90 days. As the vendor\'s contract says, "data is deleted 90 days after '
           'termination".\n',
 'zh-old': '# 「青屿书店」秋季会员日筹备说明\n'
           '\n'
           '负责人：周既白；协办：Lena Hoffmann（供应商 Paper Kite Studio 的对接人）。更新于２０２７年９月３日。\n'
           '\n'
           '## 一、时间与规模\n'
           '\n'
           '会员日定在１０月１６日（周六），上午１０点开门，晚上９点结束。预计到场１，２００人，其中老会员约８００人。去年同期到场９６０人，所以今年的目标是增长２５％。场地最多容纳３５０人，超过就要在门口分批放行。\n'
           '\n'
           '## 二、要做的事\n'
           '\n'
           '1. 在后台运行 `shelfctl tag --event autumn`，给参加活动的图书打标签，看到“标签已写入”才算完成。\n'
           '2. 把报名页 https://example.com/qingyu/signup/ 的链接发到会员群；海报素材在 '
           'https://example.net/kite/poster-v3 。\n'
           '3. 活动当天早上导出名单：\n'
           '\n'
           '```\n'
           'shelfctl export --list members --format csv\n'
           '```\n'
           '\n'
           '4. 现场每满５００元送一本《雾中灯塔》，每人限领１本；《潮汐手记》只送给前５０位到场的会员。\n'
           '5. 结束后把销售额填进表格，并抄送 Marco Bellini。\n'
           '\n'
           '## 三、注意事项\n'
           '\n'
           '- 收银台只有３台，周既白说过：“宁可慢，不要错。”结账时请对每位顾客说「谢谢惠顾，欢迎再来」。\n'
           '- Paper Kite Studio 的海报要在１０月９日前送到，联系人是 Lena Hoffmann，邮箱 lena@example.net。\n'
           '- 如果下雨，签售改到二楼的“云室”，那里只能坐４０人。\n'
           '- 去年有人用 `shelfctl refund --all` 误退了全部订单，今年这条命令已被禁用。\n'
           '- 志愿者手册《会员日十问》放在前台，共１２页。\n'
           '- 《雾中灯塔》库存只有２００本，发完即止。\n'
           '\n'
           '## 四、分工\n'
           '\n'
           '| 事项 | 负责人 | 截止 |\n'
           '|---|---|---|\n'
           '| 海报与易拉宝 | Lena Hoffmann | １０月９日 |\n'
           '| 名单导出 | 周既白 | １０月１６日 |\n'
           '| 赠书清点（《雾中灯塔》） | Marco Bellini | １０月１４日 |\n'
           '\n'
           '**雨天方案**和**赠书规则**如有变动，以 https://example.com/qingyu/rules 为准。\n',
 'opener-new': 'Check the queue before the cutover, then run the freeze. Mara Fen signs.\n',
 'listmarker-old': 'retry the upload 5 times, then wait 3 minutes.\n',
 'fence-indent-new': 'export with:\n\n```\nlanternctl export --all\n```\n'}

BLIND_EXPECTED = {'en': [['number', '36200', 'lost', 1, 0],
        ['number', '90', 'fewer', 3, 1],
        ['number', '26', 'lost', 1, 0],
        ['number', '3', 'lost', 1, 0],
        ['number', '10', 'lost', 1, 0],
        ['number', '2', 'fewer', 2, 1],
        ['number', '14', 'fewer', 2, 1],
        ['number', '19', 'lost', 1, 0],
        ['number', '31', 'lost', 1, 0],
        ['link', 'https://example.com/lantern/rollback', 'lost', 1, 0],
        ['link', 'duty@example.com', 'lost', 1, 0],
        ['link', 'https://example.com/beacon/status', 'fewer', 2, 1],
        ['code', 'beacon purge --confirm', 'lost', 1, 0],
        ['quoted-string', 'red binder', 'lost', 1, 0],
        ['quoted-string', 'attachment skipped', 'lost', 1, 0],
        ['quoted-string', 'search is catching up', 'lost', 1, 0],
        ['quoted-string', 'data is deleted 90 days after termination', 'lost', 1, 0],
        ['name', 'Mei-Ling Castellanos', 'lost', 2, 0],
        ['name', 'VPN', 'lost', 1, 0],
        ['name', 'Priya Okafor', 'fewer', 4, 3],
        ['heading', 'lanterndeskmigrationrunbookforthemarchcutover', 'lost', 1, 0],
        ['heading', 'beforeyoustart', 'lost', 1, 0],
        ['heading', 'steps', 'lost', 1, 0],
        ['heading', 'afterthecutover', 'lost', 1, 0],
        ['table-cell', 'closetheoldbillingaccount', 'lost', 1, 0]],
 'zh': [['number', '800', 'lost', 1, 0],
        ['number', '960', 'lost', 1, 0],
        ['number', '50', 'lost', 1, 0],
        ['number', '12', 'lost', 1, 0],
        ['number', '200', 'lost', 1, 0],
        ['number', '14', 'lost', 1, 0],
        ['number', '10', 'fewer', 6, 5],
        ['link', 'https://example.net/kite/poster-v3', 'lost', 1, 0],
        ['link', 'lena@example.net', 'lost', 1, 0],
        ['code', 'shelfctl refund --all', 'lost', 1, 0],
        ['quoted-string', '潮汐手记', 'lost', 1, 0],
        ['quoted-string', '谢谢惠顾,欢迎再来', 'lost', 1, 0],
        ['quoted-string', '会员日十问', 'lost', 1, 0],
        ['quoted-string', '雾中灯塔', 'fewer', 3, 1],
        ['name', 'Marco Bellini', 'lost', 2, 0],
        ['name', 'Lena Hoffmann', 'fewer', 3, 2],
        ['name', 'Paper Kite Studio', 'fewer', 2, 1],
        ['heading', '青屿书店秋季会员日筹备说明', 'lost', 1, 0],
        ['heading', '一时间与规模', 'lost', 1, 0],
        ['heading', '二要做的事', 'lost', 1, 0],
        ['heading', '三注意事项', 'lost', 1, 0],
        ['heading', '四分工', 'lost', 1, 0],
        ['bold', '雨天方案', 'lost', 1, 0],
        ['bold', '赠书规则', 'lost', 1, 0],
        ['table-cell', '赠书清点《雾中灯塔》', 'lost', 1, 0]]}

LAST_FIXTURES = {'heading-numbers-dropped': ('## 1. Scope\n'
                             '\n'
                             'The pilot runs for 3 weeks in 2 cities.\n'
                             '\n'
                             '## 2. Budget\n'
                             '\n'
                             'The budget is 900 dollars.\n'
                             '\n'
                             '## 3. Risks\n'
                             '\n'
                             'None yet.\n',
                             '## Scope\n'
                             '\n'
                             'The pilot runs for 3 weeks in 2 cities.\n'
                             '\n'
                             '## Budget\n'
                             '\n'
                             'The budget is 900 dollars.\n'
                             '\n'
                             '## Risks\n'
                             '\n'
                             'None yet.\n'),
 'heading-numbers-hide-a-loss': ('retry the upload 5 times, then wait 3 minutes.\n',
                                 '## 1. Upload\n'
                                 '\n'
                                 'upload the file.\n'
                                 '\n'
                                 '## 2. Wait\n'
                                 '\n'
                                 'wait.\n'
                                 '\n'
                                 '## 3. Upload again\n'
                                 '\n'
                                 'try again.\n'
                                 '\n'
                                 '## 4. Check\n'
                                 '\n'
                                 'check it.\n'
                                 '\n'
                                 '## 5. Report\n'
                                 '\n'
                                 'report it.\n'),
 'number-words': ('The pilot has thirty users in twenty-five teams, a dozen sites and one hundred '
                  'licences. No one objected, and one of the sites closes at noon.\n',
                  'The pilot has 30 users in 25 teams, 12 sites and 100 licences. Nobody '
                  'objected.\n'),
 'zh-number-words': ('试点有三十人，分成两组，共三家门店、五条线路，预算一万二千元。大家有一点担心，等一天再说。\n',
                     '试点有30人，分成2组，共3家门店、5条线路，预算12000元。大家有些担心。\n'),
 'title-and-surname': ('The review was led by Dr. Boateng. Dr. Boateng asked for a second '
                       'sample.\n',
                       'The review asked for a second sample.\n'),
 'opener-glued-to-name': ('After Dmitri left, the build broke. Thanks Ana for fixing it.\n',
                          'The build broke after Dmitri left; thanks to Ana for fixing it.\n'),
 'interior-ordinary-capitals': ('Decision: Ship the fix on Monday. Status: Done. I think I’m fine '
                                'with that, and I’ll confirm by 3 PM.\n',
                                'We ship the fix on Monday; it is done. I am fine with that and '
                                'will confirm by 3 pm.\n'),
 'name-only-at-sentence-start': ('Priya signed off the budget on Monday. Okafor will send the '
                                 'contract.\n'
                                 '\n'
                                 'The team meets again next week.\n',
                                 'The budget was signed off. The team meets again next week.\n'),
 'name-only-in-heading-and-table': ('## Notes from Ingrid\n'
                                    '\n'
                                    '| Owner | Task |\n'
                                    '|---|---|\n'
                                    '| Rafael | book the room |\n'
                                    '\n'
                                    'the room is booked for next week.\n',
                                    '## Notes\n\nthe room is booked for next week.\n'),
 'name-is-a-month-or-word': ('We asked May and June Okoro to review it, and Will agreed to help.\n',
                             'We asked for a review.\n'),
 'en': ('# Tidewell weekly product sync — 14 May 2027\n'
        '\n'
        'Attendees: Ingrid Vasquez (chair), Oluwaseun Adeyemi, Hana Kobayashi, Rafael Monteiro, '
        'Dr. Ama Boateng (guest, Northgate Clinic). Apologies: Callum Reid.\n'
        '\n'
        '## 1. Release status\n'
        '\n'
        'Harbor Ledger 3.2.0 shipped on Tuesday to 1,150 accounts. Oluwaseun reported 38 support '
        'tickets in the first 48 hours, of which 9 were about the new export screen. Hana said the '
        'crash rate fell from 2.4% to 0.7%. Version 3.2.1 is planned for 21 May and fixes the '
        '"blank invoice" bug that Rafael found in Lisbon during the partner demo.\n'
        '\n'
        'Release notes are at https://example.com/tidewell/releases/3.2.0 and the ticket board is '
        'at https://example.com/tidewell/board/. Callum left a comment asking whether `ledger '
        'migrate --dry-run` should be the default.\n'
        '\n'
        '## 2. Pricing experiment\n'
        '\n'
        'Ingrid presented the numbers. The Starter plan stays at $19 per month. The Team plan '
        'moves from $49 to $59 per month for new customers in Canada and Portugal only. Rafael '
        'thinks the increase is too high; he quoted a customer in Porto who said "we would rather '
        'pay per seat". Ingrid wants three weeks of data before deciding. The test covers 400 '
        'trial accounts and ends on 4 June.\n'
        '\n'
        "I'm not convinced the sample is big enough, Hana said, and Oluwaseun agreed. Dr. Boateng "
        'noted that Northgate Clinic pays CAD 7,080 a year for twelve seats and would accept a '
        'small increase if offline mode arrives first.\n'
        '\n'
        '## 3. Offline mode\n'
        '\n'
        'Hana demoed the prototype. Sync takes about 6 seconds for 500 records and 45 seconds for '
        '10,000. The storage limit on older iPads is 50 MB, which is enough for roughly two years '
        'of entries. Oluwaseun asked for a setting called "sync on Wi-Fi only". Monteiro\'s team '
        'will test it in the Lisbon office next week.\n'
        '\n'
        'Run the prototype with:\n'
        '\n'
        '    harbor dev --offline --seed 42\n'
        '\n'
        'Design files: https://example.net/tidewell/offline-mode\n'
        '\n'
        '## 4. Hiring\n'
        '\n'
        'Two engineers start on 1 June. Ama Boateng offered to introduce a pharmacist who could '
        'advise on the clinic workflow. Budget for the contractor is EUR 12,500 through '
        'September.\n'
        '\n'
        '## Actions\n'
        '\n'
        '| Action | Owner | Due |\n'
        '|---|---|---|\n'
        '| Publish the 3.2.1 changelog | Oluwaseun Adeyemi | 20 May |\n'
        '| Send the pricing summary to finance@example.com | Ingrid Vasquez | 18 May |\n'
        '| Book the Lisbon test room | Rafael Monteiro | 17 May |\n'
        '| Draft the "sync on Wi-Fi only" copy | Hana Kobayashi | 24 May |\n'
        '\n'
        'Next meeting: Friday 21 May, 10:00, in the Kelp Room.\n',
        '# Tidewell product sync, 14 May 2027\n'
        '\n'
        'Present: Ingrid Vasquez (chair), Oluwaseun Adeyemi, Hana Kobayashi, Rafael Monteiro and '
        'guest Dr. Ama Boateng. Callum Reid sent apologies.\n'
        '\n'
        '## Decisions and actions\n'
        '\n'
        '| Action | Owner | Due |\n'
        '|---|---|---|\n'
        '| Book the Lisbon test room | Rafael Monteiro | 17 May |\n'
        '| Send the pricing summary to finance@example.com | Ingrid Vasquez | 18 May |\n'
        '| Publish the 3.2.1 changelog | Oluwaseun Adeyemi | 20 May |\n'
        '\n'
        '## Release\n'
        '\n'
        'Since Tuesday, Harbor Ledger 3.2.0 has been live for 1150 accounts; the crash rate '
        'dropped from 2.4% to 0.7%, according to Hana. Of the 38 support tickets Oluwaseun '
        "counted, 9 concerned the new export screen. A fix for the 'blank invoice' bug, which "
        'Rafael found during the partner demo, ships in 3.2.1 on 21 May. Notes: '
        'https://example.com/tidewell/releases/3.2.0; board: https://example.com/tidewell/board.\n'
        '\n'
        '## Pricing\n'
        '\n'
        'Starter remains $19 a month, while Team rises to $59 for new customers in Canada and '
        'Portugal. Rafael considers that too steep, and Ingrid will decide after 3 weeks of data '
        'from the 400 trial accounts. Hana and Oluwaseun doubt the sample is large enough. '
        'Northgate Clinic, which pays CAD 7,080 a year, would accept a small increase once offline '
        'mode exists.\n'
        '\n'
        '## Offline mode\n'
        '\n'
        "In Hana's prototype, 500 records sync in about 6 seconds. Older iPads allow 50 MB of "
        'storage, roughly 2 years of entries. Oluwaseun requested a “sync on Wi-Fi only” setting, '
        'and the Lisbon office tests it next week. To run it:\n'
        '\n'
        '```\n'
        'harbor dev --offline --seed 42\n'
        '```\n'
        '\n'
        '## Hiring\n'
        '\n'
        'Two engineers join on 1 June. The contractor budget is EUR 12,500.\n'
        '\n'
        'Next meeting: 21 May, 10:00, Kelp Room.\n'),
 'zh': ('# 「拾光记账」３．６版更新说明\n'
        '\n'
        '发布日期：２０２７年５月２０日。本次更新由产品负责人沈知遥牵头，后端由 Viktor Hallberg 的小组完成，设计来自合作工作室 Moss & Lantern。\n'
        '\n'
        '## 新功能\n'
        '\n'
        '- 多账本：一个账号最多可以建５个账本，每个账本可邀请８位成员。免费版仍然只有１个账本。\n'
        '- 汇率自动换算：支持１６种货币，汇率每天早上６点更新一次，数据来自 OpenRate。\n'
        '- 发票识别：拍一张照片，就能识别金额和日期。内测时识别准确率是９２．５％，共测试了３，０００张发票。\n'
        '- 新增深色主题“夜航”和浅色主题“晨雾”。\n'
        '\n'
        '## 修复的问题\n'
        '\n'
        '1. 修复了导出 CSV 时金额超过１００，０００元会出现乱码的问题。\n'
        '2. 修复了 iPad 横屏时底部按钮被遮住的问题，这个问题由用户 Nadia Ferreira 最先反馈。\n'
        '3. 修复了连续记账超过３０天后提醒不再弹出的问题。\n'
        '4. 同步速度提升约４０％，１，０００条记录的同步时间从１２秒降到７秒。\n'
        '\n'
        '## 需要注意\n'
        '\n'
        '升级前请先备份。可以在设置里点「导出全部数据」，也可以在电脑上运行：\n'
        '\n'
        '```\n'
        'shiguang backup --all --out backup.zip\n'
        '```\n'
        '\n'
        '旧版（３．２及更早）需要先升级到３．４，再升级到本版。如果升级失败，运行 `shiguang repair --keep-data` 后重试。详细步骤见《升级手册》第４章，网址是 '
        'https://example.com/shiguang/upgrade/ 。\n'
        '\n'
        '会员价格不变：月付１８元，年付１６８元。Viktor Hallberg 说：“这是我们改动最大的一版，也是最稳的一版。”沈知遥补充：“下一版会把预算功能做完。”\n'
        '\n'
        '## 接下来\n'
        '\n'
        '| 计划 | 负责人 | 预计时间 |\n'
        '|---|---|---|\n'
        '| 预算功能 | 沈知遥 | ７月 |\n'
        '| 安卓平板适配 | Viktor Hallberg | ８月 |\n'
        '| 《家庭账本指南》电子书 | Nadia Ferreira | ９月 |\n'
        '\n'
        '反馈请发到 feedback@example.com，或在社区 https://example.org/shiguang/forum 留言。两位反馈最多的用户会得到一年会员。\n',
        '# 「拾光记账」3.6 版更新\n'
        '\n'
        '２０２７年５月２０日发布。产品负责人沈知遥，后端 Viktor Hallberg，设计 Moss & Lantern。\n'
        '\n'
        '## 升级须知\n'
        '\n'
        '- 升级前先备份：在设置里点“导出全部数据”，或在电脑上运行下面的命令。\n'
        '- ３．２及更早的版本要先升到３．４。\n'
        '- 步骤见《升级手册》，网址 https://example.com/shiguang/upgrade 。\n'
        '\n'
        '```\n'
        'shiguang backup --all --out backup.zip\n'
        '```\n'
        '\n'
        '## 新功能\n'
        '\n'
        '- 多账本：每个账号最多五个账本，每个账本可邀请８位成员。\n'
        '- 汇率自动换算：支持１６种货币，每天６点更新。\n'
        '- 发票识别：拍照即可识别金额和日期，内测准确率９２．５％。\n'
        '- 新主题「夜航」。\n'
        '\n'
        '## 修复\n'
        '\n'
        '- 导出 CSV 时金额超过 100000 元出现乱码。\n'
        '- iPad 横屏时底部按钮被遮住。\n'
        '- 连续记账超过３０天后提醒不再弹出。\n'
        '- 同步速度提升约４０％。\n'
        '\n'
        '## 其他\n'
        '\n'
        '会员价格不变：月付１８元，年付１６８元。Viktor Hallberg 表示，这是“改动最大的一版，也是最稳的一版”。\n'
        '\n'
        '| 计划 | 负责人 | 预计时间 |\n'
        '|---|---|---|\n'
        '| 预算功能 | 沈知遥 | ７月 |\n'
        '| 安卓平板适配 | Viktor Hallberg | ８月 |\n'
        '\n'
        '反馈请发到 feedback@example.com。\n')}

LAST_EXPECTED = {'en': [['number', '48', 'lost', 1, 0],
        ['number', '49', 'lost', 1, 0],
        ['number', '4', 'lost', 1, 0],
        ['number', '12', 'lost', 1, 0],
        ['number', '45', 'lost', 1, 0],
        ['number', '10000', 'lost', 1, 0],
        ['number', '24', 'lost', 1, 0],
        ['link', 'https://example.net/tidewell/offline-mode', 'lost', 1, 0],
        ['code', 'ledger migrate --dry-run', 'lost', 1, 0],
        ['quoted-string', 'we would rather pay per seat', 'lost', 1, 0],
        ['quoted-string', 'sync on Wi-Fi only', 'fewer', 2, 1],
        ['name', 'Porto', 'lost', 1, 0],
        ['name', 'Friday', 'lost', 1, 0],
        ['name', 'Lisbon', 'fewer', 3, 2],
        ['name', 'Northgate Clinic', 'fewer', 2, 1],
        ['name', 'Hana Kobayashi', 'fewer', 2, 1],
        ['name', 'Ama Boateng', 'fewer', 2, 1],
        ['heading', 'tidewellweeklyproductsync—14may2027', 'lost', 1, 0],
        ['heading', '1releasestatus', 'lost', 1, 0],
        ['heading', '2pricingexperiment', 'lost', 1, 0],
        ['heading', '3offlinemode', 'lost', 1, 0],
        ['heading', '4hiring', 'lost', 1, 0],
        ['table-cell', 'draftthesynconwifionlycopy', 'lost', 1, 0]],
 'zh': [['number', '1', 'lost', 1, 0],
        ['number', '3000', 'lost', 1, 0],
        ['number', '1000', 'lost', 1, 0],
        ['number', '12', 'lost', 1, 0],
        ['number', '4', 'lost', 1, 0],
        ['number', '9', 'lost', 1, 0],
        ['number', '2', 'lost', 1, 0],
        ['number', '7', 'fewer', 2, 1],
        ['link', 'https://example.org/shiguang/forum', 'lost', 1, 0],
        ['code', 'shiguang repair --keep-data', 'lost', 1, 0],
        ['quoted-string', '晨雾', 'lost', 1, 0],
        ['quoted-string', '下一版会把预算功能做完', 'lost', 1, 0],
        ['quoted-string', '家庭账本指南', 'lost', 1, 0],
        ['quoted-string', '这是我们改动最大的一版,也是最稳的一版', 'lost', 1, 0],
        ['name', 'OpenRate', 'lost', 1, 0],
        ['name', 'Nadia Ferreira', 'lost', 2, 0],
        ['heading', '拾光记账３．６版更新说明', 'lost', 1, 0],
        ['heading', '修复的问题', 'lost', 1, 0],
        ['heading', '需要注意', 'lost', 1, 0],
        ['heading', '接下来', 'lost', 1, 0],
        ['table-cell', '《家庭账本指南》电子书', 'lost', 1, 0]],
 'heading-numbers-dropped': [['heading', '1scope', 'lost', 1, 0],
                             ['heading', '2budget', 'lost', 1, 0],
                             ['heading', '3risks', 'lost', 1, 0]],
 'heading-numbers-hide-a-loss': [['number', '5', 'lost', 1, 0], ['number', '3', 'lost', 1, 0]],
 'number-words': [],
 'zh-number-words': [],
 'title-and-surname': [['name', 'Boateng', 'lost', 2, 0]],
 'opener-glued-to-name': [],
 'interior-ordinary-capitals': [],
 'name-only-at-sentence-start': [['name', 'Monday', 'lost', 1, 0]],
 'name-only-in-heading-and-table': [['heading', 'notesfromingrid', 'lost', 1, 0],
                                    ['table-cell', 'owner', 'lost', 1, 0],
                                    ['table-cell', 'rafael', 'lost', 1, 0]],
 'name-is-a-month-or-word': [['name', 'Okoro', 'lost', 1, 0], ['name', 'Will', 'lost', 1, 0]]}

LAST_MISSES = {'en': [['name', 'Friday', 'lost', 1, 0]]}


def third_round_cases():
    """Hand-listed new pairs/probes, intentional misses and narrow regression cases."""
    cases = []

    def equal(actual, wanted):
        if actual != wanted:
            raise AssertionError(f'expected {wanted!r}, got {actual!r}')

    def rows(tool, old, new):
        return sorted([r['kind'], r['key'], r['status'], r['old_count'], r['new_count']]
                      for r in tool.analyze(old, new)['items'] if r['status'] != 'kept')

    for name, wanted in LAST_EXPECTED.items():
        def case(tool, name=name, wanted=wanted):
            old, new = LAST_FIXTURES[name]
            data = tool.analyze(old, new)
            # Keep the hand list intact and identify the intentional difference.
            reported = [r for r in wanted if r not in LAST_MISSES.get(name, [])]
            equal(rows(tool, old, new), sorted(reported))
            equal(tool.exit_status(data), int(bool(wanted)))
            name_keys = {r['key'] for r in data['items'] if r['kind'] == 'name'}
            if name == 'opener-glued-to-name':
                equal(name_keys, {'Dmitri', 'Ana'})
            elif name == 'title-and-surname':
                equal(name_keys, {'Boateng'})
            elif name == 'interior-ordinary-capitals':
                equal(name_keys, {'Monday'})
            elif name == 'name-only-at-sentence-start':
                equal(name_keys, {'Monday'})  # Priya and Okafor intentionally missed.
            elif name == 'name-only-in-heading-and-table':
                equal(name_keys, set())  # Still covered by the structural checks.
            elif name == 'name-is-a-month-or-word':
                equal(name_keys, {'Okoro', 'Will'})  # May/June intentionally excluded.
            if name == 'en':
                versions = [(r['key'], r['old_count'], r['new_count']) for r in data['items']
                            if r['kind'] == 'number' and r['key'].startswith('3.2')]
                equal(versions, [('3.2.0', 2, 2), ('3.2.1', 2, 2)])
                equal(name_keys & {'Dr', 'CAD', 'EUR', "I'm", 'Wi-Fi'}, set())
                equal(name_keys & {'Friday'}, set())  # Single label value intentionally missed.
            elif name == 'zh':
                equal(name_keys & {'CSV'}, set())
            elif name == 'number-words':
                equal(data['counts']['number']['old'], 0)
            elif name == 'zh-number-words':
                equal(data['counts']['number']['old'], 0)  # 组/家/条 are not supported quantity suffixes.
        cases.append(('second blind ' + name, case))

    def heading_variants(tool):
        for old, new in [('## 1、重试\n等待５次', '## ５、结果\n结束'),
                         ('## 1. Retry\nwait 5 times', '## 5. Result\nend')]:
            equal([r for r in rows(tool, old, new) if r[0] == 'number'],
                  [['number', '5', 'lost', 1, 0]])
        equal([s['key'] for s in tool.fact_spans('## ４、标题\n## 一、标题\n## 2. Scope\nwait 3 minutes')
               if s['kind'] == 'number'], ['3'])
    cases.append(('heading numbering in both languages cannot match quantities', heading_variants))

    def versions(tool):
        equal([r for r in rows(tool, 'version 3.2.1', 'version 3.2 plus 1') if r[0] == 'number'],
              [['number', '3.2.1', 'lost', 1, 0]])
        equal([s['key'] for s in tool.fact_spans('３．２．１ 3.2.0 3.2.10') if s['kind'] == 'number'],
              ['3.2.1', '3.2.0', '3.2.10'])
    cases.append(('versions remain whole dotted items', versions))

    def ambiguous_one(tool):
        equal([s for s in tool.fact_spans('No one objected; one of the sites; One hour; 一点担心，一天再说，一小时')
               if s['kind'] == 'number'], [])
        equal(rows(tool, '1 hour', 'one hour'), [['number', '1', 'lost', 1, 0]])
    cases.append(('one and 一 excluded in both texts including genuine counts', ambiguous_one))

    def titles(tool):
        for title in ('Dr.', 'Mr.', 'Ms.', 'Mrs.', 'Prof.'):
            equal(rows(tool, title + ' Boateng agreed.', 'gone'), [['name', 'Boateng', 'lost', 1, 0]])
    cases.append(('five titles support following surnames without becoming names', titles))

    def ordinary_capitals(tool):
        equal([s for s in tool.fact_spans("Decision: Ship. Status: Done. with I'm and I’ll; CAD 7, EUR 8, CSV and 3 PM")
               if s['kind'] == 'name'], [])
        # Multiword names after colons are still evidence, not label values.
        equal([s['key'] for s in tool.fact_spans('Attendees: Neri Vale') if s['kind'] == 'name'], ['Neri Vale'])
    cases.append(('label values contractions currencies and file units excluded', ordinary_capitals))

    def quote_names(tool):
        for old, new, state, before, after in [('"Neri Vale"', 'gone', 'lost', 1, 0),
                                             ('"Neri Vale" "Neri Vale"', 'Neri Vale', 'fewer', 2, 1)]:
            equal(rows(tool, old, new), [['quoted-string', 'Neri Vale', state, before, after]])
        equal([r['key'] for r in tool.analyze('with Neri Vale; "Neri Vale"', 'gone')['items']
               if r['kind'] == 'name'], ['Neri Vale'])
        equal([r['key'] for r in tool.analyze('"Neri Vale"', 'Neri Vale')['items']
               if r['kind'] == 'name'], ['Neri Vale'])
    cases.append(('lost and fewer quotations cover contained names only', quote_names))

    def uncertainty(tool):
        line = tool.summary(tool.analyze('with Neri Vale', 'gone'))
        if '1 tentative names' not in line or '; lost: 1 tentative name' not in line:
            raise AssertionError('names must be last and labelled tentative in the summary')
    cases.append(('summary marks names tentative', uncertainty))
    return cases



def fix_round_cases():
    """The checker's hand list and narrow regressions; also runnable on the old script."""
    import contextlib
    import io
    base = Path(__file__).resolve().parent.parent / 'examples'
    expected = BLIND_EXPECTED
    cases = []

    def equal(actual, wanted):
        if actual != wanted:
            raise AssertionError(f'expected {wanted!r}, got {actual!r}')

    def rows(tool, old, new):
        return [[r['kind'],r['key'],r['status'],r['old_count'],r['new_count']]
                for r in tool.analyze(old,new)['items'] if r['status']!='kept']

    for lang in ('en','zh'):
        def pair(tool, lang=lang):
            old = BLIND_FIXTURES[lang+'-old']
            new = BLIND_FIXTURES[lang+'-new']
            equal(sorted(rows(tool,old,new)), sorted(expected[lang]))
            names = {r['key'] for r in tool.analyze(old,new)['items'] if r['kind']=='name'}
            wanted_names = {'Lantern Desk','Priya Okafor','Tomas Lindqvist','VPN','Beacon Hub','Parcel Bot','Mei-Ling Castellanos'} if lang=='en' else {'Lena Hoffmann','Paper Kite Studio','Marco Bellini'}
            equal(names,wanted_names)
        cases.append(('blind '+lang+': every hand-listed loss/fewer and only the listed names',pair))
    probe_expected = {'listmarker':[['number','5','lost',1,0],['number','3','lost',1,0]],
                      'fence-indent':[], 'email':[['link','duty@example.com','lost',1,0]], 'opener':[]}
    for name,wanted in probe_expected.items():
        def probe(tool,name=name,wanted=wanted):
            old=BLIND_FIXTURES[name+'-old']
            new=BLIND_FIXTURES[name+'-new']
            equal(sorted(rows(tool,old,new)),sorted(wanted))
            equal(tool.exit_status(tool.analyze(old,new)),int(bool(wanted)))
            if name=='fence-indent':
                for indent in ('   ','    ','\t'):
                    nested='10. export:\n\n'+indent+'```\n'+indent+'  fogctl export\n'+indent+'```'
                    plain='```\n  fogctl export\n```'
                    equal(rows(tool,nested,plain),[])
        cases.append(('checker probe '+name,probe))

    def numeric_words(tool):
        for old,new,key in [('4 hours','four hours','4'),('四小时','４小时','4'),
                            ('twenty times','20 times','20'),('零次、二十小时','0次、20小时','0')]:
            data=tool.analyze(old,new)
            equal([(r['key'],r['status']) for r in data['items'] if r['kind']=='number' and r['key']==key],[(key,'kept')])
        equal(rows(tool,'wait One hour','wait 1 hour'),[])
        equal([s for s in tool.fact_spans('twenty-one hours; one hundred and two hours; 二十一小时；两点五小时；第二包；《会员日十问》') if s['kind']=='number'],[])
    cases.append(('English and Chinese small-number spellings',numeric_words))

    def markers(tool):
        text='1. upload\n２． wait\n3) retry\n(4) check\n５、报告\n等待５次'
        equal([(s['key'],s['value']) for s in tool.fact_spans(text) if s['kind']=='number'],[('5','５')])
    cases.append(('list marker variants in both languages are not quantities',markers))

    def parents(tool):
        data=tool.analyze('https://example.org/poster-v3 `fogctl --retry 7`','gone')
        equal([r for r in data['items'] if r['kind']=='number'],[])
        # A standalone quantity must survive suppression of the same digits in a lost parent.
        equal(rows(tool,'3 hours; https://example.org/poster-v3','gone'),
              [['number','3','lost',1,0],['link','https://example.org/poster-v3','lost',1,0]])
    cases.append(('numbers inside lost links/code are covered by their parent item',parents))

    def quote_punctuation(tool):
        for old,new,key in [('“宁可慢，不要错。”','“宁可慢，不要错”。','宁可慢,不要错'),
                            ('"fog gate,"','"fog gate",','fog gate'),('"fog gate."','"fog gate".','fog gate')]:
            equal([(r['key'],r['status']) for r in tool.analyze(old,new)['items'] if r['kind']=='quoted-string'],[(key,'kept')])
    cases.append(('closing full stop and comma can move outside quotation marks',quote_punctuation))

    def counts(tool):
        data=tool.analyze('with Mira Sedge; Mira Sedge; "amber" "amber"; 8 8','gone')
        for kind,c in data['counts'].items():
            group=[r for r in data['items'] if r['kind']==kind]
            equal(c['old'],len(group))
            for state in ('kept','lost','fewer'):
                equal(c[state],sum(r['status']==state for r in group))
        equal(data['counts']['name']['lost'],1)
        if not tool.summary(data).startswith('distinct items · '):
            raise AssertionError('summary must state distinct-item counting')
    cases.append(('summary counts distinct rows while item records retain mentions',counts))

    def language(tool):
        old,new='这是中文测试。','这是改写文本。'
        data=tool.analyze(old,new); data.update(old_file='old.md',new_file='new.md')
        if '<html lang="zh">' not in tool.render_html(data,old,new):
            raise AssertionError('Chinese report needs lang=zh')
    cases.append(('Chinese HTML language',language))

    def cli_case(tool,mode):
        with tempfile.TemporaryDirectory(prefix='coverage-fix-',dir=Path.cwd()) as tmp:
            previous=Path.cwd()
            try:
                os.chdir(tmp)
                Path('old.md').write_text('`fogctl seal`',encoding='utf-8')
                Path('new.md').write_text('gone',encoding='utf-8')
                out,err=io.StringIO(),io.StringIO()
                if mode=='default':
                    Path('rewrite-coverage.html').write_bytes(b'existing report sentinel')
                    args=['old.md','new.md']
                elif mode=='directory':
                    args=['.','new.md','--html','report.html']
                else:
                    args=['old.md','new.md','--html','report.html']
                with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                    rc=tool.main(args)
                if mode=='default':
                    equal(rc,2); equal(Path('rewrite-coverage.html').read_bytes(),b'existing report sentinel')
                    if 'explicit --html' not in err.getvalue():
                        raise AssertionError('refusal must tell the user to choose a report')
                elif mode=='directory':
                    equal(rc,2)
                    if not err.getvalue().startswith('.:') or 'directory' not in err.getvalue():
                        raise AssertionError('directory refusal needs a nonempty name and a plain explanation')
                else:
                    equal(rc,1)
                    if 'every old item' in out.getvalue() or 'every structural item' not in out.getvalue():
                        raise AssertionError('structural-only success must be explicitly scoped')
            finally:
                os.chdir(previous)
    for mode in ('default','directory','structural wording'):
        cases.append(('CLI '+mode,lambda tool,mode=mode:cli_case(tool,mode)))

    def demo_openings(tool):
        old=(base/'english-old.md').read_text(encoding='utf-8')
        expected_demo=json.loads((base/'expected.json').read_text(encoding='utf-8'))['english']
        for filename in ('english-new.md','english-new-openings.md'):
            new=(base/filename).read_text(encoding='utf-8')
            equal(sorted(rows(tool,old,new)),sorted(expected_demo))
    cases.append(('bundled English rewrites change sentence openings without false names',demo_openings))
    return cases


def selftest():
    """Behavior checks and controlled rule-disable runs, all under the cwd."""
    import contextlib
    import io
    from html.parser import HTMLParser
    from unittest.mock import patch
    checks = []

    def equal(actual, expected):
        if actual != expected:
            raise AssertionError(f'expected {expected!r}, got {actual!r}')

    def true(value, message):
        if not value:
            raise AssertionError(message)

    def check(label, fn):
        try:
            fn()
        except Exception as exc:
            checks.append((label, False, str(exc)))
        else:
            checks.append((label, True, ''))

    def rule(label, fn, replacements):
        check(label, fn)
        def disabled():
            with patch.dict(globals(), replacements):
                try:
                    fn()
                except AssertionError as exc:
                    return str(exc)
            raise AssertionError('case still passed with the rule switched off')
        try:
            evidence = disabled()
            checks.append(('MUTATION CAUGHT ' + label, True, evidence))
        except Exception as exc:
            checks.append(('MUTATION CAUGHT ' + label, False, str(exc)))

    def row(old, new, kind, key):
        rs = [r for r in analyze(old, new)['items'] if r['kind'] == kind and r['key'] == key]
        true(len(rs) == 1, f'{kind} {key!r}: expected one item, got {len(rs)}')
        return rs[0]

    def verdict(old, new, kind, key, expected):
        r = row(old, new, kind, key)
        equal((r['status'], r['old_count'], r['new_count']), expected)

    original_facts = fact_spans
    number_key_original, link_key_original, literal_count_original = number_key, link_key, literal_count
    for kind, old, key in (('number', '73', '73'), ('link', 'https://example.org/missing', 'https://example.org/missing'),
                           ('code', '`fogctl seal`', 'fogctl seal'), ('quoted-string', '“amber gate”', 'amber gate'),
                           ('name', 'Mira Sedge', 'Mira Sedge')):
        rule('extract and report lost ' + kind,
             lambda k=kind, o=old, v=key: verdict(o, 'nothing remains', k, v, ('lost', 1, 0)),
             {'fact_spans': lambda t, k=kind: [s for s in original_facts(t) if s['kind'] != k]})
    rule('full-width digits and punctuation', lambda: verdict('值１，０００', '值1,000', 'number', '1000', ('kept', 1, 1)),
         {'number_key': lambda v: v.replace(',', '')})
    rule('thousands separator equivalence', lambda: verdict('1,000', '1000', 'number', '1000', ('kept', 1, 1)),
         {'number_key': width})
    def substring_facts(t):
        rs = original_facts(t)
        for s in list(rs):
            if s['kind'] == 'number' and s['key'] == '1730':
                rs.append(dict(s, key='73'))
        return rs
    rule('number inside a longer number is not a match',
         lambda: verdict('73', '1730', 'number', '73', ('lost', 1, 0)), {'fact_spans': substring_facts})
    def number_without_suffix(t):
        rs = original_facts(t)
        for s in rs:
            if s['kind'] == 'number':
                s['key'] = s['key'].rstrip('%')
        return rs
    rule('percent is part of the numeric literal', lambda: verdict('19', '19%', 'number', '19', ('lost', 1, 0)),
         {'fact_spans': number_without_suffix})
    rule('leading decimal point is part of the number', lambda: verdict('5', '.5', 'number', '5', ('lost', 1, 0)),
         {'number_key': lambda v: number_key_original(v).lstrip('.')})
    rule('decimal spelling, signs and exponent spelling remain distinct',
         lambda: equal([(s['key']) for s in fact_spans('1.0 +1 -2 1e3') if s['kind'] == 'number'], ['1.0', '+1', '-2', '1e3']),
         {'number_key': lambda v: str(float(number_key_original(v)))})
    rule('URL trailing path slash equivalence',
         lambda: verdict('https://example.org/route/', 'https://example.org/route', 'link', 'https://example.org/route', ('kept', 1, 1)),
         {'link_key': lambda v: v})
    rule('URL scheme and host case equivalence',
         lambda: verdict('HTTPS://EXAMPLE.ORG/route', 'https://example.org/route', 'link', 'https://example.org/route', ('kept', 1, 1)),
         {'link_key': lambda v: v.rstrip('/')})
    rule('URL path case is significant',
         lambda: verdict('https://example.org/route', 'https://example.org/ROUTE', 'link', 'https://example.org/route', ('lost', 1, 0)),
         {'link_key': lambda v: link_key_original(v).lower()})
    rule('URL query and fragment are significant',
         lambda: verdict('https://example.org/route?x=amber#dock', 'https://example.org/route?x=blue#gate', 'link', 'https://example.org/route?x=amber#dock', ('lost', 1, 0)),
         {'link_key': lambda v: link_key_original(v).split('?')[0].split('#')[0]})
    rule('URL stops at Chinese punctuation and words',
         lambda: verdict('在https://example.org/map，备用', 'https://example.org/map', 'link', 'https://example.org/map', ('kept', 1, 1)),
         {'fact_spans': lambda t: [dict(s, key=s['key']+'，备用') if '，备用' in t and s['kind']=='link' else s for s in original_facts(t)]})
    rule('relative Markdown links and fragment links are extracted',
         lambda: equal([s['key'] for s in fact_spans('[guide](guide.md) [dock](#dock)') if s['kind']=='link'], ['guide.md','#dock']),
         {'fact_spans': lambda t: [s for s in original_facts(t) if s['kind']!='link' or s['key'].startswith('http')]})
    rule('reference definitions and resolved uses each count',
         lambda: verdict('[guide][Dock]\n[Dock]: https://example.org/map', '[dock]: https://example.org/map\n[guide][DOCK]', 'link', 'https://example.org/map', ('kept',2,2)),
         {'fact_spans': lambda t: [s for s in original_facts(t) if s['kind']!='link' or not s['value'].startswith('https://example.org/map') or s['start']==t.index('https://')]})
    check('mailto, FTP, balanced URL parentheses and angle destinations',
          lambda: equal([s['key'] for s in fact_spans('mailto:tray@example.org ftp://example.net/pack [map](<guide.md>) https://example.org/map_(blue).') if s['kind']=='link'],
                        ['mailto:tray@example.org','ftp://example.net/pack','guide.md','https://example.org/map_(blue)']))
    check('malformed URL literal does not crash', lambda: verdict('https://[fiction', 'other', 'link', 'https://[fiction', ('lost',1,0)))
    check('explicit Markdown destination preserves Han URL paths',
          lambda: verdict('[图](https://example.org/虚构图)', '[地址](<https://example.org/虚构图>)', 'link', 'https://example.org/虚构图', ('kept',1,1)))
    rule('inline, fenced and indented code share exact contents',
         lambda: verdict('`fogctl check`', '```sh\nfogctl check\n```\n\n    fogctl check\n', 'code', 'fogctl check', ('kept', 1, 2)),
         {'code_spans': lambda t: [(m.start(1), m.end(1), m[1]) for m in re.finditer(r'(?<!`)`([^`]+)`(?!`)', t)]})
    rule('code keeps whitespace and case',
         lambda: verdict('`fogctl  check`', '`FOGCTL check`', 'code', 'fogctl  check', ('lost', 1, 0)),
         {'code_key': lambda v: ' '.join(v.lower().split())})
    rule('code line ending equivalence',
         lambda: verdict('```\na\r\nb\r\n```', '```\na\nb\n```', 'code', 'a\nb', ('kept', 1, 1)),
         {'code_key': lambda v: v})
    rule('double backtick and tilde code fences',
         lambda: verdict('``fog`check``', '~~~sh\nfog`check\n~~~', 'code', 'fog`check', ('kept', 1, 1)),
         {'code_spans': lambda t: []})
    for marks in ('“amber gate”', '「amber gate」', '『amber gate』', '《amber gate》', "'amber gate'", '‘amber gate’'):
        rule('quote delimiters ' + marks,
             lambda o=marks: verdict(o, '"amber gate"', 'quoted-string', 'amber gate', ('kept', 1, 1)),
             {'fact_spans': lambda t: [s for s in original_facts(t) if s['kind'] != 'quoted-string']})
    rule('curly apostrophe inside a quote',
         lambda: verdict('“keeper’s note”', '"keeper\x27s note"', 'quoted-string', "keeper's note", ('kept', 1, 1)),
         {'literal_key': lambda v: width(v).replace('\r\n', '\n').replace('\r', '\n')})
    rule('full-width Latin name equivalence',
         lambda: verdict('Ｎｅｒｉ Ｖａｌｅ', 'Neri Vale', 'name', 'Neri Vale', ('kept', 1, 1)),
         {'literal_key': lambda v: v.translate(SMART)})
    rule('quoted contents may be retained without quote marks',
         lambda: verdict('“amber gate”', 'the amber gate is open', 'quoted-string', 'amber gate', ('kept', 1, 1)),
         {'literal_count': lambda k, t, boundary=False: sum(s['key'] == k and s['kind']=='quoted-string' for s in original_facts(t))})
    rule('quoted whitespace and case remain exact',
         lambda: verdict('"amber gate"', '"Amber  gate"', 'quoted-string', 'amber gate', ('lost', 1, 0)),
         {'literal_count': lambda k, t, boundary=False: int(' '.join(k.lower().split()) in ' '.join(t.lower().split()))})
    rule('Latin boundaries on quoted contents and names',
         lambda: verdict('"amber"', 'chamber', 'quoted-string', 'amber', ('lost', 1, 0)),
         {'literal_count': lambda k, t, boundary=False: literal_count_original(k, t, False)})
    rule('capitalised Latin name inside Chinese text',
         lambda: verdict('由Neri Vale保管', '交给Neri Vale后归档', 'name', 'Neri Vale', ('kept', 1, 1)),
         {'fact_spans': lambda t: [s for s in original_facts(t) if s['kind'] != 'name']})
    rule('names are case-sensitive',
         lambda: verdict('Neri Vale', 'neri vale', 'name', 'Neri Vale', ('lost', 1, 0)),
         {'literal_count': lambda k, t, boundary=False: len(re.findall(re.escape(k), literal_key(t), re.I))})
    rule('single names, acronyms and apostrophe names',
         lambda: equal([s['key'] for s in fact_spans("with Neri arrived; FOG stood; O'Vale signed") if s['kind']=='name'], ['Neri', 'FOG', "O'Vale"]),
         {'fact_spans': lambda t: [s for s in original_facts(t) if s['kind'] != 'name']})
    rule('accented Latin names are whole names',
         lambda: verdict('由Énora Vélan保管', 'Énora Vélan签字', 'name', 'Énora Vélan', ('kept',1,1)),
         {'fact_spans': lambda t: [s for s in original_facts(t) if s['kind']!='name' or s['value'].isascii()]})
    rule('common sentence openers do not flood names',
         lambda: equal([s['value'] for s in fact_spans('with The tray. with This folder. 这是林雾舟。普通中文。') if s['kind']=='name'], []),
         {'COMMON_OPENERS': frozenset()})
    for kind, old, new, key in (('number', '8 8 8', '8', '8'), ('link', 'https://example.org/a '*3, 'https://example.org/a', 'https://example.org/a'),
                               ('code', '`fogctl` '*3, '`fogctl`', 'fogctl'), ('quoted-string', '「青色副本」'*3, '“青色副本”', '青色副本'),
                               ('name', 'Mira Sedge; '*3, 'Mira Sedge', 'Mira Sedge')):
        rule('fewer versus lost for ' + kind, lambda k=kind,o=old,n=new,v=key: verdict(o,n,k,v,('fewer',3,1)),
             {'status_for': lambda a,b: 'kept' if b else 'lost'})
    check('fewer is never also labelled kept or lost', lambda: equal(analyze('8 8 8', '8')['counts']['number'],
          {'old':1, 'kept':0, 'lost':0, 'fewer':1, 'missing':2}))
    check('greater occurrence count stays kept', lambda: verdict('8', '8 8', 'number', '8', ('kept',1,2)))
    check('number and name inside a quote are independently counted',
          lambda: equal(Counter(s['kind'] for s in fact_spans('“Neri Vale has 73”')), Counter({'quoted-string':1,'name':1,'number':1})))
    check('apostrophes in ordinary words are not quotation marks',
          lambda: equal([s for s in fact_spans("the keeper's gate isn't open") if s['kind']=='quoted-string'], []))
    check('multiline quotations and quoted strings inside code',
          lambda: equal([s['key'] for s in fact_spans('“amber\ngate” `print("mist")`') if s['kind']=='quoted-string'], ['amber\ngate','mist']))
    check('selected table-cell source location excludes unrelated second-column text',
          lambda: equal(row('| label | note |\n|---|---|\n| first | amber |\n| amber | blue |', 'none', 'table-cell', 'amber')['locations'][0]['line'], 4))
    rule('legacy structural punctuation and case equivalence',
         lambda: equal(coverage('**amber gate**', 'AMBER-GATE')[1], []), {'norm': lambda t: t})
    rule('numbered tables compare the rule column',
         lambda: equal(coverage(NUMBERED_OLD,NUMBERED_NEW)[1], [('Totals are computed on the page','table-cell')]),
         {'counts_rows': lambda rows: False})
    rule('table code IDs are not row counters',
         lambda: equal(coverage(CODES_OLD,CODES_NEW)[1], [('200','table-cell')]),
         {'counts_rows': lambda rows: True})
    table_blocks_original = table_blocks
    rule('tables without a trailing pipe still count',
         lambda: equal(set(coverage(NO_TRAILING_PIPE,'nothing')[1]), {('name','table-cell'),('latency','table-cell')}),
         {'table_blocks': lambda t: (b for b in table_blocks_original(t) if all(ln.endswith('|') for ln in b))})
    rule('exit 1 when anything is lost or fewer',
         lambda: equal([exit_status(analyze(a,b)) for a,b in [('73','none'),('73 73','73'),('73','73')]], [1,1,0]),
         {'exit_status': lambda d: 0})

    class Page(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.ids, self.links, self.resources, self.texts, self.masks = [], [], [], [], []
            self.pre = -1
            self.mark = 0
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if 'id' in attrs:
                self.ids.append(attrs['id'])
            if 'href' in attrs:
                self.links.append(attrs['href'])
            if tag in ('script', 'img', 'link', 'iframe') or 'src' in attrs or any(k.startswith('on') for k in attrs):
                self.resources.append(tag)
            if tag == 'pre':
                self.pre = len(self.texts)
                self.texts.append('')
                self.masks.append([])
            if tag == 'mark':
                self.mark += 1
        def handle_endtag(self, tag):
            if tag == 'pre':
                self.pre = -1
            if tag == 'mark':
                self.mark -= 1
        def handle_data(self, text):
            if self.pre >= 0:
                self.texts[self.pre] += text
                self.masks[self.pre].extend([bool(self.mark)] * len(text))

    def source_page():
        old = '# Fog\r\n**amber gate** “amber gate 73” <script>test()</script> & 「青色副本」\rnext 73'
        new = 'fog remains'
        data = analyze(old, new)
        data.update(old_file='<old>.md', new_file='new.md')
        page = render_html(data, old, new)
        parsed = Page()
        parsed.feed(page)
        equal(parsed.texts, [old, new])
        equal(len(parsed.ids), len(set(parsed.ids)))
        equal(parsed.resources, [])
        true('default-src' in page and 'max-width:600px' in page and 'prefers-color-scheme:dark' in page, 'offline, phone or dark styles missing')
        for r in data['items']:
            if r['status'] == 'kept':
                continue
            for i, loc in enumerate(r['locations'], 1):
                equal(old[loc['start']:loc['end']], loc['text'])
                anchor = f'{r["id"]}-{i}'
                true(anchor in parsed.ids and '#'+anchor in parsed.links, 'missing location anchor or link')
                true(all(parsed.masks[0][loc['start']:loc['end']]), 'lost source characters are unmarked')
        true(all(x.startswith('#') and x[1:] in parsed.ids for x in parsed.links), 'external or broken report link')
    rule('overlapping losses mark source spans and every list link resolves', source_page,
         {'marked_source': lambda t, rows: html.escape(t)})
    check('UTF-8, CRLF and CR locations', lambda: equal(row('首行\r\n值７３\r最后', '其他', 'number', '73')['locations'][0],
          {'start':5,'end':7,'line':2,'column':2,'end_line':2,'end_column':3,'text':'７３'}))
    check('min-len affects structures only', lambda: equal(len(analyze('7 `a` "x"', 'none', 999)['items']), 3))

    ok, old_lines = legacy_selftest()
    for line in old_lines:
        checks.append(('legacy: ' + line[4:], line.startswith('  ✔'), ''))
    true(ok, 'legacy selftest failed')
    base = Path(__file__).resolve().parent.parent / 'examples'
    if base.exists():
        expectations = json.loads((base/'expected.json').read_text(encoding='utf-8'))
        for lang, expected in expectations.items():
            def demo(lang=lang, expected=expected):
                old = (base/(lang+'-old.md')).read_text(encoding='utf-8')
                new = (base/(lang+'-new.md')).read_text(encoding='utf-8')
                data = analyze(old, new)
                actual = [[r['kind'],r['key'],r['status'],r['old_count'],r['new_count']] for r in data['items'] if r['status']!='kept']
                equal(sorted(actual), sorted(expected))
                equal(exit_status(data), 1)
            check('declared exact demo set: ' + lang, demo)
    else:
        checks.append(('bundled examples exist', False, str(base)))

    with tempfile.TemporaryDirectory(prefix='coverage-selftest-', dir=Path.cwd()) as tmp:
        folder = Path(tmp)
        old_p, new_p, html_p = folder/'old.md', folder/'new.md', folder/'report.html'
        def execute(extra=(), old=old_p, new=new_p):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main([str(old), str(new), '--html', str(html_p)] + list(extra))
            return rc, out.getvalue(), err.getvalue()
        def cli_checks():
            old_p.write_text('73 73 73', encoding='utf-8')
            new_p.write_text('73', encoding='utf-8')
            rc, output, err = execute(['--json'])
            equal(rc, 1)
            equal(err, '')
            data = json.loads(output)
            equal(data['items'][0]['status'], 'fewer')
            equal(len(data['items'][0]['locations']), 3)
            first_page = html_p.read_bytes()
            execute(['--json'])
            equal(html_p.read_bytes(), first_page)
            new_p.write_text('none', encoding='utf-8')
            equal(execute()[0], 1)
            new_p.write_text('73 73 73', encoding='utf-8')
            equal(execute()[0], 0)
            equal(old_p.read_text(), '73 73 73')
            ledger = folder/'ledger.md'
            ledger.write_text('- 73 [dropped] invented reason', encoding='utf-8')
            new_p.write_text('none', encoding='utf-8')
            equal(execute(['--ledger',str(ledger)])[0], 1)
        check('CLI JSON, lost/fewer/kept exits, ledger annotation, deterministic page and unchanged input', cli_checks)

        def refusal_checks():
            old_p.write_text('invented text', encoding='utf-8')
            new_p.write_text('other text', encoding='utf-8')
            equal(execute(old=old_p,new=old_p)[0], 2)
            true('same file' in execute(old=old_p,new=old_p)[2], 'same-file refusal missing')
            link = folder/'alias.md'
            os.link(old_p, link)
            equal(execute(new=link)[0], 2)
            link.unlink()
            link.symlink_to(old_p)
            equal(execute(new=link)[0], 2)
            for raw, message in ((b'\xff', 'UTF-8'), (b'a\x00b','UTF-8'), (b' \r\n\t', 'empty')):
                new_p.write_bytes(raw)
                rc, out, err = execute()
                equal(rc, 2)
                equal(out, '')
                true(message in err and len(err.strip().splitlines())==1, 'refusal must be one plain sentence')
            new_p.write_bytes(b'\xef\xbb\xbf')
            equal(execute()[0], 2)
            new_p.write_bytes(b'\xef\xbb\xbfinvented text')
            equal(execute()[0], 0)
            new_p.write_text('other text',encoding='utf-8')
            before = old_p.read_bytes()
            equal(execute(['--html',str(old_p)])[0], 2)
            equal(old_p.read_bytes(), before)
            equal(execute(new=folder/'missing.md')[0], 2)
        check('same path, hardlink, symlink, invalid UTF-8, binary, empty, BOM and output collision refusals', refusal_checks)

        def legacy_output():
            old_p.write_text(OLD,encoding='utf-8'); new_p.write_text(NEW,encoding='utf-8')
            listing = folder/'structural.md'
            rc, out, err = execute(['--out', str(listing)])
            equal(listing.read_text(), '- Caveats  (heading)  [ ]\n- throughput  (bold)  [ ]\n- weekdays  (bold)  [ ]\n')
            equal(coverage(OLD,NEW)[1], [('Caveats','heading'),('throughput','bold'),('weekdays','bold')])
            expected_structure = 'structure  headings 4→3  table_rows 4→3  quote_lines 1→1  chars 162→108'
            true(expected_structure in out, 'legacy structure values changed')
            expected_lines = ('old: 10 items (headings, bold terms, table cells) · unaccounted in new: 3\n'
                              + expected_structure + '\n'
                              + '  [      ] heading    Caveats\n  [      ] bold       throughput\n  [      ] bold       weekdays\n'
                              + '✘ 3 unaccounted item(s) without a verdict — decide each: [renamed], [merged], [restored], [dropped]\n')
            true(expected_lines in out, 'new CLI changed the original structural stdout block')
        check('old example structural list and hints unchanged', legacy_output)

    from types import SimpleNamespace
    current=SimpleNamespace(**globals())
    for label,fn in fix_round_cases():
        check('fix round: '+label,lambda fn=fn:fn(current))

    for label,fn in third_round_cases():
        check('last round: '+label,lambda fn=fn:fn(current))

    passed = sum(ok for _, ok, _ in checks)
    print(f'rewrite_coverage selftest · {passed}/{len(checks)} passed')
    for label, ok, detail in checks:
        print(('PASS ' if ok else 'FAIL ') + label + (': ' + detail if detail else ''))
    return 0 if passed == len(checks) else 2


if __name__ == '__main__':
    sys.exit(main())

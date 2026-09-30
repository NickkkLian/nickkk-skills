#!/usr/bin/env python3
"""rewrite_coverage.py — after rewriting a long document, list what the old version had that the new one no longer
mentions, and require a three-state ledger for each item. A percentage is not the criterion; the ledger is.

    python3 rewrite_coverage.py <old.md> <new.md> [--min-len 3] [--ledger LEDGER.md] [--out unaccounted.md]
    python3 rewrite_coverage.py --selftest

What it extracts from the old document: headings, bold terms (**…**), and one cell per table row: the first, or the
second when the table's first column only counts its rows (1, 2, 3 … in order). A first column of codes or ids
(200, 404, #123) is not a count, so it is compared as it is.
An item is "unaccounted" when its normalised text does not occur anywhere in the new document. The list is the
product: every line on it needs a human verdict in the ledger, one of
    [renamed]   the same content under other words        [merged]   folded into another section
    [restored]  it was lost and has been put back          [dropped]  removed on purpose, with a reason
Exit 0 only when a --ledger is given and every unaccounted item carries one of those tags. Without --ledger the
exit code is 1 whenever the list is non-empty — "there is work to do", not "the rewrite is bad".
Structure hints (headings / table rows / quote lines / non-space characters, old vs new) flag two failure shapes the
existence test cannot see: a term dump (all the words, none of the structure) and a truncated new file (the new
text is far shorter). Hints are printed, never scored. What it cannot see: content moved to the wrong section;
quotations that are no longer verbatim; a new file that is complete but wrong; a change in any other cell of a table
row (each row is compared by one cell).
"""
import os, re, sys, tempfile

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


def report(old_p, new_p, min_len=3, ledger_p=None, out_p=None):
    if os.path.realpath(old_p) == os.path.realpath(new_p):
        return 2, ["old and new are the same file — nothing to compare (a 100% result here would be meaningless)"]
    old, new = open(old_p, encoding="utf-8").read(), open(new_p, encoding="utf-8").read()
    if not old.strip() or not new.strip():
        return 2, ["one of the files is empty"]
    its, un, so, sn = coverage(old, new, min_len)
    lines = [f"old: {len(its)} items (headings, bold terms, table cells) · unaccounted in new: {len(un)}"]
    lines.append("structure  " + "  ".join(f"{k} {so[k]}→{sn[k]}" for k in so))
    ratio = sn["chars"] / max(1, so["chars"])
    if ratio < 0.6:
        lines.append(f"⚠️ new text has {ratio:.0%} of the old characters — check for truncation before anything else")
    if sn["headings"] == 0 and so["headings"] > 2:
        lines.append("⚠️ new text has no headings while the old had several — a term dump keeps words and loses structure")
    verdicts = ledger_verdicts(open(ledger_p, encoding="utf-8").read()) if ledger_p else {}
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
    if ledger_p and not missing_verdict:
        lines.append(f"✔ all {len(un)} unaccounted items have a ledger verdict")
        return 0, lines
    lines.append(f"✘ {len(missing_verdict) if ledger_p else len(un)} unaccounted item(s) without a verdict — decide each: {', '.join(TAGS)}")
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


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory() as d:
        o, n, l = os.path.join(d, "old.md"), os.path.join(d, "new.md"), os.path.join(d, "ledger.md")
        open(o, "w").write(OLD); open(n, "w").write(NEW)
        its, un, so, sn = coverage(OLD, NEW)
        names = {k for k, _ in un}
        chk(names == {"Caveats", "throughput", "weekdays"}, f"unaccounted = Caveats (heading), throughput (table cell), weekdays (bold): {sorted(names)}")
        chk("frobnicator" not in names, "a term that lost its bold but is still present is accounted")
        rc, out = report(o, n)
        chk(rc == 1 and any("without a verdict" in x for x in out), "no ledger → exit 1 with the list")
        open(l, "w").write("- Caveats [merged] into Setup\n- throughput [dropped] duplicate of a chart\n- weekdays [restored]\n")
        rc, out = report(o, n, ledger_p=l)
        chk(rc == 0 and any("all 3 unaccounted items have a ledger verdict" in x for x in out), "complete ledger → exit 0")
        open(l, "w").write("- Caveats [merged]\n- weekdays [restored]\n")
        rc, out = report(o, n, ledger_p=l)
        chk(rc == 1 and any("1 unaccounted item(s) without a verdict" in x for x in out), "ledger missing one verdict → exit 1 naming the count")
        open(n, "w").write(OLD)
        rc, out = report(o, n)
        chk(rc == 0 and any(x.startswith("✔ every old item") for x in out), "identical content → exit 0 (with the caveat printed)")
        open(n, "w").write(OLD[:len(OLD) // 3])
        rc, out = report(o, n)
        chk(any("truncation" in x for x in out), "a much shorter new file prints the truncation hint")
        open(n, "w").write("Title Setup Results Caveats frobnicator cold start metric latency throughput weekdays quoted line " * 3 + "\n")
        rc, out = report(o, n)
        chk(rc == 0 and any("term dump" in x for x in out), "a term dump passes the existence test but prints the structure hint (the known limit)")
        rc, out = report(o, o)
        chk(rc == 2, "old == new file → exit 2 (a meaningless 100%)")
        its2, un2, _, _ = coverage(NUMBERED_OLD, NUMBERED_NEW)
        chk([k for k, _ in un2] == ["Totals are computed on the page"] and "Keep one token file" in its2,
            f"a numbered table's rule text is compared, not its row number: {[k for k, _ in un2]}")
        its4, un4, _, _ = coverage(CODES_OLD, CODES_NEW)
        chk([k for k, _ in un4] == ["200"], f"a first column of codes is not a row count: deleting the 200 row is reported ({[k for k, _ in un4]})")
        its3, un3, _, _ = coverage(NO_TRAILING_PIPE, "nothing here")
        chk({k for k, _ in un3} == {"name", "latency"}, f"rows without a closing pipe are still read: {sorted(k for k, _ in un3)}")
    return ok, lines


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__); return 2
    ok, lines = selftest()
    if "--selftest" in argv or not ok:
        print(f"rewrite_coverage selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    pos, opts, i = [], {"--min-len": "3", "--ledger": None, "--out": None}, 0
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]] = argv[i + 1]; i += 2
        else:
            pos.append(argv[i]); i += 1
    if len(pos) != 2:
        print(__doc__); return 2
    rc, out = report(pos[0], pos[1], int(opts["--min-len"]), opts["--ledger"], opts["--out"])
    print("\n".join(out)); return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

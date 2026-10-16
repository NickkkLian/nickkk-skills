#!/usr/bin/env python3
"""Offline contact reconciliation. Python 3.9+, standard library only."""
import argparse
import base64
import collections
import csv
import decimal
import hashlib
import html
import io
import itertools
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
EMPTY = {'', '-', '/', 'n/a', 'na', 'null', 'none', '无', '無', 'nil', '—', '--'}
TITLES = {'dr', 'mr', 'mrs', 'ms', 'prof'}
SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv'}
CALLING_CODES = set('1 7 20 27 30 31 32 33 34 36 39 40 41 43 44 45 46 47 48 49 51 52 53 54 55 56 57 58 60 61 62 63 64 65 66 81 82 84 86 90 91 92 93 94 95 98 211 212 213 216 218 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 248 249 250 251 252 253 254 255 256 257 258 260 261 262 263 264 265 266 267 268 269 290 291 297 298 299 350 351 352 353 354 355 356 357 358 359 370 371 372 373 374 375 376 377 378 380 381 382 383 385 386 387 389 420 421 423 500 501 502 503 504 505 506 507 508 509 590 591 592 593 594 595 596 597 598 599 670 672 673 674 675 676 677 678 679 680 681 682 683 685 686 687 688 689 690 691 692 850 852 853 855 856 880 886 960 961 962 963 964 965 966 967 968 970 971 972 973 974 975 976 977 992 993 994 995 996 998'.split())


class Refused(ValueError):
    """An input needs a user decision rather than a guess."""


def nfkc(value):
    return unicodedata.normalize('NFKC', str(value))


def present(value):
    return nfkc(value).strip().lower() not in EMPTY


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', nfkc(value).casefold())
                   if not unicodedata.combining(c))


def key(value):
    return ''.join(c for c in fold(value) if c.isalnum())


def cjk(value):
    return any('\u3400' <= c <= '\u9fff' or '\U00020000' <= c <= '\U0003134f' for c in value)


def load_pinyin():
    data = json.loads((ROOT / 'references/pinyin.json').read_text(encoding='utf-8'))
    return data['readings'], data['compound_surnames']


PINYIN, COMPOUND = load_pinyin()


def name_info(value, organisation=False):
    text = fold(value)
    tokens = re.findall(r'[^\W_]+', text, re.UNICODE)
    if not organisation:
        tokens = [t for t in tokens if t not in TITLES]
    raw_tokens = re.findall(r'[^\W_]+', nfkc(value), re.UNICODE)
    chinese = ''.join(t for t in raw_tokens if fold(t) not in TITLES) if cjk(value) else ''
    parts, issue, surname_length = (), '', 1
    if chinese and not organisation:
        unknown = [c for c in chinese if c not in PINYIN]
        if unknown:
            issue = 'characters outside the pinyin table: ' + ''.join(dict.fromkeys(unknown))
        else:
            surname_length = 2 if any(chinese.startswith(s) for s in COMPOUND) else 1
            parts = tuple(tuple(PINYIN[c]) for c in chinese)
    return {'tokens': sorted(tokens), 'ordered_tokens': tokens, 'compact': ''.join(sorted(tokens)), 'chinese': chinese,
            'pinyin_parts': parts, 'surname_length': surname_length,
            'pinyin': pinyin_compact(value), 'issue': issue, 'organisation': organisation}


def pinyin_compact(value):
    # Keep the distinct vowel ü (v / u:) while removing tone marks. Generic
    # accent folding would incorrectly turn Lü into Lu.
    text = unicodedata.normalize('NFD', nfkc(value).casefold()).replace('u:', 'v').replace('u\u0308', 'v')
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ''.join(t for t in re.findall(r'[^\W_]+', text, re.UNICODE) if t not in TITLES)


def pinyin_match(a, b):
    """Match every supported reading without expanding their Cartesian product."""
    if bool(a['chinese']) == bool(b['chinese']):
        return None
    cn, latin = (a, b) if a['chinese'] else (b, a)
    if cn['issue'] or cn['organisation'] or latin['organisation']:
        return None
    parts, target = cn['pinyin_parts'], latin['pinyin']
    n = cn['surname_length']
    # Retain the brief's given-first form too, moving the family chunk as a
    # whole. Never reverse the individual given-name syllables.
    for ordered in (parts, parts[n:] + parts[:n]):
        positions = {0: ()}
        for readings in ordered:
            following = {}
            for start, path in positions.items():
                for reading in readings:
                    if target.startswith(reading, start):
                        following.setdefault(start + len(reading), path + (reading,))
            positions = following
            if not positions:
                break
        if not target:
            continue
        if len(target) in positions:
            return cn['chinese'], ' '.join(positions[len(target)])
    return None


def same_name_reason(a, b):
    reading = pinyin_match(a, b)
    if reading:
        return 'same name: pinyin %s romanises %s' % (reading[1], reading[0])
    return 'same name after formatting normalization'


def name_relation(a, b):
    if a['organisation'] != b['organisation']:
        return 'different'
    if not a['tokens'] or not b['tokens']:
        return 'unknown'
    if a['chinese'] and b['chinese']:
        return 'same' if a['chinese'] == b['chinese'] else 'different'
    if a['chinese'] or b['chinese']:
        cn, latin = (a, b) if a['chinese'] else (b, a)
        if cn['issue']:
            return 'unknown'
        return 'same' if pinyin_match(cn, latin) else 'different'
    if a['tokens'] == b['tokens']:
        return 'same'
    # Hyphens, apostrophes and spaces are formatting, but suffixes remain meaningful.
    def formatting_forms(info):
        tokens = info['ordered_tokens']
        return {''.join(tokens), ''.join(reversed(tokens)), ''.join(sorted(tokens))}
    if formatting_forms(a) & formatting_forms(b):
        return 'same'
    at = [t for t in a['tokens'] if t not in SUFFIXES]
    bt = [t for t in b['tokens'] if t not in SUFFIXES]
    small, large = sorted((at, bt), key=len)
    remaining = list(large)
    matched = 0
    for t in sorted(small, key=lambda s: -len(s)):
        hit = next((v for v in remaining if v == t or
                    (min(len(v), len(t)) == 1 and v[0] == t[0])), None)
        if hit:
            matched += 1
            remaining.remove(hit)
    if matched == len(small) and matched:
        return 'compatible'
    # Shared full part plus a changed part may be a nickname. Never auto-merge.
    if set(at) & set(bt):
        return 'compatible'
    return 'different'


EMAIL = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", re.I)


def emails(value):
    text = re.sub(r'(?i)mailto:', '', nfkc(value).strip()).lower()
    good, bad = [], []
    for item in re.split(r'[;,\s]+', text):
        if not present(item):
            continue
        item = item.strip('<>')
        if EMAIL.fullmatch(item) and '..' not in item:
            good.append(item)
        else:
            bad.append(item)
    return sorted(set(good)), bad


def phone_text(digits, extension):
    return digits + (' x' + extension if extension else '')


def phones(value, plus=None):
    # plus, when given, collects the forms a source wrote with an explicit country code (+ or 00).
    out, bad = [], []
    for part in re.split(r'[;\n/]+', nfkc(value)):
        part = part.strip()
        if not present(part):
            continue
        ext = re.search(r'(?:ext\.?|extension|x|#|分机)\s*(\d+)\s*$', part, re.I)
        extension = ext.group(1) if ext else ''
        base = part[:ext.start()] if ext else part
        base = re.sub(r'^00', '+', base.strip())
        # Explicit +country (0) trunk notation.
        base = re.sub(r'^(\+\d{1,3})\s*\(0\)', r'\1', base)
        digits = ''.join(c for c in base if c.isdigit())
        if re.search(r'[^\d\s+().\-]', base) or not 7 <= len(digits) <= 15:
            bad.append(part)
        else:
            out.append((digits, extension))
            if plus is not None and re.match(r'\(?\s*\+', base):
                plus.add(phone_text(digits, extension))
    return sorted(set(out)), bad


def same_phone(a, b, ignore_extension=False):
    if not ignore_extension and a[1] != b[1]:
        return False
    if a[0] == b[0]:
        return True
    for short, long in ((a[0], b[0]), (b[0], a[0])):
        national = short[1:] if short.startswith('0') else short
        if len(national) >= 7 and long.endswith(national):
            prefix = long[:-len(national)]
            if prefix in CALLING_CODES:
                return True
    return False


ALIASES = {
    'name': ['name', 'full name', 'contact', 'contact name', 'person', 'person name', '姓名', '姓名 Name', '联系人', '名字', '客户姓名'],
    'first': ['first', 'first name', 'given name', 'forename', '名'],
    'last': ['last', 'last name', 'family name', 'surname', '姓'],
    'email': ['email', 'email address', 'e-mail', 'e-mail address', 'email 1', 'email 2', 'work email', 'personal email', '邮箱', '电子邮件', '电邮', '邮箱 Email'],
    'phone': ['phone', 'phone number', 'telephone', 'tel', 'mobile', 'mobile number', 'mobile #', 'cell', 'cell phone', 'work phone', 'home phone', 'phone 1', 'phone 2', '电话', '手机', '联系电话', '手机 Phone', '电话 Phone'],
    'organisation': ['company', 'company name', 'organization', 'organisation', 'organization name', 'organisation name', 'business', '单位', '公司', '机构', '公司 Company', '单位 Company']
}
HEADER_MAP = {key(label): kind for kind, labels in ALIASES.items() for label in labels}


def header_kind(value):
    k = key(value)
    if k in HEADER_MAP:
        return HEADER_MAP[k]
    for kind, labels in ALIASES.items():
        if any(cjk(label) and key(label) in k for label in labels) and len(k) < 28:
            return kind
    # Multirow groups and bilingual labels often combine two known labels.
    for prefix in ('contact', 'personal', 'business', 'work', 'primary', 'secondary'):
        if k.startswith(prefix) and k[len(prefix):] in HEADER_MAP:
            return HEADER_MAP[k[len(prefix):]]
    return None


def decode_csv(data, encoding=None):
    if encoding:
        try:
            return data.decode(encoding), encoding
        except (UnicodeError, LookupError) as exc:
            raise Refused('Cannot decode with --encoding %s: %s' % (encoding, exc))
    for bom, enc in ((b'\xef\xbb\xbf', 'utf-8-sig'), (b'\xff\xfe', 'utf-16'), (b'\xfe\xff', 'utf-16')):
        if data.startswith(bom):
            return data.decode(enc), enc
    if b'\x00' in data:
        raise Refused('UTF-16 without a BOM or binary data: specify --encoding utf-16-le or utf-16-be after checking the file.')
    try:
        return data.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        pass
    # GBK and GB18030 often decode to exactly the same text. They are one reading,
    # not an ambiguity; prefer the narrower compatible codec in that case.
    candidates = []
    for enc in ('gbk', 'gb18030', 'cp1252'):
        try:
            value = data.decode(enc)
            if not any((ord(c) < 32 and c not in '\r\n\t') or 127 <= ord(c) <= 159 for c in value):
                if any(value == text for text, _ in candidates):
                    continue
                candidates.append((value, enc))
        except UnicodeDecodeError:
            pass
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        chinese = next(((value, enc) for value, enc in candidates if enc in ('gbk', 'gb18030')), None)
        western = next(((value, enc) for value, enc in candidates if enc == 'cp1252'), None)
        if chinese and western:
            value = chinese[0]
            count = sum(cjk(c) for c in value)
            mixed_words = sum((cjk(a) and b.isascii() and b.isalpha()) or
                              (cjk(b) and a.isascii() and a.isalpha())
                              for a, b in zip(value, value[1:]))
            # Coherent Chinese runs are evidence. A CJK character embedded in a
            # Latin word (François -> Fran鏾is, for example) is not that evidence.
            runs = re.findall(r'[\u3400-\u9fff\U00020000-\U0003134f]{2,}', value)
            chinese_labels = sum(label in value for label in ('姓名', '邮箱', '手机', '公司', '电话', '联系人'))
            if count >= 2 and mixed_words == 0 and (runs or chinese_labels >= 2):
                return chinese
            accented_words = re.findall(r'[A-Za-z]+[\u00c0-\u024f]+[A-Za-z]*', western[0])
            western_symbols = sum(unicodedata.category(c)[0] in 'PS' and ord(c) > 127 for c in western[0])
            if accented_words and mixed_words and western_symbols == 0:
                return western
        # A common ASCII preamble can be long. Show the part where readings
        # actually diverge, rather than two indistinguishable truncated prefixes.
        common = 0
        shortest = min(len(value) for value, _ in candidates)
        while common < shortest and len({value[common] for value, _ in candidates}) == 1:
            common += 1
        start = max(0, common - 40)
        samples = '; '.join('%s sample: %s' % (enc, json.dumps(
            ('…' if start else '') + value[start:start + 120] + ('…' if len(value) > start + 120 else ''), ensure_ascii=False))
            for value, enc in candidates)
        raise Refused('Encoding is genuinely ambiguous; choose --encoding after checking these possible readings. ' + samples)
    raise Refused('Encoding is unsupported or contains invalid bytes; export UTF-8 or specify the known --encoding. No bytes were replaced.')


def column_index(ref):
    n = 0
    for c in re.match(r'[A-Za-z]+', ref).group().upper():
        n = n * 26 + ord(c) - 64
    return n - 1


def column_name(n):
    out = ''
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def numeric_text(value):
    try:
        number = decimal.Decimal(value)
        if not number.is_finite():
            return value
        return format(number.to_integral_value() if number == number.to_integral_value() else number, 'f')
    except decimal.InvalidOperation:
        return value


def unescape_ooxml(value):
    # A single pass preserves escaped literal markers, e.g. _x005F_x0041_.
    text = re.sub(r'_x([0-9a-fA-F]{4})_', lambda m: chr(int(m.group(1), 16)), value)
    # Excel sometimes encodes a supplementary character as two UTF-16 escapes.
    return text.encode('utf-16-le', 'surrogatepass').decode('utf-16-le')


def read_xlsx(data):
    sheets = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > 256 * 1024 * 1024:
                raise Refused('Workbook expands beyond 256 MiB; split it into smaller exports.')
            def xml(path):
                content = z.read(path)
                if b'<!DOCTYPE' in content or b'<!ENTITY' in content:
                    raise Refused('Workbook XML contains a DTD or entity declaration.')
                return ET.fromstring(content)
            def elems(root, tag):
                return [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] == tag]
            strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                strings = [unescape_ooxml(''.join(t.text or '' for t in elems(si, 't'))) for si in elems(xml('xl/sharedStrings.xml'), 'si')]
            workbook = xml('xl/workbook.xml')
            rels = {e.attrib['Id']: e.attrib['Target'] for e in xml('xl/_rels/workbook.xml.rels')
                    if e.attrib.get('TargetMode') != 'External'}
            style_xml = z.read('xl/styles.xml').decode('utf-8') if 'xl/styles.xml' in z.namelist() else ''
            for sheet in elems(workbook, 'sheet'):
                rid = next(v for k, v in sheet.attrib.items() if k.endswith('}id'))
                target = rels[rid]
                target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
                import posixpath
                root = xml(posixpath.normpath(target))
                matrix, metadata = {}, {}
                for row in elems(root, 'row'):
                    rn = int(row.attrib.get('r', len(matrix) + 1))
                    values, cells = [], []
                    for cell in list(row):
                        if cell.tag.rsplit('}', 1)[-1] != 'c':
                            continue
                        ref = cell.attrib.get('r', column_name(len(values) + 1) + str(rn))
                        ci = column_index(ref)
                        if ci >= 16384 or rn > 1048576:
                            raise Refused('Cell coordinate exceeds XLSX limits.')
                        while len(values) <= ci:
                            values.append('')
                        kind = cell.attrib.get('t', 'n')
                        vs, fs = elems(cell, 'v'), elems(cell, 'f')
                        raw = vs[0].text or '' if vs else ''
                        if fs:
                            value = '=' + (fs[0].text or '')
                        elif kind == 's':
                            value = strings[int(raw)]
                        elif kind == 'inlineStr':
                            value = unescape_ooxml(''.join(t.text or '' for t in elems(cell, 't')))
                        elif kind == 'n':
                            value = numeric_text(raw)
                        else:
                            value = raw
                        values[ci] = value
                        cells.append({'column': ci + 1, 'ref': ref, 'type': kind,
                                      'style': cell.attrib.get('s', '0'), 'stored': raw,
                                      'formula': fs[0].text or '' if fs else None,
                                      'xml': ET.tostring(cell, encoding='unicode')})
                    matrix[rn], metadata[rn] = values, cells
                last = max((r for r, v in matrix.items() if any(str(c).strip() for c in v)), default=0)
                rows = [matrix.get(r, []) for r in range(1, last + 1)]
                sheets.append({'sheet': sheet.attrib['name'], 'values': rows,
                               'cell_metadata': metadata, 'styles_xml': style_xml,
                               'merged_cells': [m.attrib['ref'] for m in elems(root, 'mergeCell')],
                               'date1904': any(p.attrib.get('date1904') in ('1', 'true') for p in elems(workbook, 'workbookPr'))})
    except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, StopIteration) as exc:
        raise Refused('Cannot read XLSX workbook: %s. Export it again as .xlsx or CSV.' % exc)
    return sheets


def read_source(path, encoding=None):
    data = path.read_bytes()
    if path.suffix.lower() == '.xls':
        raise Refused('Old binary .xls is not supported. Save it as .xlsx or UTF-8 CSV, then run again.')
    if path.suffix.lower() == '.xlsx':
        sheets = read_xlsx(data)
    elif path.suffix.lower() in ('.csv', '.tsv'):
        text, enc = decode_csv(data, encoding)
        try:
            dialect = csv.Sniffer().sniff(text[:65536], delimiters=',;\t')
            delimiter = dialect.delimiter
        except csv.Error:
            # Titles above the header confuse Sniffer. Score consistent row widths.
            choices = []
            for sep in (',', ';', '\t'):
                parsed = list(csv.reader(io.StringIO(text, newline=''), delimiter=sep))
                sizes = collections.Counter(len(r) for r in parsed if len(r) > 1)
                choices.append((max(sizes.values(), default=0), sep))
            delimiter = max(choices)[1] if any(x[0] for x in choices) else ','
        values = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True))
        while values and not any(str(v).strip() for v in values[-1]):
            values.pop()
        sheets = [{'values': values, 'encoding': enc, 'delimiter': delimiter, 'cell_metadata': {}}]
    else:
        raise Refused('Use CSV, TSV, or XLSX input; unsupported extension: ' + path.suffix)
    return data, sheets


NON_CONTACT_LABELS = {
    'id', 'identifier', 'recordid', 'contactid', 'routingid', 'trackingtoken',
    'date', 'added', 'created', 'updated', 'timestamp', 'notes', 'note', 'remarks',
    'visitremarks', 'comments', 'status', 'country', 'address', 'postcode', 'zipcode',
    '编号', '备注', '日期', '国家', '地址'
}
ORG_WORDS = {'company', 'co', 'ltd', 'limited', 'inc', 'llc', 'studio', 'studios',
             'services', 'supplies', 'workshop', 'works', 'collective', 'association',
             'foundation', 'office', 'design', 'paperworks', 'group', 'university'}
NAME_PARTICLES = {'de', 'del', 'da', 'dos', 'van', 'von', 'la', 'le', 'al', 'bin'}


def value_shapes(value):
    """Observable cell shapes, independent of its column heading."""
    text = nfkc(value).strip()
    if not present(text) or header_kind(text):
        return set()
    result = set()
    good_emails, bad_emails = emails(text)
    if good_emails and not bad_emails:
        return {'email'}
    if re.fullmatch(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T].*)?|\d{1,2}[-/]\d{1,2}[-/]\d{4}', text):
        return result
    good_phones, bad_phones = phones(text)
    if good_phones and not bad_phones:
        return {'phone'}
    if '@' in text or any(c.isdigit() for c in text) or text.startswith(('=', '<')):
        return result
    if any(word in text for word in ('公司', '工作室', '机构', '協會', '协会', '大学', '大學')):
        return {'organisation'}
    words = re.findall(r'[^\W_]+', text, re.UNICODE)
    if not words or re.search(r'[^\w\s.,\-\'’]', text, re.UNICODE):
        return result
    if set(fold(w) for w in words) & ORG_WORDS:
        return {'organisation'}
    if cjk(text):
        if all(cjk(c) or c.isspace() for c in text) and 1 <= len(key(text)) <= 5:
            return {'name', 'name_part'} if len(key(text)) >= 2 else {'name_part'}
        return result
    if len(words) == 1 and 1 <= len(words[0]) <= 24 and words[0].isalpha():
        result.add('name_part')
    meaningful = [w for w in words if fold(w) not in TITLES]
    capitals = all(w[0].isupper() or fold(w) in NAME_PARTICLES or len(w) == 1 for w in meaningful)
    lowercase_name = len(meaningful) == 2 and all(w.islower() for w in meaningful)
    if 2 <= len(meaningful) <= 5 and (capitals or lowercase_name):
        result.add('name')
    return result


def infer_column_roles(values, header_values, labels):
    width = max([len(r) for r in values + header_values] or [0])
    mapping, evidence = [], []
    for column in range(width):
        headings = [row[column] for row in header_values if column < len(row) and present(row[column])]
        header_role = next((header_kind(v) for v in reversed(headings) if header_kind(v)), None)
        final_label = labels[column] if column < len(labels) else ''
        blocked = key(final_label) in NON_CONTACT_LABELS
        sample = [row[column] for row in values if column < len(row) and present(row[column])
                  and not header_kind(row[column]) and key(row[column]) != key(final_label)][:200]
        shapes = [value_shapes(value) for value in sample]
        names = [name_info(value) for value in sample]
        native_names = [info for info, shape in zip(names, shapes) if info['chinese'] and 'name' in shape]
        pinyin_values = 0
        for info, shape in zip(names, shapes):
            if not info['chinese'] and any(pinyin_match(native, info) for native in native_names):
                shape.add('name')
                pinyin_values += 1
        tallies = collections.Counter(shape for shape_set in shapes for shape in shape_set)
        threshold = max(1, int(len(sample) * 0.75 + 0.999))
        role, reason = header_role, 'recognized header' if header_role else 'no supported role'
        # Data can supply missing roles and correct a contradictory label. Known
        # ID/date/note columns remain auxiliary rather than becoming phone/name data.
        if sample and not blocked:
            for shape in ('email', 'phone', 'organisation'):
                if shape == 'organisation' and header_role in ('name', 'first', 'last'):
                    continue
                if tallies[shape] >= threshold:
                    role, reason = shape, 'inferred from %d of %d nonempty values' % (tallies[shape], len(sample))
                    break
        mapping.append(role)
        evidence.append({'column': column + 1, 'headers': headings, 'header_role': header_role,
                         'nonempty_sample_count': len(sample), 'value_shapes': dict(tallies),
                         'role': role, 'reason': reason, 'auxiliary_header': blocked,
                         'pinyin_name_values': pinyin_values})
    # One recognizable component heading is enough to look for its adjacent
    # counterpart, but not to pretend the component is already a complete name.
    for role, counterpart in (('first', 'last'), ('last', 'first')):
        if role in mapping and counterpart not in mapping:
            options = [i for i, item in enumerate(evidence) if mapping[i] is None and not item['auxiliary_header']
                       and any(0 <= j < len(mapping) and mapping[j] == role for j in (i - 1, i + 1))
                       and item['nonempty_sample_count'] and item['value_shapes'].get('name_part', 0) >=
                       max(1, int(item['nonempty_sample_count'] * 0.75 + 0.999))]
            if len(options) == 1:
                i = options[0]
                mapping[i] = counterpart
                evidence[i].update(role=counterpart, reason='name-part values adjacent to the recognized ' + role + '-name column')
    if not any(role in ('name', 'first', 'last') for role in mapping):
        candidates = [i for i, item in enumerate(evidence) if mapping[i] is None and not item['auxiliary_header']
                      and item['nonempty_sample_count'] and item['value_shapes'].get('name', 0) >=
                      max(1, int(item['nonempty_sample_count'] * 0.75 + 0.999))]
        if len(candidates) == 1:
            i = candidates[0]
            mapping[i] = 'name'
            evidence[i].update(role='name', reason='inferred from person-name-shaped values')
        elif not candidates:
            parts = [i for i, item in enumerate(evidence) if mapping[i] is None and not item['auxiliary_header']
                     and item['nonempty_sample_count'] and item['value_shapes'].get('name_part', 0) >=
                     max(1, int(item['nonempty_sample_count'] * 0.75 + 0.999))]
            if len(parts) == 2 and parts[1] == parts[0] + 1:
                for i, role in zip(parts, ('first', 'last')):
                    mapping[i] = role
                    evidence[i].update(role=role, reason='two adjacent columns contain complementary name parts')
        else:
            for i in candidates:
                evidence[i]['reason'] = 'multiple possible name columns; no arbitrary choice'
    # A Name group label over two otherwise unnamed component columns must not
    # make the first component a complete name. Values can reveal the split too.
    part_columns = [i for i, item in enumerate(evidence) if mapping[i] in (None, 'name')
                    and not item['auxiliary_header'] and item['nonempty_sample_count']
                    and item['value_shapes'].get('name_part', 0) >= max(1, int(item['nonempty_sample_count'] * 0.75 + 0.999))
                    and item['value_shapes'].get('name', 0) == 0]
    if len(part_columns) == 2 and part_columns[1] == part_columns[0] + 1 and not any(r in ('first', 'last') for r in mapping):
        for i, role in zip(part_columns, ('first', 'last')):
            mapping[i] = role
            evidence[i].update(role=role, reason='two adjacent columns contain complementary name parts')
    return mapping, evidence


def find_header(sheet, override=None):
    values = sheet['values']
    if not values:
        sheet['column_role_evidence'] = []
        return 0, [], []
    if override:
        if not 1 <= override <= len(values):
            raise Refused('--header-row falls outside this sheet.')
        end = override
    else:
        # Find the transition to identifier-bearing values, not merely the first
        # familiar label. Group labels can themselves be Name/Email/Phone.
        first_data = next((i for i, row in enumerate(values[:200]) if any(
            not header_kind(cell) and ('email' in value_shapes(cell) or 'phone' in value_shapes(cell)
                                      or ('@' in str(cell) and not str(cell).startswith('='))) for cell in row)), None)
        if first_data is None:
            first_data = next((i for i, row in enumerate(values[1:200], 1)
                               if any(value_shapes(v) & {'name', 'organisation'} for v in row)
                               or sum('name_part' in value_shapes(v) for v in row) >= 2), None)
        limit = min(first_data if first_data is not None else len(values), 50)
        identity_columns = {i for i, v in enumerate(values[first_data])
                            if value_shapes(v) & {'email', 'phone'} or '@' in str(v)} if first_data is not None else set()
        schema_rows = []
        for i, row in enumerate(values[:limit]):
            nonempty = [v for v in row if present(v)]
            if not nonempty:
                continue
            known = sum(header_kind(v) is not None for v in nonempty)
            # The true field row names the identifier columns even when none of
            # its labels are in our alias list. Sparse name-only data does not.
            text_at_identifiers = any(j < len(row) and present(row[j]) and
                                      not any(c.isdigit() for c in str(row[j])) for j in identity_columns)
            all_labels = not any(value_shapes(v) & {'email', 'phone'} or '@' in str(v)
                                 or (any(c.isdigit() for c in str(v)) and not header_kind(v)) for v in nonempty)
            if all_labels and (known or (len(nonempty) >= 2 and text_at_identifiers)):
                schema_rows.append(i)
        if schema_rows:
            end = schema_rows[-1] + 1
        else:
            # A headed export with entirely unusual labels can still be processed.
            # Do not eat blank/contact rows above the first identifiable contact.
            end = next((i + 1 for i, row in enumerate(values[:50]) if any(present(v) for v in row)), 1)
    labels = [str(c) for c in values[end - 1]]
    mapping, evidence = infer_column_roles(values[end:], values[:end], labels)
    sheet['column_role_evidence'] = evidence
    return end, mapping, labels


def normalize_row(values, mapping):
    fields = collections.defaultdict(list)
    for i, value in enumerate(values):
        if i < len(mapping) and mapping[i] and present(value):
            fields[mapping[i]].append(nfkc(value).strip())
    components = fields['first'] + fields['last']
    if fields['first'] and fields['last'] and all(cjk(v) and all(cjk(c) or c.isspace() for c in v) for v in components):
        components = fields['last'] + fields['first']
    name = ' '.join(fields['name']) or ' '.join(components)
    org = ' | '.join(fields['organisation'])
    e, bad_e = emails(';'.join(fields['email']))
    plus = set()
    p, bad_p = phones(';'.join(fields['phone']), plus)
    # Bad values remain visible in the clean contact; only valid tokens match.
    clean = {'name': re.sub(r'\s+', ' ', name), 'organisation': re.sub(r'\s+', ' ', org),
             'emails': e, 'phones': [phone_text(d, ext) for d, ext in p],
             'unverified_emails': bad_e, 'unverified_phones': bad_p}
    info = name_info(name or org, organisation=not bool(name) and bool(org))
    issues = []
    if bad_e:
        issues.append('Invalid email syntax retained; not used to match: ' + ', '.join(bad_e))
    if bad_p:
        issues.append('Unrecognized phone retained; not used to match: ' + ', '.join(bad_p))
    if info['issue']:
        issues.append(info['issue'])
    return clean, info, e, p, issues, bool(name or org or fields['email'] or fields['phone']), plus


def locator(row):
    return row['file'] + ((' / ' + row['sheet']) if 'sheet' in row else '') + ' row ' + str(row['row'])


def shared(a, b):
    evidence = []
    if set(a['_emails']) & set(b['_emails']):
        evidence.append('email ' + ', '.join(sorted(set(a['_emails']) & set(b['_emails']))))
    if any(same_phone(x, y) for x in a['_phones'] for y in b['_phones']):
        evidence.append('phone (digits equal, or a country code with the national trunk 0 removed)')
    return evidence


def build_audit(paths, encoding=None, header_row=None):
    if len({p.name for p in paths}) != len(paths):
        raise Refused('Input basenames must be distinct so file/row references stay unambiguous. Use separate runs or distinctly named copies.')
    sources, rows, originals, warnings = [], [], [], []
    for path in paths:
        data, sheets = read_source(path, encoding)
        digest = hashlib.sha256(data).hexdigest()
        originals.append({'file': path.name, 'sha256': digest, 'base64': base64.b64encode(data).decode('ascii')})
        for sheet in sheets:
            end, mapping, labels = find_header(sheet, header_row)
            source = {'file': path.name, 'sha256': digest, 'header_rows': list(range(1, end + 1)),
                      'headers': labels, 'column_roles': mapping,
                      'column_role_evidence': sheet['column_role_evidence'],
                      'original_header_values': sheet['values'][:end]}
            if sheet['values'] and not any(role in ('name', 'first', 'last') for role in mapping):
                source_name = path.name + (' / ' + sheet['sheet'] if 'sheet' in sheet else '')
                warnings.append({'file': path.name, **({'sheet': sheet['sheet']} if 'sheet' in sheet else {}),
                                 'code': 'missing_name_column',
                                 'message': 'No name column found in ' + source_name + '; person matching is unavailable. Review the column roles before relying on merges.'})
            for k in ('sheet', 'encoding', 'delimiter', 'merged_cells', 'styles_xml', 'date1904'):
                if k in sheet:
                    source[k] = sheet[k]
            sources.append(source)
            for i, values in enumerate(sheet['values'][end:], end + 1):
                row = {'file': path.name, 'row': i, 'original': values,
                       'cell_metadata': sheet['cell_metadata'].get(i, [])}
                if 'sheet' in sheet:
                    row['sheet'] = sheet['sheet']
                clean, info, e, p, issues, is_contact, plus = normalize_row(values, mapping)
                row.update(cleaned=clean, changes=[], issues=issues)
                recognized = [(j, header_kind(v)) for j, v in enumerate(values) if str(v).strip()]
                repeats = sum(kind is not None and j < len(mapping) and kind == mapping[j] for j, kind in recognized)
                exact_header = sum(bool(str(v).strip()) for v in values) >= 2 and \
                    [key(v) for v in values] == [key(v) for v in labels]
                header_like = exact_header or (repeats >= 2 and all(not str(v).strip() or header_kind(v) or key(v) in {key(x) for x in labels} for v in values))
                if header_like:
                    row.update(disposition='not_contact', reason='repeats the header row')
                    row['issues'] = []
                elif not is_contact:
                    row.update(disposition='empty', reason='no person name, organisation, email or phone after placeholder handling')
                else:
                    row.update(disposition='kept', _name=info, _emails=e, _phones=p, _plus_phones=plus)
                if is_contact and not header_like:
                    row['changes'].append({'reason': 'Contact columns mapped; placeholders omitted; Unicode width and spacing normalized; email case/mailto and phone formatting normalized. Originals and invalid tokens retained.',
                                           'before': values, 'after': clean})
                rows.append(row)
    contacts = [r for r in rows if r['disposition'] == 'kept']
    if len(contacts) > 6000:
        raise Refused('This version supports at most 6,000 contact rows per run (pairwise review). Split the export into smaller runs.')
    edges = collections.defaultdict(set)
    candidates = {}
    for i, a in enumerate(contacts):
        for j in range(i + 1, len(contacts)):
            b = contacts[j]
            relation = name_relation(a['_name'], b['_name'])
            evidence = shared(a, b)
            if relation == 'same' and evidence:
                edges[i].add(j)
                edges[j].add(i)
            reason = None
            if relation == 'same' and not evidence:
                reason = same_name_reason(a['_name'], b['_name']) + '; no shared email or phone (R4)'
            elif evidence and relation in ('compatible', 'unknown'):
                reason = 'shared ' + ' and '.join(evidence) + '; names ' + (
                    'compatible but not the same (R2)' if relation == 'compatible' else
                    'cannot be resolved: ' + '; '.join(filter(None, [a['_name']['issue'], b['_name']['issue']])) + ' (unsettled name case)')
            elif relation in ('same', 'compatible') and any(same_phone(x, y, True) for x in a['_phones'] for y in b['_phones']):
                reason = 'same base phone with different or missing extensions; do not assume the same destination'
            if reason:
                candidates[i, j] = reason
    def relation(i, j):
        return 'same' if i == j else name_relation(contacts[i]['_name'], contacts[j]['_name'])
    # R5: an ambiguous bridge joins neither side. Compute before any union, independent of row order.
    blocked = {i for i, neighbours in edges.items()
               if any(relation(j, k) != 'same' for j, k in itertools.combinations(neighbours, 2))}
    for i in blocked:
        for j in edges[i]:
            explanation = same_name_reason(contacts[i]['_name'], contacts[j]['_name'])
            candidates[min(i, j), max(i, j)] = explanation + '; shared ' + ' and '.join(shared(contacts[i], contacts[j])) + '; fits two contacts whose names are not the same; joins neither (R5)'
    groups, visited = [], set()
    for i in range(len(contacts)):
        if i in visited:
            continue
        component, todo = [], [i]
        while todo:
            j = todo.pop()
            if j in visited:
                continue
            visited.add(j)
            component.append(j)
            if j not in blocked:
                todo.extend(k for k in edges[j] if k not in blocked and k not in visited)
        if any(relation(j, k) != 'same' for j, k in itertools.combinations(component, 2)):
            # A nontransitive component cannot be merged safely, even if a longer bridge hid the conflict.
            groups.extend([[j] for j in sorted(component)])
            for j, k in itertools.combinations(sorted(component), 2):
                if k in edges[j]:
                    candidates[j, k] = 'conflicting names in a connected match chain; left separate (R5)'
        else:
            groups.append(sorted(component))
    groups.sort(key=lambda group: min(group))
    records = []
    for n, group in enumerate(groups, 1):
        rid = 'C%04d' % n
        first = group[0]
        # BFS yields a real shared-identifier witness for every merged row, including chains.
        witnesses, queue = {}, collections.deque([first])
        seen = {first}
        members = set(group)
        while queue:
            j = queue.popleft()
            for k in sorted(edges[j] & members):
                if k not in seen:
                    seen.add(k)
                    witnesses[k] = j
                    queue.append(k)
        for j in group:
            row = contacts[j]
            row['record'] = rid
            if j != first:
                witness = contacts[witnesses[j]]
                row.update(disposition='merged', reason='shared ' + ' and '.join(shared(row, witness)) +
                           ' with ' + locator(witness) + '; ' + same_name_reason(row['_name'], witness['_name']) + ' (R1)',
                           matched_to={'file': witness['file'], 'row': witness['row'], **({'sheet': witness['sheet']} if 'sheet' in witness else {})})
        values = {}
        for field in ('name', 'organisation', 'emails', 'phones', 'unverified_emails', 'unverified_phones'):
            all_values = []
            for j in group:
                value = contacts[j]['cleaned'][field]
                all_values.extend(value if isinstance(value, list) else ([value] if value else []))
            values[field] = list(dict.fromkeys(all_values))
        observed = json.loads(json.dumps(values))
        canonical_phones = []
        for phone in sorted(values['phones'], key=lambda v: -len(v)):
            parsed = phones(phone)[0]
            if parsed and not any(same_phone(parsed[0], phones(existing)[0][0]) for existing in canonical_phones):
                canonical_phones.append(phone)
        # A chosen form that a source wrote with + or 00 keeps its plus; a country code is never guessed.
        written_with_plus = set().union(*(contacts[j]['_plus_phones'] for j in group))
        values['phones'] = [('+' + phone if phone in written_with_plus else phone) for phone in canonical_phones]
        records.append({'record': rid, 'values': values, 'observed_values': observed,
                        'primary_name': next(iter(values['name']), ''),
                        'primary_organisation': next(iter(values['organisation']), ''),
                        'source_rows': [{'file': contacts[j]['file'], 'row': contacts[j]['row'],
                                         **({'sheet': contacts[j]['sheet']} if 'sheet' in contacts[j] else {})} for j in group],
                        'assembly': 'Display name and organisation use the first nonempty source value. Name variants and all distinct email values retained. Equivalent phone formats use the longest digit form, written with a leading + when a source wrote that form with a country code (+ or 00); a country code is never added. Every observed value is retained in observed_values.',
                        'assembly_changes': {'before': observed, 'after': values}})
    uncertain_map = {}
    for (i, j), reason in sorted(candidates.items()):
        pair = tuple(sorted((contacts[i]['record'], contacts[j]['record'])))
        if pair[0] == pair[1]:
            continue
        entry = uncertain_map.setdefault(pair, {'records': list(pair), 'reason': reason, 'evidence': []})
        entry['evidence'].append({'rows': [locator(contacts[i]), locator(contacts[j])], 'reason': reason})
    uncertain = list(uncertain_map.values())
    review = [{'file': r['file'], 'row': r['row'], **({'sheet': r['sheet']} if 'sheet' in r else {}),
               'record': r.get('record'), 'reason': issue} for r in rows for issue in r['issues']]
    for row in rows:
        for private in ('_name', '_emails', '_phones', '_plus_phones'):
            row.pop(private, None)
    tally = collections.Counter(r['disposition'] for r in rows)
    audit = {'schema_version': 1, 'counts': {'in': len(rows), 'clean': tally['kept'], 'merged': tally['merged'],
             'empty': tally['empty'], 'not_contact': tally['not_contact'], 'uncertain_pairs': len(uncertain)},
             'sources': sources, 'rows': rows, 'uncertain': uncertain, 'records': records,
             'values_needing_review': review, 'original_files': originals, 'warnings': warnings,
             'normalization_policy': 'Original values and source bytes retained. Formulas are inert text, never evaluated. See references/matching.md.'}
    validate_audit(audit)
    return audit


def validate_audit(audit):
    rows, counts = audit['rows'], audit['counts']
    identities = [(r['file'], r.get('sheet'), r['row']) for r in rows]
    if len(set(identities)) != len(rows):
        raise Refused('Internal check: a source row appears twice.')
    for key_, disposition in [('clean', 'kept'), ('merged', 'merged'), ('empty', 'empty'), ('not_contact', 'not_contact')]:
        if counts[key_] != sum(r['disposition'] == disposition for r in rows):
            raise Refused('Internal check: disposition count mismatch: ' + key_)
    if counts['in'] != len(rows) or counts['in'] != sum(counts[k] for k in ('clean', 'merged', 'empty', 'not_contact')):
        raise Refused('Internal check: conservation failed.')
    if counts['uncertain_pairs'] != len(audit['uncertain']):
        raise Refused('Internal check: uncertain pair count mismatch.')
    for record in audit['records']:
        members = [r for r in rows if r.get('record') == record['record']]
        if sum(r['disposition'] == 'kept' for r in members) != 1:
            raise Refused('Internal check: contact does not have exactly one kept row.')
        if any(r['disposition'] == 'merged' and not r.get('reason') for r in members):
            raise Refused('Internal check: merge without a reason.')


def equation(counts):
    line = '{in} in = {clean} clean + {merged} merged + {empty} empty'.format(**counts)
    if counts['not_contact']:
        line += ' + %d not a contact' % counts['not_contact']
    return line


def pair_label(count):
    return '%d %s to check' % (count, 'pair' if count == 1 else 'pairs')


def xml_text(value):
    # Escape OOXML's literal escape marker before encoding XML-forbidden controls.
    value = re.sub(r'_x([0-9A-Fa-f]{4})_', r'_x005F_x\1_', str(value))
    return ''.join('_x%04X_' % ord(c) if (ord(c) < 32 and c not in '\t\r\n') else c for c in value)


def xlsx_bytes(sheets):
    ET.register_namespace('', NS)
    def tag(name):
        return '{%s}%s' % (NS, name)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        content = ET.Element('Types', xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
        ET.SubElement(content, 'Default', Extension='rels', ContentType='application/vnd.openxmlformats-package.relationships+xml')
        ET.SubElement(content, 'Default', Extension='xml', ContentType='application/xml')
        ET.SubElement(content, 'Override', PartName='/xl/workbook.xml', ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
        ET.SubElement(content, 'Override', PartName='/xl/styles.xml', ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml')
        root_rels = ET.Element('Relationships', xmlns=PACKAGE_REL)
        ET.SubElement(root_rels, 'Relationship', Id='rId1', Type=REL + '/officeDocument', Target='xl/workbook.xml')
        z.writestr('_rels/.rels', ET.tostring(root_rels))
        workbook = ET.Element(tag('workbook'))
        nodes = ET.SubElement(workbook, tag('sheets'))
        rels = ET.Element('Relationships', xmlns=PACKAGE_REL)
        ET.SubElement(rels, 'Relationship', Id='styles', Type=REL + '/styles', Target='styles.xml')
        z.writestr('xl/styles.xml', '<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="' + NS + '"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="49" fontId="1" fillId="0" borderId="0" xfId="0"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i, (name, rows) in enumerate(sheets, 1):
            ET.SubElement(nodes, tag('sheet'), name=name, sheetId=str(i), attrib={'{%s}id' % REL: 'rId%d' % i})
            ET.SubElement(rels, 'Relationship', Id='rId%d' % i, Type=REL + '/worksheet', Target='worksheets/sheet%d.xml' % i)
            ET.SubElement(content, 'Override', PartName='/xl/worksheets/sheet%d.xml' % i, ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
            worksheet = ET.Element(tag('worksheet'))
            views = ET.SubElement(worksheet, tag('sheetViews'))
            view = ET.SubElement(views, tag('sheetView'), workbookViewId='0')
            ET.SubElement(view, tag('pane'), ySplit='1', topLeftCell='A2', activePane='bottomLeft', state='frozen')
            cols = ET.SubElement(worksheet, tag('cols'))
            for col in range(max((len(r) for r in rows), default=1)):
                ET.SubElement(cols, tag('col'), min=str(col + 1), max=str(col + 1), width='28', customWidth='1')
            data = ET.SubElement(worksheet, tag('sheetData'))
            if len(rows) > 1048576:
                raise Refused('Output sheet exceeds the XLSX row limit.')
            for rn, row in enumerate(rows, 1):
                node = ET.SubElement(data, tag('row'), r=str(rn))
                for ci, value in enumerate(row, 1):
                    value = str(value)
                    if len(value.encode('utf-16-le')) // 2 > 32767:
                        raise Refused('A value exceeds Excel\'s 32,767-character cell limit; shorten it in a copy before running.')
                    cell = ET.SubElement(node, tag('c'), r=column_name(ci) + str(rn), t='inlineStr', s='1' if rn == 1 else '0')
                    string = ET.SubElement(cell, tag('is'))
                    ET.SubElement(string, tag('t'), attrib={'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}).text = xml_text(value)
            if rows:
                ET.SubElement(worksheet, tag('autoFilter'), ref='A1:' + column_name(max(len(r) for r in rows)) + str(len(rows)))
            z.writestr('xl/worksheets/sheet%d.xml' % i, ET.tostring(worksheet, encoding='utf-8', xml_declaration=True).replace(b'\r', b'&#13;'))
        z.writestr('xl/workbook.xml', ET.tostring(workbook, encoding='utf-8', xml_declaration=True))
        z.writestr('xl/_rels/workbook.xml.rels', ET.tostring(rels))
        z.writestr('[Content_Types].xml', ET.tostring(content))
    return stream.getvalue()


def workbook_bytes(audit):
    summary = [['Measure', 'Count / explanation']]
    summary.extend([['WARNING', item['message']] for item in audit.get('warnings', [])])
    summary.append(['Reconciliation', equation(audit['counts'])])
    summary.extend([[k, v] for k, v in audit['counts'].items()])
    summary.append(['Source restoration', 'audit.json contains the exact original source bytes in original_files; --restore writes verified copies.'])
    fields = ['name', 'organisation', 'emails', 'phones', 'unverified_emails', 'unverified_phones']
    clean = [['Record', 'Primary name', 'Primary organisation'] + fields + ['Source rows', 'Assembly', 'Assembly changes (JSON)']]
    for r in audit['records']:
        clean.append([r['record'], r['primary_name'], r['primary_organisation']] + ['; '.join(r['values'][k]) for k in fields] +
                     ['; '.join(locator(s) for s in r['source_rows']), r['assembly'], json.dumps(r['assembly_changes'], ensure_ascii=False)])
    merges = [['Record', 'Source', 'Reason', 'Matched source', 'Original values (JSON)']]
    width = max((len(r['original']) for r in audit['rows']), default=0)
    ledger = [['File', 'Sheet', 'Row', 'Disposition', 'Record', 'Reason', 'Original cell count'] +
              ['Original ' + column_name(i + 1) for i in range(width)]]
    changes = [['Source', 'Reason', 'Before (JSON)', 'After (JSON)']]
    cells = [['Source', 'Column', 'Type', 'Style', 'Stored value', 'Formula (text)', 'Original XML (text)']]
    for row in audit['rows']:
        if row['disposition'] == 'merged':
            merges.append([row['record'], locator(row), row['reason'], locator(row['matched_to']), json.dumps(row['original'], ensure_ascii=False)])
        # One workbook row per counted source row; original cells stay in their column order.
        ledger.append([row['file'], row.get('sheet', ''), row['row'], row['disposition'], row.get('record', ''),
                       row.get('reason', ''), len(row['original'])] + row['original'])
        for change in row['changes']:
            changes.append([locator(row), change['reason'], json.dumps(change['before'], ensure_ascii=False), json.dumps(change['after'], ensure_ascii=False)])
        for cell in row['cell_metadata']:
            cells.append([locator(row), cell['column'], cell['type'], cell['style'], cell['stored'], cell['formula'] or '', cell['xml']])
    uncertain = [['Contact A', 'Contact B', 'Reason', 'Source evidence (JSON)']]
    uncertain.extend([u['records'] + [u['reason'], json.dumps(u['evidence'], ensure_ascii=False)] for u in audit['uncertain']])
    review = [['Source', 'Record', 'Reason']] + [[locator(r), r.get('record', ''), r['reason']] for r in audit['values_needing_review']]
    headers = [['File', 'Sheet', 'Header row', 'Original column', 'Original value', 'SHA-256']]
    roles = [['File', 'Sheet', 'Column', 'Header labels', 'Role', 'Evidence', 'Value shapes (JSON)']]
    for s in audit['sources']:
        for item in s.get('column_role_evidence', []):
            roles.append([s['file'], s.get('sheet', ''), item['column'], ' | '.join(item['headers']),
                          item['role'] or 'unassigned', item['reason'], json.dumps(item['value_shapes'], ensure_ascii=False)])
        for rn, vals in enumerate(s['original_header_values'], 1):
            for ci, v in enumerate(vals or [''], 1):
                headers.append([s['file'], s.get('sheet', ''), rn, ci, v, s['sha256']])
    return xlsx_bytes([('Summary', summary), ('Clean contacts', clean), ('Merges', merges),
                       ('Uncertain pairs', uncertain), ('Original rows', ledger), ('Changes', changes),
                       ('Values to review', review), ('Original headers', headers), ('Cell metadata', cells), ('Column roles', roles)])


def page_html(audit):
    esc = lambda v: html.escape(str(v), quote=True)
    by_record = {r['record']: r for r in audit['records']}
    rows = collections.defaultdict(list)
    for row in audit['rows']:
        if row.get('record'):
            rows[row['record']].append(row)
    def source_evidence(row):
        source = next(s for s in audit['sources'] if s['file'] == row['file'] and s.get('sheet') == row.get('sheet'))
        labels = source['headers']
        vals = row['original']
        fields = ''.join('<div class="source-field"><dt>' +
                         esc(labels[i] if i < len(labels) and labels[i] else column_name(i + 1)) +
                         '</dt><dd>' + esc(v) + '</dd></div>' for i, v in enumerate(vals))
        return '<div class="source" data-source="' + esc(locator(row)) + '"><h4>' + esc(locator(row)) + '<span>' + esc(row['disposition']) + '</span></h4><dl class="source-values">' + fields + '</dl></div>'
    def contact_card(rid):
        r = by_record[rid]
        vals = r['values']
        title = r['primary_name'] or r['primary_organisation'] or 'Contact without a name'
        return '<div class="contact"><small>' + esc(rid) + ' · CLEAN CONTACT</small><h3>' + esc(title) + '</h3><p>' + esc(' · '.join(vals['emails'] + vals['phones'])) + '</p></div>'
    def detail(rid, opened=False):
        r = by_record[rid]
        title = r['primary_name'] or r['primary_organisation'] or rid
        why = ' '.join(row['reason'] for row in rows[rid] if row['disposition'] == 'merged')
        return '<details' + (' open' if opened else '') + '><summary>' + esc(title) + '<span>' + str(len(rows[rid])) + ' source rows</span></summary>' + contact_card(rid) + '<p class="reason">' + esc(why) + '</p>' + ''.join(source_evidence(row) for row in rows[rid]) + '</details>'
    merged_ids = [r['record'] for r in audit['records'] if len(rows[r['record']]) > 1]
    warning_text = ''.join('<p role="status"><strong>WARNING: ' + esc(item['message']) + '</strong></p>'
                           for item in audit.get('warnings', []))
    body = '<header><div><div class="eyebrow">CLEAN LIST · LOCAL AUDIT</div>' + warning_text + '<h1>' + esc(equation(audit['counts'])) + '</h1></div><div class="badge">' + pair_label(audit['counts']['uncertain_pairs']) + '</div></header>'
    body += '<main><h2>See what changed</h2><p class="intro">Every original row is accounted for. Open a merge to trace it back.</p>'
    if merged_ids:
        body += detail(merged_ids[0], True)
        body += ''.join(detail(rid) for rid in merged_ids[1:])
    else:
        body += '<p>No rows were merged in this run.</p>'
    body += '<section><h2>Pairs to check · ' + str(len(audit['uncertain'])) + '</h2><p>These contacts remain separate.</p>'
    for u in audit['uncertain']:
        body += '<details><summary>' + esc(' + '.join(u['records'])) + '</summary><p class="reason">' + esc(u['reason']) + '</p>'
        for rid in u['records']:
            body += contact_card(rid) + ''.join(source_evidence(row) for row in rows[rid])
        body += '</details>'
    body += '</section><section><h2>Values needing review · ' + str(len(audit['values_needing_review'])) + '</h2>'
    for r in audit['values_needing_review']:
        body += '<p>' + esc(locator(r) + ': ' + r['reason']) + '</p>'
    body += '</section><section><h2>All original rows · ' + str(len(audit['rows'])) + '</h2>'
    for row in audit['rows']:
        body += '<details><summary>' + esc(locator(row)) + '<span>' + esc(row['disposition']) + '</span></summary>' + source_evidence(row) + '<p>' + esc(row.get('reason', 'Kept as the contact’s representative row.')) + '</p>'
        if row['changes']:
            body += '<pre>' + esc(json.dumps(row['changes'], ensure_ascii=False, indent=2)) + '</pre>'
        body += '</details>'
    body += '</section></main><footer>Generated from audit.json. Cleaned values, original rows and reversible source bytes stay in this output folder. No external resources.</footer>'
    css = '*{box-sizing:border-box}body{margin:0;background:#f5f4ef;color:#203a34;font:15px/1.45 system-ui,sans-serif;overflow-wrap:anywhere}header,main,footer{max-width:1180px;margin:auto;padding:24px 32px}header{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid #d2d8cf}header>div{min-width:0}.eyebrow{font-size:11px;letter-spacing:.16em;color:#597166;font-weight:700}h1{font-size:clamp(20px,2.6vw,32px);letter-spacing:-.035em;margin:8px 0}h2{font-size:20px;margin:0 0 3px}h3{font-size:20px;margin:3px 0}p{margin:6px 0}.badge{background:#e8dba8;color:#4d441d;padding:9px 15px;border-radius:24px;white-space:nowrap;font-weight:600}.intro{color:#63776c;margin-bottom:16px}details{border:1px solid #cbd6ca;border-radius:10px;background:white;margin:10px 0}summary{cursor:pointer;padding:13px 18px;font-weight:600;background:#eef2ea;border-radius:9px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px 12px}details[open]>summary{border-radius:9px 9px 0 0}summary span,h4 span{color:#66756c;font-size:12px;font-weight:400}summary:focus-visible{outline:3px solid #315e48;outline-offset:-3px}.contact{padding:13px 18px 8px}small{font-size:10px;letter-spacing:.1em;color:#66756c}.reason{padding:8px 18px;background:#f6f7f2;color:#4f6257;font-size:13px}.source{padding:4px 18px 10px;min-width:0}h4{margin:7px 0;font-size:12px;font-weight:600;display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px 12px}.source-values{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:6px 14px;margin:0;font-size:12px}.source-field{min-width:0;padding:5px 0;border-bottom:1px solid #edf0e9}.source-field dt{font-size:10px;color:#68796e;font-weight:500;white-space:pre-wrap}.source-field dd{margin:3px 0 0;min-height:1.45em;white-space:pre-wrap;overflow-wrap:anywhere}section{margin-top:34px}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:18px;font-size:12px}footer{color:#66756c;font-size:12px}details>p:not(.reason){padding:0 18px}@media(max-width:700px){header{display:block}header,main,footer{padding:18px 16px}.badge{display:inline-block}h1{font-size:22px}.source-values{grid-template-columns:minmax(0,1fr)}}'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; form-action \'none\'"><title>Clean List — run audit</title><style>' + css + '</style></head><body>' + body + '</body></html>'


def write_run(paths, output, encoding=None, header_row=None):
    output = Path(output)
    if output.exists():
        raise Refused('Output folder already exists. Choose a new folder; previous runs are never overwritten.')
    audit = build_audit(paths, encoding, header_row)
    # Construct all three artifacts before creating the destination.
    workbook = workbook_bytes(audit)
    page = page_html(audit)
    payload = json.dumps(audit, ensure_ascii=False, indent=2) + '\n'
    for path, original in zip(paths, audit['original_files']):
        if hashlib.sha256(path.read_bytes()).hexdigest() != original['sha256']:
            raise Refused('Source changed while being read: ' + path.name + '. Run again when it is no longer being edited.')
    output.mkdir(parents=True)
    (output / 'audit.json').write_text(payload, encoding='utf-8')
    (output / 'clean.xlsx').write_bytes(workbook)
    (output / 'report.html').write_text(page, encoding='utf-8')
    return audit


def restore(audit_path, output):
    audit = json.loads(Path(audit_path).read_text(encoding='utf-8'))
    dest = Path(output)
    if dest.exists():
        raise Refused('Restore folder already exists; choose a new folder.')
    originals = []
    for source in audit['original_files']:
        name = source['file']
        if name != Path(name).name or '/' in name or '\\' in name or name in ('.', '..'):
            raise Refused('Unsafe source filename in audit.')
        data = base64.b64decode(source['base64'], validate=True)
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            raise Refused('Stored source hash mismatch: ' + name)
        originals.append((name, data))
    if len({name for name, _ in originals}) != len(originals):
        raise Refused('Duplicate restored filenames in audit.')
    dest.mkdir(parents=True)
    for name, data in originals:
        (dest / name).write_bytes(data)
    return len(originals)


def selftest():
    """Named behavioral checks; failures are reported instead of an unhandled crash."""
    # Explicit directory avoids OS temporary locations and works in restricted skill sandboxes.
    with tempfile.TemporaryDirectory(prefix='.clean-list-selftest-', dir=Path.cwd()) as temp:
        folder = Path(temp)
        checks = []
        def check(name, fn):
            try:
                fn()
                checks.append((name, True, ''))
            except Exception as exc:
                checks.append((name, False, str(exc) or type(exc).__name__))
        def require(condition, message='unexpected result'):
            if not condition:
                raise AssertionError(message)
        def sample(name, values, **kwargs):
            path = folder / (name + '.csv')
            with path.open('w', encoding='utf-8', newline='') as f:
                csv.writer(f).writerows(values)
            return build_audit([path], **kwargs)
        header = ['Name', 'Email', 'Phone', 'Company', 'Notes']
        def core():
            a = sample('core', [header,
                ['Dr. José Alder', 'mailto:JOSE@EXAMPLE.COM', '07700 900142'],
                ['Alder, Jose', 'jose@example.com', '+44 7700 900142'],
                ['J. Alder', 'jose@example.com'], [], ['N/A', '-', '/', 'none'], header,
                ['Other Person', 'bad@@example.com'], ['Jose Alder', 'else@example.org'], []])
            require(a['counts'] == {'in': 8, 'clean': 4, 'merged': 1, 'empty': 2, 'not_contact': 1, 'uncertain_pairs': 2}, str(a['counts']))
            require(any('Invalid email' in r['reason'] for r in a['values_needing_review']))
        check('conservation, titles, accents, initial uncertainty and repeated headers', core)
        def chains():
            a = sample('chains', [header, ['Mira Vale', 'mira@example.com'], ['VALE MIRA', 'mira@example.com', '6045550134'], ['Mira Vale', 'other@example.net', '+16045550134']])
            require(a['counts']['clean'] == 1 and a['counts']['merged'] == 2)
            require(all(r.get('matched_to') for r in a['rows'][1:]))
        check('R1 transitive chain with checkable witnesses', chains)
        def pinyin():
            for latin in ('Wang Yinuo', 'Yinuo Wang', 'Wang Yi Nuo', 'Wangyinuo', 'Yinuowang'):
                a = sample('pinyin', [header, ['王一诺', 'one@example.com'], [latin, 'one@example.com']])
                require(a['counts']['merged'] == 1, latin)
            data = [['王一诺', 'one@example.com'], ['王依诺', 'one@example.com'], ['Wang Yinuo', 'one@example.com']]
            for perm in itertools.permutations(data):
                a = sample('bridge', [header] + list(perm))
                require(a['counts']['clean'] == 3 and a['counts']['uncertain_pairs'] == 2, str(a['counts']))
            a = sample('unknown', [header, ['林龘', 'one@example.com'], ['Lin Da', 'one@example.com']])
            require(a['counts']['merged'] == 0 and a['counts']['uncertain_pairs'] == 1)
            require(len(a['values_needing_review']) == 1)
        check('pinyin order, homophone bridge permutations and unsupported readings', pinyin)
        def names():
            require(name_relation(name_info('Vale, Dr. Mira'), name_info('Mira Vale')) == 'same', 'title with reversed name order')
            for a, b in [('E. Vale', 'Elena Vale'), ('Elena Vale Jr', 'Elena Vale'), ('Elena Mira Vale', 'Elena Vale'), ('Liz Vale', 'Elizabeth Vale')]:
                require(name_relation(name_info(a), name_info(b)) == 'compatible', a + ' / ' + b)
            require(name_relation(name_info('王一诺'), name_info('王依诺')) == 'different')
            require(name_relation(name_info('Mira Vale'), name_info('Tomas Reed')) == 'different')
        check('initials, suffixes, extra parts and nicknames never equal', names)
        def organisations():
            a = sample('orgs', [header, ['', 'office@example.com', '6045550100', 'Cedar Workshop'], ['', 'office@example.com', '6045550100', 'CEDAR WORKSHOP'], ['Mira Vale', 'office@example.com', '6045550100', 'Cedar Workshop']])
            require(a['counts']['clean'] == 2 and a['counts']['merged'] == 1)
        check('R6 organisations merge together, never into a person', organisations)
        def formatting():
            require(emails('mailto:Ａ＠ＥＸＡＭＰＬＥ．ＣＯＭ; b@example.org')[0] == ['a@example.com', 'b@example.org'])
            require(same_phone(('6045550134', ''), ('6045550134', '')), 'equal phone digits did not match')
            a = sample('equal-phones', [header, ['Mira Vale', 'first@example.com', '6045550134'], ['Mira Vale', 'second@example.org', '6045550134']])
            require(a['counts']['merged'] == 1, 'identical phones alone did not supply R1 evidence')
            for a, b in [('07700 900142', '+44 7700 900142'), ('0491 570 156', '+61 491 570 156'), ('6045550134', '+1 (604) 555-0134')]:
                require(same_phone(phones(a)[0][0], phones(b)[0][0]), a)
            require(not same_phone(('6045550134', '123'), ('6045550134', '124')))
        check('full-width multi-email cells, country codes and phone extensions', formatting)
        def phone_form():
            def clean_phones(tag, *source_phones):
                rows_ = [['Mira Vale', 'mira@example.com', value] for value in source_phones]
                a = sample('phone-form-' + tag, [header] + rows_)
                require(a['counts']['clean'] == 1 and a['counts']['merged'] == len(rows_) - 1, tag + ': ' + str(a['counts']))
                return a
            for tag, sources, expected in [
                    ('bare-and-plus', ('6045550134', '+1 (604) 555-0134'), ['+16045550134']),
                    ('plus-first', ('+1 (604) 555-0134', '6045550134'), ['+16045550134']),
                    ('all-bare', ('6045550134', '(604) 555-0134'), ['6045550134']),
                    ('bare-with-code', ('6045550134', '1 604 555 0134'), None),
                    ('double-zero', ('07700 900142', '0044 7700 900142'), ['+447700900142']),
                    ('extension', ('6045550134 ext 12', '+1 604 555 0134 x12'), ['+16045550134 x12']),
                    ('single-plus', ('+61 491 570 156',), ['+61491570156'])]:
                a = clean_phones(tag, *sources)
                got = a['records'][0]['values']['phones']
                if expected is None:  # no source wrote a country code: the longest form's digits, and no plus
                    expected = [''.join(c for c in max(sources, key=len) if c.isdigit())]
                require(got == expected, tag + ': clean phone ' + repr(got) + ', expected ' + repr(expected))
                require(not any('+' in v for v in a['records'][0]['observed_values']['phones']), tag + ': observed_values changed')
                require(not any('+' in v for r in a['rows'] for v in r['cleaned']['phones']), tag + ': row-level cleaned value changed')
            a = clean_phones('workbook', '6045550134', '+1 (604) 555-0134')
            with zipfile.ZipFile(io.BytesIO(workbook_bytes(a))) as z:
                sheet = z.read('xl/worksheets/sheet2.xml').decode('utf-8')
                styles = z.read('xl/styles.xml').decode('utf-8')
            cell = re.search(r'<c r="G2"[^>]*>.*?</c>', sheet).group(0)
            require('t="inlineStr"' in cell and 's="0"' in cell and '>+16045550134<' in cell and '<f' not in cell and '<v' not in cell,
                    'clean phone is not an inline text cell: ' + cell)
            require('<cellXfs count="2"><xf numFmtId="49"' in styles, 'cell style 0 is not the text format')
        check('clean phone keeps a source-written + or 00 country code, never adds one, and is a text cell', phone_form)
        def encoding_checks():
            text = 'Name;Email\r\nMira Vale;mira@example.com\r\n'
            for enc in ('utf-8', 'utf-8-sig', 'utf-16', 'gb18030', 'gbk', 'cp1252'):
                path = folder / ('encoding-' + enc + '.csv')
                path.write_bytes(text.encode(enc))
                a = build_audit([path], encoding=enc)
                require(a['counts']['clean'] == 1, enc)
            try:
                decode_csv(b'\xff\x00\x81')
            except Refused:
                pass
            else:
                raise AssertionError('unknown encoding accepted')
        check('all documented encodings and ambiguous encoding refusal', encoding_checks)
        def headers():
            a = sample('headers', [['Autumn visitors'], [], ['Name', 'Name', 'Contact'], ['First', 'Last', 'E-mail Address'], ['Mira', 'Vale', 'mira@example.com'], ['Mira', 'Vale', 'mira@example.com']])
            require(a['sources'][0]['header_rows'] == [1, 2, 3, 4])
            require(a['counts']['merged'] == 1)
        check('title, blank preamble, multirow headers and split names', headers)
        def injection():
            a = sample('inert', [header, ['=HYPERLINK("https://example.com")', '<script>alert(1)</script>', '6045550134', '', '=1+1']])
            page = page_html(a)
            require('<script>' not in page and '&lt;script&gt;' in page)
            with zipfile.ZipFile(io.BytesIO(workbook_bytes(a))) as z:
                require(all(b'<f>' not in z.read(n) for n in z.namelist() if n.startswith('xl/worksheets/')))
            dest = folder / 'restored'
            audit_path = folder / 'inert-audit.json'
            audit_path.write_text(json.dumps(a), encoding='utf-8')
            restore(audit_path, dest)
            require((folder / 'inert.csv').read_bytes() == (dest / 'inert.csv').read_bytes())
        check('HTML escaping, inert workbook formulas, exact byte restoration', injection)
        def xlsx_checks():
            require(numeric_text('6045550134.0') == '6045550134', 'integral number cell retained a decimal zero')
            require(numeric_text('6.045550134E9') == '6045550134', 'number-cell exponent changed the phone')
            path = folder / 'inline.xlsx'
            path.write_bytes(xlsx_bytes([('One', [header, ['Mira Vale', 'mira@example.com', '6045550134']]), ('Two', [header, ['Mira Vale', 'mira@example.com', '+16045550134']])]))
            a = build_audit([path])
            require(a['counts']['merged'] == 1 and len(a['sources']) == 2)
            require({r['sheet'] for r in a['rows']} == {'One', 'Two'})
            # Independent, shared-string fixture with a number phone, date style, merge and a formula.
            fixture = folder / 'shared.xlsx'
            data = path.read_bytes()
            stream = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(stream, 'w') as z:
                for n in src.namelist():
                    if n == 'xl/worksheets/sheet1.xml':
                        z.writestr(n, '<worksheet xmlns="' + NS + '"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row><row r="3"><c r="A3" t="s"><v>1</v></c><c r="B3" t="s"><v>2</v></c><c r="C3" t="s"><v>3</v></c></row><row r="4"><c r="A4" t="s"><v>4</v></c><c r="B4"><v>6045550134</v></c><c r="C4" s="1"><v>46083</v></c><c r="D4"><f>1+1</f><v>2</v></c></row></sheetData><mergeCells><mergeCell ref="A1:D1"/></mergeCells></worksheet>')
                    else:
                        z.writestr(n, src.read(n))
                z.writestr('xl/sharedStrings.xml', '<sst xmlns="' + NS + '">' + ''.join('<si><t>' + s + '</t></si>' for s in ['Visitors', 'Name', 'Phone', 'Date', 'Mira Vale']) + '</sst>')
            fixture.write_bytes(stream.getvalue())
            a = build_audit([fixture])
            require(a['sources'][0]['header_rows'] == [1, 2, 3])
            require(a['rows'][0]['original'] == ['Mira Vale', '6045550134', '46083', '=1+1'])
            require(a['rows'][0]['cell_metadata'][-1]['stored'] == '2')
        check('XLSX inline/shared strings, sheets, numeric phone, dates, merges, formulas', xlsx_checks)
        def outputs():
            path = folder / 'run.csv'
            path.write_text('Name,Email\nMira Vale,mira@example.com\nMira Vale,mira@example.com\n', encoding='utf-8')
            before = path.read_bytes()
            dest = folder / 'run-output'
            a = write_run([path], dest)
            require(path.read_bytes() == before)
            require({p.name for p in dest.iterdir()} == {'clean.xlsx', 'report.html', 'audit.json'})
            require(equation(a['counts']) in (dest / 'report.html').read_text())
            try:
                write_run([path], dest)
            except Refused:
                pass
            else:
                raise AssertionError('existing output overwritten')
            broken = json.loads(json.dumps(a))
            broken['counts']['clean'] += 1
            try:
                validate_audit(broken)
            except Refused:
                pass
            else:
                raise AssertionError('broken counts accepted')
        check('three artifacts, conserved counts, source bytes and no overwrite', outputs)
        def inferred_columns():
            for identity_headers in (['Email', 'Phone'], ['Return route', 'Reach digits']):
                a = sample('badge-columns', [
                    ['Badge inscription'] + identity_headers + ['Tracking token', 'Visit remarks'],
                    ['Celia Ashford', 'celia@example.org', '07700 900163', 'A-19', 'Bring paper samples'],
                    [' CELIA ASHFORD ', 'CELIA@EXAMPLE.ORG', '+44 7700 900163', 'A-20', 'Evening booking']])
                require(a['counts']['in'] == 2 and a['counts']['merged'] == 1,
                        'unusual headers did not yield one merge: ' + str(a['counts']))
                require(a['sources'][0]['column_roles'] == ['name', 'email', 'phone', None, None],
                        'unexpected inferred roles: ' + str(a['sources'][0]['column_roles']))
                require(a['sources'][0].get('column_role_evidence'), 'role inference has no audit evidence')
            a = sample('partly-named', [['First name', 'Clan marker', 'Return route'],
                                      ['Celia', 'Ashford', 'celia@example.org'],
                                      ['Celia', 'Ashford', 'celia@example.org'],
                                      ['Celia', 'Bellwood', 'celia@example.org']])
            require(a['counts']['clean'] == 2 and a['counts']['merged'] == 1,
                    'unknown surname column caused different family names to merge')
        check('review regression: column roles inferred from values under unusual wording', inferred_columns)
        def missing_name_warning():
            import contextlib
            path = folder / 'routing-only.csv'
            path.write_text('Routing ID,Email,Phone\nR-81,desk@example.net,6045550183\nR-82,desk@example.net,6045550183\n', encoding='utf-8')
            destination = folder / 'routing-output'
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main([str(path), '--out', str(destination)])
            require(status == 0, 'warning run failed instead of preserving the rows')
            require(output.getvalue().splitlines()[0].startswith('WARNING: No name column found'),
                    'summary conceals missing name column: ' + output.getvalue().splitlines()[0])
            a = json.loads((destination / 'audit.json').read_text(encoding='utf-8'))
            require(a.get('warnings') and a['counts']['merged'] == 0, 'missing names were guessed or not audited')
            page = (destination / 'report.html').read_text(encoding='utf-8')
            require('No name column found' in page and page.index('No name column found') < page.index(equation(a['counts'])),
                    'report conceals the warning below the normal count')
            with zipfile.ZipFile(destination / 'clean.xlsx') as z:
                summary = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
                text = list(summary.itertext())
                require(any('No name column found' in v for v in text) and
                        next(i for i, v in enumerate(text) if 'No name column found' in v) < text.index(equation(a['counts'])),
                        'workbook Summary disagrees with the warning')
        check('review regression: absent name column warns before count in summary and report', missing_name_warning)
        def grouped_header():
            path = folder / 'visitor-blocks.xlsx'
            values = [['Autumn material visitors'], ['Personal block', '', 'Email', 'Phone'],
                      ['Forename', 'Surname', 'Dispatch token', 'Call token'],
                      ['Celia', 'Ashford', 'celia@example.org', '6045550183'],
                      ['CELIA', 'ASHFORD', 'celia@example.org', '+1 604 555 0183']]
            initial = xlsx_bytes([('Visitors', values)])
            stream = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(initial)) as src, zipfile.ZipFile(stream, 'w') as dest:
                for filename in src.namelist():
                    content = src.read(filename)
                    if filename == 'xl/worksheets/sheet1.xml':
                        node = ET.fromstring(content)
                        merged = ET.SubElement(node, '{%s}mergeCells' % NS, count='2')
                        for ref in ('A1:D1', 'A2:B2'):
                            ET.SubElement(merged, '{%s}mergeCell' % NS, ref=ref)
                        content = ET.tostring(node)
                    dest.writestr(filename, content)
            path.write_bytes(stream.getvalue())
            a = build_audit([path])
            require(a['sources'][0]['header_rows'] == [1, 2, 3],
                    'title/group/field rows were not all headers: ' + str(a['sources'][0]['header_rows']))
            require(a['sources'][0]['column_roles'] == ['first', 'last', 'email', 'phone'],
                    'split-name roles were lost: ' + str(a['sources'][0]['column_roles']))
            require(a['counts']['in'] == 2 and a['counts']['merged'] == 1, str(a['counts']))
            require(a['records'][0]['primary_name'] == 'Celia Ashford', 'first and last names not combined')
            a = sample('split-chinese', [['Forename', 'Surname', 'Dispatch token', 'Call token'],
                                       ['雨婷', '林', 'yuting@example.net', '6045550183'],
                                       ['雨婷', '林', 'yuting@example.net', '+16045550183']])
            require(a['counts']['merged'] == 1 and key(a['records'][0]['primary_name']) == '林雨婷',
                    'Chinese split name did not retain surname-first order')
        check('review regression: merged group header above field row and split names', grouped_header)
        def automatic_encodings():
            for enc, name, note in [('gbk', '林雨婷', '纸张样品'), ('gb18030', '王一诺', '\U00020000'),
                                    ('cp1252', 'Renée Ashford', 'Paper samples'),
                                    ('cp1252', 'François Ashford', 'Paper samples'),
                                    ('utf-8', 'José Ashford', 'Paper samples')]:
                path = folder / ('automatic-' + enc + '.csv')
                text = 'Name;Email;Phone;Notes\r\n%s;person@example.com;6045550183;%s\r\n%s;person@example.com;6045550183;%s\r\n' % (name, note, name, note)
                path.write_bytes(text.encode(enc))
                a = build_audit([path])
                require(a['counts']['merged'] == 1 and a['rows'][0]['original'][0] == name,
                        enc + ' decoded or matched incorrectly')
            try:
                decode_csv(b'Name,Email,Notes\nCelia Ashford,celia@example.org,\xa1\xa1\n')
            except Refused as exc:
                message = str(exc)
                require('gbk' in message and 'cp1252' in message and 'sample' in message.lower() and '--encoding' in message,
                        'ambiguity message lacks candidate samples: ' + message)
            else:
                raise AssertionError('genuinely ambiguous punctuation was guessed')
            try:
                decode_csv(b'Name,Email,Notes\nCelia Ashford,celia@example.org,' + b'Long preamble. ' * 30 + b'\xa1\xa1\n')
            except Refused as exc:
                require('¡¡' in str(exc) and '\u3000' in str(exc), 'samples omit the differing characters after a long prefix')
            else:
                raise AssertionError('long ambiguous reading was guessed')
        check('review regression: automatic legacy encodings and samples for real ambiguity', automatic_encodings)
        def pinyin_spellings():
            cases = [('陈子桐', 'Chén Zǐtóng'), ('何雨童', 'he yu tong'),
                     ('何雨童', 'HÉ, Yǔtóng'), ('何雨童', 'HEYUTONG'),
                     ('章雨琪', 'ZHANG, Yuqi'), ('周思墨', 'Zhōu Sīmò')]
            for chinese, latin in cases:
                path = folder / 'material-visitors-gb.csv'
                text = io.StringIO(newline='')
                csv.writer(text, delimiter=';').writerows([
                    ['Attendee caption', 'Return route', 'Reach digits', 'Notes'],
                    [chinese, 'visitor@example.org', '6045550186', '纸样预约'],
                    [latin, 'VISITOR@EXAMPLE.ORG', '+1 604 555 0186', 'Evening visit']])
                path.write_bytes(text.getvalue().encode('gb18030'))
                a = build_audit([path])
                require(a['counts']['merged'] == 1 and a['counts']['clean'] == 1,
                        chinese + ' / ' + latin + ': ' + str(a['counts']))
                merged = next(r for r in a['rows'] if r['disposition'] == 'merged')
                require('pinyin' in merged['reason'].lower() and chinese in merged['reason'],
                        'merge reason omits the character/pinyin evidence: ' + merged['reason'])
                a = sample('phone-linked-pinyin', [header, [chinese, '', '07700 900168'],
                                                  [latin, '', '+44 7700 900168']])
                require(a['counts']['merged'] == 1, 'phone evidence did not merge ' + latin)
        check('pinyin regression: GB18030 names, joined/spaced/comma spellings and tones', pinyin_spellings)
        def pinyin_name_alone():
            a = sample('separate-invitations', [header,
                       ['陈子桐', 'first@example.org', '6045550186'],
                       ['CHEN, Zitong', 'second@example.net', '7785550187']])
            require(a['counts']['clean'] == 2 and a['counts']['merged'] == 0 and a['counts']['uncertain_pairs'] == 1,
                    'pinyin-only evidence was merged or omitted from review: ' + str(a['counts']))
            require('pinyin' in a['uncertain'][0]['reason'].lower(), 'uncertain reason omits romanisation')
        check('pinyin regression: same romanised name without identifiers stays uncertain', pinyin_name_alone)
        def pinyin_one_link():
            data = [['何雨童', 'appointment@example.org', '6045550186'],
                    ['何雨桐', 'separate@example.net', '7785550187'],
                    ['HE, Yutong', 'appointment@example.org', '']]
            for permutation in itertools.permutations(data):
                a = sample('one-linked-booking', [header] + list(permutation))
                require(a['counts']['clean'] == 2 and a['counts']['merged'] == 1 and a['counts']['uncertain_pairs'] == 1,
                        'one-link homophone case: ' + str(a['counts']))
                rec = {r['original'][0]: r['record'] for r in a['rows']}
                require(rec['HE, Yutong'] == rec['何雨童'] and rec['何雨童'] != rec['何雨桐'], 'wrong homophone joined')
                require(set(a['uncertain'][0]['records']) == {rec['何雨童'], rec['何雨桐']}, 'other homophone omitted from review')
        check('pinyin regression: one linked homophone merges, the other stays uncertain in every row order', pinyin_one_link)
        def pinyin_family_address():
            for chinese in ('章乐童', '章乐桐'):
                require(name_relation(name_info(chinese), name_info('ZHANG, Yuetong')) == 'same',
                        'permitted polyphonic reading not recognized: ' + chinese)
            data = [['章乐童', 'family@example.org', ''], ['章乐桐', 'family@example.org', ''],
                    ['ZHANG, Yuetong', 'family@example.org', '']]
            for permutation in itertools.permutations(data):
                a = sample('family-replies', [header] + list(permutation))
                require(a['counts']['clean'] == 3 and a['counts']['merged'] == 0 and a['counts']['uncertain_pairs'] == 2,
                        'shared-family homophone case: ' + str(a['counts']))
                rec = {r['original'][0]: r['record'] for r in a['rows']}
                expected = {frozenset((rec['ZHANG, Yuetong'], rec['章乐童'])),
                            frozenset((rec['ZHANG, Yuetong'], rec['章乐桐']))}
                require({frozenset(u['records']) for u in a['uncertain']} == expected, 'ambiguous row not listed against both')
                require(all('pinyin' in u['reason'].lower() for u in a['uncertain']), 'family ambiguity reason omits pinyin')
        check('pinyin regression: shared family address merges neither homophone in every row order', pinyin_family_address)
        def pinyin_multiple_readings():
            for family in ('Dan', 'Shan', 'Chan'):
                for given in ('Le', 'Yue', 'Yao', 'Lao'):
                    require(name_relation(name_info('单乐'), name_info(family + ', ' + given)) == 'same',
                            'missing reading: ' + family + ' ' + given)
            for spelling in ('LǙ Míng', 'Lü Ming', 'LV, Ming', 'Lu: Ming'):
                require(name_relation(name_info('吕鸣'), name_info(spelling)) == 'same', spelling)
            require(name_relation(name_info('何雨童'), name_info('He Tong Yu')) == 'different',
                    'reversing given-name syllables changed the name silently')
            a = sample('unsupported-still-separate', [header, ['林龘', 'desk@example.org'], ['Lin Da', 'desk@example.org']])
            require(a['counts']['merged'] == 0 and a['counts']['uncertain_pairs'] == 1 and a['values_needing_review'],
                    'unsupported character was guessed')
        check('pinyin regression: all supported readings, vowel forms, syllable order and unknown characters', pinyin_multiple_readings)
    for name, ok, error in checks:
        print(('PASS ' if ok else 'FAIL ') + name + (': ' + error if error else ''))
    print('SELFTEST: %d/%d passed' % (sum(ok for _, ok, _ in checks), len(checks)))
    return 0 if all(ok for _, ok, _ in checks) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='*', type=Path)
    parser.add_argument('--out', type=Path, help='new output folder (required except for --selftest)')
    parser.add_argument('--demo', action='store_true', help='run the bundled fictional example')
    parser.add_argument('--selftest', action='store_true', help='run named behavioral checks')
    parser.add_argument('--encoding', help='explicit CSV encoding when automatic detection is ambiguous')
    parser.add_argument('--header-row', type=int, help='last header row, 1-based; applies to each source sheet')
    parser.add_argument('--restore', type=Path, metavar='AUDIT_JSON', help='restore byte-identical source copies into --out')
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.out:
        parser.error('--out is required; choose a new output folder')
    try:
        if args.restore:
            if args.inputs or args.demo:
                parser.error('--restore cannot be combined with inputs or --demo')
            print('Restored %d source files; SHA-256 verified.' % restore(args.restore, args.out))
            return 0
        if args.demo and args.inputs:
            parser.error('--demo cannot be combined with input files')
        paths = sorted((ROOT / 'references/example').glob('*.csv')) if args.demo else args.inputs
        if not paths:
            parser.error('provide one or more input files, or use --demo')
        audit = write_run(paths, args.out, args.encoding, args.header_row)
        for warning in audit.get('warnings', []):
            print('WARNING: ' + warning['message'])
        print(equation(audit['counts']))
        review_count = len(audit['values_needing_review'])
        print(pair_label(audit['counts']['uncertain_pairs']) + '; %d %s needing review' %
              (review_count, 'value' if review_count == 1 else 'values'))
        print('Wrote clean.xlsx, report.html, audit.json to ' + str(args.out))
        return 0
    except (Refused, OSError, UnicodeError, csv.Error, ValueError) as exc:
        print('Cannot complete run: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

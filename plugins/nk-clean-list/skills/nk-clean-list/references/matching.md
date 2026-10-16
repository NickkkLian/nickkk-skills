# Matching and input decisions

## Rules

1. Shared valid email or phone + same person name → merge. A connected chain may
   merge only if every pair has the same name. Each merged row cites a directly
   connected source row as its witness; the witness need not be the kept row.
2. Shared identifier + compatible names (initial, added/omitted part, suffix,
   possible nickname) → uncertain, separate contacts.
3. Shared identifier + plainly different names → separate contacts. A common
   full name part can conservatively create an uncertain pair; it never merges.
4. Same name without a shared identifier → uncertain, separate contacts.
5. Conflicting alternatives → no arbitrary winner. A direct bridge joins neither
   side; a longer connected component with incompatible names stays separate.
6. Organisation-only rows use organisation names in place of person names. They
   do not merge with person rows.

Missing names and unresolvable Chinese-to-pinyin comparisons with shared identifiers
are uncertain. Invalid email/phone tokens are retained and flagged; they do not
provide match evidence. Unrelated rows are not listed just because a name is unknown.

## Name formatting

Unicode compatibility width normalization, case folding, accent removal, punctuation,
spacing, part order, and Dr/Mr/Mrs/Ms/Prof title tokens are formatting. Suffixes
remain significant. The tool does not invent a nickname dictionary. A shared name
part can suggest compatibility for review, but never equality.

Chinese names are equal only when their characters are equal after width/spacing
normalization. Simplified and traditional characters are not silently substituted
for one another. Pinyin comparison applies only between a Chinese name and a Latin
name, using the table below. Equal pinyin never makes two Chinese spellings equal.

## Pinyin coverage and ambiguity

`pinyin.json` is the maintained coverage list, authored for this skill without an
external dataset. It includes common surnames such as 王, 李, 张, 陈, 刘, 林, 周 and
given-name characters such as 一, 诺, 晓, 雯, 雨, 明, 文, 婷. Some traditional characters
are included individually. Compound surnames are listed explicitly; if any character
has no supported reading, that name is unresolvable too.

Arrays enumerate the readings, including polyphonic characters. Tones are removed;
ü is written `v` and Latin input accepts ü/v/u:. Case, spaces, tone marks and comma
formatting do not change the comparison. Family-first spellings can join given-name
syllables (`Zhou Zimo`), space them (`He Yu Tong`) or use a comma (`HE, Yutong`).
Given-first forms from the brief also work, moving the family chunk as a whole;
individual given-name syllables are never reordered. A dynamic comparison checks
every listed reading without generating exponentially many aliases or selecting
the most common pronunciation. There is no lookup or fallback pronunciation.

A matched character/pinyin name needs a shared valid email or phone to merge (R1).
Its reason identifies the characters, the pinyin reading and the shared identifier.
Without a shared identifier the pair stays uncertain (R4). If a pinyin row fits two
different character names and links only to one, it merges with that one and remains
uncertain against the other. If it links to both through a shared family address or
phone, it joins neither, with an uncertain pair against each (R5). Character names
are still compared literally, so homophones cannot collapse into one contact.

An exact Chinese spelling can still match itself without transliteration. A name
with an unsupported character is added to Values needing review. If it shares an
identifier with a Latin-name row, that pair is uncertain with the character-level
reason. If no candidate partner exists, its review item remains visible without a
fabricated pair. The README lists all covered characters; the JSON records their
readings. This is a finite Mandarin table, not a complete name or dialect dictionary.

## Identifiers

Email normalization trims whitespace, lowercases, normalizes width and removes
`mailto:`. Semicolons, commas and whitespace separate multiple addresses. No
provider-specific dot or plus-tag rules. The syntax check is deliberately modest;
it is not an RFC validator or delivery check. Display-name mailbox strings may need
review. The original cell is retained regardless of parsing.

Phone normalization removes spaces and punctuation. Numeric XLSX cells are expanded
from decimal/exponent notation without floating-point rounding. Equal digits match;
a national number can match a recognized 1–3 digit country calling-code prefix,
dropping its leading trunk zero. `00` and `+` international forms are recognized.
Matching compares digits only; the plus matters only for how the clean number is
written (see Assembly and output). No country is inferred from a name, email or address. This permissive suffix rule is
required by the brief and can equate ambiguous national numbers across countries.

Extensions must agree. Missing/different extensions do not support a phone merge;
same/compatible names sharing the base number are uncertain. An independently shared
email still provides R1 evidence. Several phone values may be separated by semicolons,
slashes or newlines. Invalid/unrecognized forms stay in `unverified_phones`.

## Readers

CSV row numbers are logical spreadsheet rows, not physical text lines inside quoted
multiline cells. Empty lines between data remain rows. Unicode whitespace-only rows
after the last content row are not counted. Byte-exact originals preserve even those
trailing rows. UTF-8/BOM detection precedes legacy decoding. Strict GBK, GB18030 and
Windows-1252 candidates are compared without replacement characters. Identical
GBK/GB18030 text is one reading, recorded as GBK when that narrower codec suffices.
Coherent CJK runs/headings favor the Chinese reading. Accented Latin words favor
Windows-1252 when the competing reading embeds stray CJK characters in Latin words.
This is deterministic text evidence, not proof of the exporter's original codec.
If neither reading has decisive evidence, refuse with short samples of each and
request `--encoding`. Symbol-only or very short legacy text can remain ambiguous.

Header detection examines the first 50 possible header rows and looks for the
transition to contact values. The latest field-label row before that transition
is selected, so an earlier title/group row cannot consume the real field row as
data. Everything through the final field row is recorded as header/preamble;
blank/contact rows below it remain data. There is no three-row header limit.
Column aliases are defined in `HEADER_MAP` through `ALIASES` in the implementation.
Roles also use up to 200 nonempty sampled values per column. A Latin value matching
a supported Chinese name in that column counts as a name shape, including lowercase
spaced syllables or a fully joined spelling. Valid email/phone
shapes supply missing roles or correct contradictory labels. Name/organisation
shapes and adjacent name parts supply remaining roles. Recognized auxiliary fields
such as IDs, notes, dates and countries are excluded from contact-role inference.
Recognized person-name labels are not changed to organisations just because a
surname resembles an organisation word. Chinese split names use surname-first
order; Latin split names use given-name-first order.

Multiple equally plausible name columns remain unassigned. No identified name
column produces a source-specific warning in the audit, the terminal's first
summary line, the report before its count, and the workbook Summary. Rows are still
accounted for and organisation matching can still operate, but person matching
must be reviewed. `column_role_evidence` records the labels, shape counts and
reason for every inferred role. Data cells in
merged ranges are not propagated. A repeated header is `not_contact`, with a reason.
Other non-data structures are conservatively retained as contacts or empty rows;
this version does not guess that a total or separator row can be discarded.

`--header-row N` explicitly selects the last header row. It applies to all input
sheets in that run. Blank sheets contribute a source entry and zero data rows.
Nonempty sheets are accounted for even when column roles cannot all be identified;
the missing-name warning requires review before relying on the result. They are
not silently skipped. Files with identical basenames require separate runs or
distinctly named copies so audit source references remain unambiguous.

## Assembly and output

The first source row in a contact is kept; other rows are merged. Source order is
CLI file order, then workbook sheet order, then spreadsheet row order. Record IDs
are deterministic for that ordering. No timestamps or random IDs are introduced.

Primary names/organisations use the first nonempty normalized value. All spelling
variants and different emails remain. Equivalent phone formats use the longest
digit form, with the alternatives in `observed_values` (digits only) and an assembly
change record. The clean number starts with `+` when a source row wrote that form
with an explicit country code, as `+` or `00`: `6045550134` and `+1 (604) 555-0134`
become `+16045550134`. A form that no row wrote with a country code stays digits
only, even when it is long enough to contain one (`1 604 555 0134` keeps its
eleven digits and gets no plus); a country code is never added or guessed. An
extension follows as before: `+16045550134 x12`. Every workbook cell is written as text, so a
spreadsheet program shows the plus and does not read the value as a formula or a
number. The cell exactly as typed stays in the row's `original` values and in the
report's source rows. Other columns are preserved in original rows rather than guessed into a
single address, date or note. `changes` and the workbook account for normalization.

All workbook cells are text. Original formulas cannot execute in the output. XLSX
date serials, styles, raw XML and cached formula values remain in audit metadata;
the tool does not recreate Excel's presentation or calculate formulas. The entire
source workbook can be restored exactly from the embedded source bytes.

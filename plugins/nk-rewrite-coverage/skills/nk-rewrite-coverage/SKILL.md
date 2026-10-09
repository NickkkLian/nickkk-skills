---
name: nk-rewrite-coverage
description: Check what a document rewrite lost. Use when an agent tidied, shortened or restructured a document, resumed after compaction, or a reviewer suspects missing detail. Count numbers, links, Markdown code, quoted strings and capitalised Latin names as kept, fewer or lost; retain heading, bold-term and table-cell checks. Produce one offline HTML page with marked old locations and the new text, plus optional JSON. Does not judge reasoning or semantic accuracy.
license: MIT
metadata:
  provenance: own practice; invented validation examples
  version: 0.2.2
---
# Rewrite coverage

**A rewrite is a retelling from memory, and memory keeps conclusions and drops process.** A 630-line
analysis rewritten after a context compaction came back as 755 lines that read fine — and had lost eight
reasoning chains compressed into one, a timetable, five verbatim quotations, a placement table and a
cross-reference section, six whole blocks. Nothing in the new text said anything was missing. The parts
that vanish are exactly the ones a reader needs to check or reuse the work.

Use this after a rewrite to find literal details the old document had and the new one no longer contains. The output is evidence for review; it cannot establish that a rewrite is complete or correct.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## Procedure

1. Keep the old text in a separate file. Both inputs must be nonempty UTF-8 text or Markdown; giving the same file twice is refused.
2. Run `python3 <skill-dir>/scripts/rewrite_coverage.py old.md new.md --html rewrite-coverage.html`.
3. Read the first line, then open the local report. It counts numbers, links, code items, quoted strings and capitalised Latin names; headings, bold terms and selected table cells appear alongside them. Lost items are red with a solid underline in the old text; fewer items are amber with a dashed underline. The list links to every old location. The new text is beside it on a wide screen and available through the New text link on a phone. Use System, Light or Dark to change the theme.
4. Review every lost or fewer item against the source and restore it or record why it changed. A fewer item appeared more times before than after; all its old locations are shown because the missing one cannot be inferred.
5. Rerun after restoring details. Exit 1 means anything is lost or fewer; exit 0 means every extracted item is kept; exit 2 means a refusal or command error. A ledger annotates the evidence and never overrides these exit codes.
6. When you report to the user, give the tool's first line first, exactly as printed. If any name is in the list, say that names are the least certain kind (the tool calls them tentative names). Keep what you add from your own reading apart from the tool's list, and say which is which.

The English demo prints:

```text
distinct items · kept 1 of 5 numbers, 2 of 3 links, 1 of 2 code items, 0 of 2 quoted strings, 1 of 2 tentative names; lost: 3 numbers, 1 link, 1 code item, 1 quoted string, 1 tentative name, 1 bold term, 1 table cell; fewer: 1 number (3→1 occurrences), 1 quoted string (3→1 occurrences)
```

## Demos and machine output

```sh
python3 <skill-dir>/scripts/rewrite_coverage.py <skill-dir>/examples/english-old.md <skill-dir>/examples/english-new.md --html english-report.html
python3 <skill-dir>/scripts/rewrite_coverage.py <skill-dir>/examples/english-old.md <skill-dir>/examples/english-new-openings.md --html openings-report.html
python3 <skill-dir>/scripts/rewrite_coverage.py <skill-dir>/examples/chinese-old.md <skill-dir>/examples/chinese-new.md --html chinese-report.html
python3 <skill-dir>/scripts/rewrite_coverage.py old.md new.md --json --html rewrite-coverage.html > coverage.json
python3 <skill-dir>/scripts/rewrite_coverage.py --selftest
```

Both demos and the extra English rewrite intentionally exit 1. Their exact lost and fewer sets are declared in [examples/EXPECTED.md](examples/EXPECTED.md). JSON schema version 2 and the summary/report counts count distinct items, while each item retains its mention counts and all old locations. The page is still produced with `--json`. Counts labelled kept exclude fewer groups. Different kinds can overlap.

`--out unaccounted.md` retains the old list of structural items. `--min-len` affects that list only. `--ledger ledger.md` adds `[renamed]`, `[merged]`, `[restored]` or `[dropped]` annotations; see [references/ledger-example.md](references/ledger-example.md). The default report refuses an existing file; an explicit `--html` path allows replacement. Inputs and ledgers are protected from output collisions. Directory inputs are refused by name.

## Matching and limits

Read [references/matching-rules.md](references/matching-rules.md) when interpreting ambiguous matches. Thousands separators, full-width digits and small-number word spellings normalize; heading and list numbering is excluded in both texts. Versions such as 3.2.1 stay one item. Numbers inside wholly lost code/link items are covered by those items. Bare e-mail addresses count as links. Links normalize host and scheme case and terminal path slashes. Code is exact after removing fence/container indentation and normalizing line endings. Straight, curly and Chinese quote marks and 《》 titles are recognized; a closing comma or full stop may move outside. Quote contents can remain without their enclosing marks. Latin names require textual evidence and can occur inside Chinese sentences; lost/fewer quotations cover contained names.

## What it cannot see

- The tool does not judge rephrased sentences, lost reasoning, facts moved to the wrong section, or digits whose meaning changed.
- Names are last as tentative names, the least certain kind.
- It deliberately misses one-word names only at sentence/heading starts, names that are months, and single label values such as Friday in Next meeting: Friday.
- Lowercase names, Chinese personal names, titles, units, currencies and CSV are excluded.
- Interior capitalisation can remain ambiguous.
- Number words above twenty and standalone one/一 are deliberately ignored, even for genuine quantities.
- A table row is compared by its first cell, or its second when the first column counts rows.
- Other cells can change without a structural warning.
- Code and links use the documented text/Markdown forms, not a full Markdown parser.
- An opening word glued to a name can be reported as a lost name: `On Windows` was reported lost while Windows was still in the new text.
- The first word of a table cell can be taken for a name.
- A small number can be hidden when the same digit appears in the new text as a label, such as "Step 3", a numbered table row or a footnote mark: the lost number is then counted as kept.

## Provenance

Own practice, 2026-08: the compaction rewrite described above, followed by four rounds of an auditor
breaking the first version of this tool (a positive probe that was always true; a percentage that a term
dump could game; a truncated file that still scored mid-range).

The original three structural checks and their self-test fixtures are retained. This upgrade was validated with invented English and Chinese examples and standard-library tests, including controlled rule-disable runs. Two fix rounds embedded four independent pairs, their hand-listed expectations and fourteen probes in the script; checker files are not installed. The HTML uses the sibling review's green, paper-card and side-by-side visual approach. No browser rendering was run by this agent.

---
name: nk-rewrite-coverage
description: After rewriting a long document — a spec, a research report, a handbook — list what the old version had that the new one no longer mentions, and account for every item with a three-state verdict before the rewrite is accepted. Use when an agent rewrote instead of edited, after a context compaction, when a "clean-up" made a file shorter, or when a reviewer suspects detail was lost. scripts/rewrite_coverage.py extracts headings, bold terms and table cells from the old text and reports the unaccounted ones; a percentage is never the criterion, the ledger is. Not a diff tool.
license: MIT
metadata:
  provenance: own practice (2026-08); no external source
  version: 0.1.0
---
# Rewrite coverage

**A rewrite is a retelling from memory, and memory keeps conclusions and drops process.** A 630-line
analysis rewritten after a context compaction came back as 755 lines that read fine — and had lost eight
reasoning chains compressed into one, a timetable, five verbatim quotations, a placement table and a
cross-reference section, six whole blocks. Nothing in the new text said anything was missing. The parts
that vanish are exactly the ones a reader needs to check or reuse the work.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- The new file replaced the old one instead of patching it (an agent "cleaned up", "restructured",
  "rewrote for clarity", or resumed after compaction).
- The new file is shorter, or the diff is the whole file.
- The document is one people rely on for detail: specs, research, procedures, handbooks.

## Procedure

1. Keep the old version (git has it: `git show HEAD:path > /tmp/old.md`).
2. `python3 <skill-dir>/scripts/rewrite_coverage.py old.md new.md --out unaccounted.md`
   prints every heading, bold term and table cell of the old text that does not occur in the new, plus
   structure hints (headings / table rows / quote lines / character count, old → new).
3. **Read the hints first.** New text under 60% of the old characters: check for truncation before
   anything else. Old had headings, new has none: the rewrite kept the words and lost the structure.
4. **Give every unaccounted item one verdict** in a ledger file (one line each, the item text followed
   by a tag): `[renamed]` same content, other words · `[merged]` folded into another section ·
   `[restored]` it was lost and you put it back · `[dropped]` removed on purpose, with the reason.
5. `rewrite_coverage.py old.md new.md --ledger ledger.md` exits 0 only when every item has a tag.
   Commit the ledger with the rewrite; it is the record of what this revision did to the previous one.
6. Anything tagged `[restored]`: restore it verbatim from the old file, not from memory.

## Why not a percentage

The existence test only asks whether the characters occur somewhere in the new text. Measured on real
rewrites: a "term dump" (every old term pasted into a list, no analysis, no quotations, no sections) scored
92%; an honest rewrite scored 51% because it renamed things. High does not mean nothing was lost; low does
not mean something was. The only output that carries information is the list, and the only criterion is
that each line on it has a human verdict.

## What it cannot see

- Content moved to the wrong section (the words exist, the place is wrong).
- A change in any other cell of a table row: each row is compared by one cell, the first, or the second
  when the first column only counts the rows (1, 2, 3 … in order). Codes and ids in a first column (200, #123)
  are compared as they are.
- Quotations that are no longer verbatim — compare those against the source, not against the old draft.
- A new file that is complete and wrong.
- Truncation of the new file is hinted by the character ratio only; confirm the file ends where it should.

## Provenance

Own practice, 2026-08: the compaction rewrite described above, followed by four rounds of an auditor
breaking the first version of this tool (a positive probe that was always true; a percentage that a term
dump could game; a truncated file that still scored mid-range). The tool was then demoted from a gate to
a list generator with a ledger rule. No external source.

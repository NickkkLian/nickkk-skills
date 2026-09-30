# A filled receipt (what "good" looks like)

```markdown
# Hand-back receipt

## What I did
Implemented the CSV importer in output/work/importer.py and its test file. Did not touch the exporter
(TASK.md: "not changing").

## How I verified it
$ python3 output/work/importer.py --selftest        → output/evidence/01-selftest.txt (exit 0, 14 checks)
$ python3 output/work/importer.py samples/bad.csv   → output/evidence/02-bad-input.txt (exit 2, no traceback)
$ python3 output/handback_check.py                  → output/evidence/03-handback.txt (exit 0)

## Unsure
- Whether the date parser should accept two-digit years; I made it reject them and left a note in
  pending/decisions/dates.md with the veto point.
- The bad.csv sample only covers missing columns, not wrong encodings.

## Boundary crossings
none
```

The "Unsure" section is graded highest: an executor who found a gate they could get around, or a case
nobody had thought of, and wrote it down, did the most valuable work in the package.

# Ledger example

`rewrite-ledger-2026-09-15.md`, committed next to the rewritten document:

```markdown
# Rewrite ledger — spec.md, 2026-09-15 (old: a1b2c3d, new: this commit)

- Caveats [merged] into "Setup", second paragraph
- throughput [dropped] duplicated the chart in section 4; chart kept
- weekdays [restored] verbatim from old §3
- Failure modes table [restored] all 6 rows, from old §5
- Q&A appendix [renamed] now "Questions we were asked"
```

Rules of the ledger:
- one line per unaccounted item, the item text first, then exactly one tag;
- `[dropped]` always says why; `[restored]` means restored from the old text, not rewritten;
- retain the ledger with the rewrite as the human record of decisions;
- the ledger annotates the report but does not change literal matching or the exit code.

Command line:
```bash
python3 scripts/rewrite_coverage.py spec-old.md spec-new.md --out unaccounted.md --html coverage.html   # exit 1: lost or fewer items
# … write the ledger …
python3 scripts/rewrite_coverage.py spec-old.md spec-new.md --ledger rewrite-ledger.md --html coverage.html
# exit 0 only when every extracted item is kept; acknowledged losses still exit 1
```

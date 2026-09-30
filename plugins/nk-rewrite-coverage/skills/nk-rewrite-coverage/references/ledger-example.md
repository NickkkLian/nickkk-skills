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
- the ledger is part of the change: a rewrite without one is a rewrite nobody checked.

Command line:
```bash
git show HEAD:docs/spec.md > /tmp/spec-old.md
python3 scripts/rewrite_coverage.py /tmp/spec-old.md docs/spec.md --out /tmp/unaccounted.md   # exit 1: work to do
# … write the ledger …
python3 scripts/rewrite_coverage.py /tmp/spec-old.md docs/spec.md --ledger rewrite-ledger.md   # exit 0 when complete
```

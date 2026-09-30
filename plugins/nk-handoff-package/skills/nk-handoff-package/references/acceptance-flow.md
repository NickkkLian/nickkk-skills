# Acceptance flow (what happens at hand-back, in order)

| # | Step | Command / action | Evidence kept |
|---|---|---|---|
| 0 | Publish-surface hygiene on the raw package (no exclusions: a `.pyc` once carried a username) | `find <pkg> -name '__pycache__' -o -name '*.pyc' -o -name '.DS_Store'`; a byte scan for local paths | console + saved output |
| 1 | Trust root + hand-back check + drift, denominator declared by the package | `handoff_verify.py <pkg> --trust-root <file> --source <dir>` | its printed table, raw checker output |
| 2 | Remote / config reconciliation (if the executor could reach remotes): compare ref snapshots taken before and after | your own snapshot tool | before/after diff |
| 3 | Untouched-copy run: copy the deliverable, run its check *without* building first (the shipped artefacts must match the checker) | `rsync -a <pkg>/output/work/ <tmp>/ && cd <tmp> && <check>` | output file |
| 4 | Break → build → check: in a copy, break the deliverable on purpose, confirm its own check goes red, rebuild, confirm green and identical to the delivered artefacts | project-specific | three output files |
| 5 | Replay `output/pending/` by hand | — | the commits, devlog lines, memory files you created |
| 6 | Independent auditor on `output/evidence/` | the nk-evidence-audit brief | one-line verdict per claim |

Denominator rule: the table says how many steps were planned; each is PASS / FAIL / CRASH / NOT RUN. A
report that shows only passes without the denominator hides the steps that were skipped.

# Manifest format (freeze or compare several baselines at once)

`baselines.json`:
```json
[
  {"name": "report-default", "cmd": ["python3", "report.py"], "files": ["out/*.json"], "normalize": ["\\d{4}-\\d{2}-\\d{2}T[\\d:.]+"]},
  {"name": "report-empty",   "cmd": ["python3", "report.py", "--input", "fixtures/empty.csv"]},
  {"name": "cli-help",       "cmd": ["python3", "report.py", "--help"]}
]
```
- `cmd` is an argv list (no shell). `cwd` per entry is optional (defaults to `--cwd` or the current dir).
- `files` are globs relative to cwd for outputs the command writes; their sha256 is stored.
- `normalize` regexes are applied to stdout/stderr before storing and before comparing.

`python3 baseline.py run --dir .baselines --manifest baselines.json --mode freeze`
`python3 baseline.py run --dir .baselines --manifest baselines.json --mode compare`  (exit 1 if any differs)

Commit `.baselines/` with the code: the baseline is part of the change's evidence, and a baseline in a
temp directory is gone the next day.

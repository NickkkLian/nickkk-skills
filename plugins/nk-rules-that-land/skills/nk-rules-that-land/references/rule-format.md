# Rule format that rules_check.py reads

A rule is any list item or paragraph containing a directive word (must, never, always, do not, don't,
forbidden, required, prohibited, refuse), or one of the Chinese equivalents listed under "Directives in
Chinese" below. Tags are searched inside the same block (the item plus its indented continuation lines):

```markdown
- Never push while the branch is behind origin.
  Incident: 2026-07-11 a stale local build was deployed over work that only existed on the remote.
  Enforced by: hooks/guardrail.py
- Data-file edits must keep the file's indentation.
  Why: 2026-08-19 a one-line edit re-indented a 600 KB file; the diff became unreadable.
  Enforced by: python3 tools/indent_guard.py
```

`Enforced by:` accepts a path (relative to the rules file's directory or `--base`) or a command. With
`--run`, `.py/.sh/.mjs` targets are executed with the matching interpreter and must exit 0.

## Directives in Chinese

A rules file written in Chinese is read by the same script. The table is the checker's matching range — the
words `rules_check.py` also accepts as directives, beside the English term each one stands for. Nothing the
script prints is in Chinese; these words are matched, not written.

| English directive | Chinese equivalent it also matches |
|---|---|
| must | 必须 |
| must not, not allowed | 不许 |
| forbidden, prohibited | 禁止 |
| always, without exception | 一律 |
| never | 绝不 |
| may not | 不得 |

## Converting a prohibition into a step

| Prohibition | Default action that produces it | Checkable step + trigger |
|---|---|---|
| never simplify the analysis | writing compresses | end-of-procedure coverage check: every old heading accounted for |
| never `git add -A` | habit | PreToolUse hook denies and prints `git add -- <paths>` |
| never trust "tests pass" | accepting a claim | evidence bundle + independent audit before the claim is acted on |
| don't guess contact e-mails | filling a table quickly | each address has a source URL opened and quoted |

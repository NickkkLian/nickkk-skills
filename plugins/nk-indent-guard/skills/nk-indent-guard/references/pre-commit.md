# Pre-commit hook (per clone)

`.git/hooks/pre-commit`:
```bash
#!/usr/bin/env bash
# refuse commits that re-indented data files; see the nk-indent-guard skill
python3 "$HOME/.claude/skills/nk-indent-guard/scripts/indent_guard.py" || {
  echo "indent-guard: rewrite the files above with their original indentation, then commit again" >&2
  exit 1
}
```
`chmod +x .git/hooks/pre-commit`. Hooks are not versioned, so each clone runs this once. If the skill is
installed in the project instead, point at `.claude/skills/nk-indent-guard/scripts/indent_guard.py`.

To bypass for a deliberate reformat: `git commit --no-verify` — and say so in the commit message, because
the next reader will see a 400-line diff and want to know it was intentional.

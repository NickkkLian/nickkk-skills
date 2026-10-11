# Run it on every commit

Two ways. Both refuse the commit when a data file was re-indented and name the file.

## With the pre-commit framework

If the repository already uses [pre-commit](https://pre-commit.com), add this to its `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/NickkkLian/nk-indent-guard
    rev: v0.1.4
    hooks:
      - id: indent-guard
```

`rev` takes a version tag, as in the block above, or a commit id.
`git ls-remote https://github.com/NickkkLian/nk-indent-guard` lists that repository's tags and the id of its newest
commit. The hook is the script itself (`language: script` in `.pre-commit-hooks.yaml` at the repository root): it
needs `python3` (3.9 or newer) and git on the machine, and the framework installs nothing for it. It is given the
staged `.json`, `.yaml` and `.yml` files.

How far this was checked. On 2026-10-09 the manifest was read against the framework's documentation and its manifest
schema, and the script was started by a hand-written git hook the way that documentation describes for this hook
type (the file itself, from the repository root, with the staged data files as arguments). On 2026-10-10 it was run
under pre-commit 4.6.2 on macOS 15.7 (Apple silicon, git 2.39.3, Python 3.13), with the framework cloning that
repository at its 0.1.3 commit from a local copy: `git commit` passed a one-line edit, was refused for a re-indented
JSON file and again under `git commit -a` for a re-indented JSON and YAML file, and `pre-commit run --all-files`
failed while the re-indented file was there and passed once it was put back. The script and `.pre-commit-hooks.yaml`
are unchanged in 0.1.4. It was not run from the GitHub address, on Linux or on Windows, or under another pre-commit
version.

## As a plain git hook (per clone)

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

Use 0.1.3 or newer for either hook. Up to 0.1.2 the script, started from a hook, wrote its self-test's sample files
into the index of the commit in progress: `git commit -a` and `git commit <path>` stopped with "invalid object",
and the guard saw no data files. A plain `git commit` after `git add` was not affected.

To bypass for a deliberate reformat: `git commit --no-verify` — and say so in the commit message, because
the next reader will see a 400-line diff and want to know it was intentional.

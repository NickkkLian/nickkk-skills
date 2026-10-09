---
name: nk-indent-guard
description: Stop a one-line edit to a JSON or YAML data file from re-indenting the whole file and burying the real change in a 400-line diff. Use when you edit tracked data files with a script (json.dump, JSON.stringify, a YAML dumper) and before committing them; also use when a diff for a small change looks huge. Compares each file's indentation unit with the last committed version and refuses the commit until the file is written back with the original unit. Not a JSON validator.
license: MIT
metadata:
  provenance: own practice (2026-08); no external source
  version: 0.1.3
---
# Indent guard

**A rewritten data file passes every validator and destroys the diff.** Change one value, write the file
back with `json.dump(obj, f, indent=1)` on a file that used two spaces: the schema check is green, the
record count is right, the content is right — and the diff is 391 lines instead of 4. Nobody can ever
again answer "what did this commit change". Writing "keep the indent" into a memory did not stop it
happening a third time; a machine check did.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- You just edited a tracked `.json` / `.yaml` / `.yml` file through code and are about to commit.
- A diff for a small edit is suspiciously long.
- You maintain a repository where data files are the product (registries, ledgers, content libraries).

## Procedure

1. After editing, before committing:
   `python3 <skill-dir>/scripts/indent_guard.py` (whole repo) or
   `python3 <skill-dir>/scripts/indent_guard.py data/` (a subtree); `--ref` compares against
   another revision, `--ext` changes the extensions.
2. A red line names the file and the change of unit (`2 spaces → 1 space`, `4 spaces → tab`,
   `2 spaces → none` for pretty → single line). Rewrite the file with the original unit — read it first:
   `references/write-back.md` shows how to detect and preserve the unit in Python and Node.
3. New files have no baseline; they are listed, not judged. Decide their unit deliberately.
4. To make it automatic, use one of the two hooks in `references/pre-commit.md`. A repository that already uses
   the pre-commit framework adds three lines to its `.pre-commit-config.yaml`; any other repository gets a plain
   `.git/hooks/pre-commit` file (hooks live in `.git/hooks`, so every clone installs it once).

## What it does not do

- It does not validate the content; pair it with your schema check.
- It reads the first 200 lines to find the unit; a file whose first indented line is inconsistent
  with the rest is judged by that first line.
- Key order changes, trailing-newline changes and reformatting inside a line are invisible to it —
  those also inflate diffs, but they are a different guard.
- The pre-commit framework entry was checked against that framework's documentation and started by hand the way
  the documentation describes; it has not been run under the framework itself, and not on Windows.

## Provenance

Own practice, 2026-08: the same mistake three times in one month across two repositories (a devlog
rewritten with `indent=1`, a fix script with `indent=1`, a sources file two weeks later). The guard was
written after the third time. No external source.

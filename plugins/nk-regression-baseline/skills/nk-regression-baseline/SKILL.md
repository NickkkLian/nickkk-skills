---
name: nk-regression-baseline
description: Freeze the byte-exact output of production code on its default inputs before you change it, and compare after. Use when you are about to modify a function, script or pipeline that existing users or automated jobs already run, when adding a feature to code with callers you did not write, or before an A/B experiment (first confirm the baseline is alive). New-feature tests only exercise the new branch; the default path is where everyone else is. scripts/baseline.py freeze/compare with normalizers for volatile output; freeze --depends-on FILE refuses to save a baseline whose output does not change when that input file is emptied. Not a unit-test framework.
license: MIT
metadata:
  provenance: own practice (2026-08 to 2026-09); no external source
  version: 0.1.3
---
# Regression baseline

**New-feature tests prove the new code runs; they say nothing about the old behaviour.** A layer added to
a render pipeline passed all three of its acceptance checks. The regression baseline caught what they
could not: with the feature switched off — the state every existing caller was in — a planning table that
was "non-empty" for a different reason now sent seven unrelated jobs to a directory that did not exist.
No new-feature test ever contains the input "feature absent".

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- You are changing code that is already in use: a function with callers, a script a scheduler runs, a
  pipeline with consumers of its output.
- You are adding a feature behind a flag or a new parameter — the interesting case is the flag *off*.
- You are about to run an experiment (A/B, before/after tuning): the baseline arm must be alive, i.e. the
  mechanism you are studying must actually move in it, or every difference you measure is a difference
  between two ways of being dead.

## Procedure

1. **Freeze before touching anything.** Pick the commands existing users run, with their default inputs:
   `python3 <skill-dir>/scripts/baseline.py freeze --dir .baselines --name totals --files 'out/*.json' -- python3 report.py`
   Several at once: a manifest (`references/manifest.md`) and `run --manifest baselines.json --mode freeze`.
2. **Check the frozen run is alive.** `freeze` prints exit code and output size; an empty stdout and no
   files is a warning, not a baseline. Read the stored stdout once — it should look like the real thing.
   To have the tool check it, name one input file the command should be reading:
   `python3 <skill-dir>/scripts/baseline.py freeze --dir .baselines --name totals --depends-on data/prices.csv -- python3 report.py`
   The folder the command runs in is copied twice to a temporary place; the command runs in one copy as it is
   and in the other with that file emptied. Your own file is never touched. Identical output means the baseline
   would pass whatever you break in the file: `freeze` prints `refused: …`, saves nothing and exits 1. Different
   output: the command runs in your folder as usual, the baseline is saved, and a second line says which part
   of the output changed. If two runs with nothing changed already differ, it says it cannot tell, saves nothing
   and exits 2: add a normalizer first (step 3).
3. **Normalize only what is truly volatile** (timestamps, temp paths, run ids) with `--normalize REGEX`.
   Each pattern is stored with the baseline; a normalizer wide enough to hide a real change is a hole.
4. **Change the code.** Add the feature, refactor, clean up.
5. **Compare.** `baseline.py compare --dir .baselines --name totals` — exit 0 means byte-identical
   stdout, stderr, exit code and output-file hashes after normalization; exit 1 prints a unified diff and
   the changed files. Every difference is either intended (update the baseline, say why in the commit) or
   a regression.
6. **Freeze the new state** once the change is accepted, so the next change has a baseline too.

## Rules that keep it honest

- **Freeze first, then edit.** A baseline frozen after the change is a baseline of the change.
- **Default inputs, not test fixtures.** The path that matters is the one nobody wrote a test for.
- **Byte-exact, then decide.** Do not pre-filter differences you expect; look at the diff and decide.
- **Rubric before verdict.** In an experiment, write down what "better" means before running the
  post-change arm; a criterion chosen after seeing results is a story, not a measurement.
- **Aborted runs stay visible.** A run that was stopped is recorded as stopped, not re-run until it looks
  good; survivors-only results flatter every change.

## Boundaries

- It compares outputs; it does not know which differences matter. That is the review.
- Non-deterministic programs need normalizers or seeds; if the control comparison is not identical
  before you change anything, fix that first — you have no baseline yet.
- `--depends-on` shows that the output depends on the file at all. It does not show that the part of the file,
  or the code path, you are about to change is exercised.
- `--depends-on` copies the whole folder the command runs in, twice, and runs the command three times, so it suits
  a folder small enough to copy and a command quick enough to repeat. A full path on the command line is sent to
  the copy; a full path written inside a script is not, so that command reads your real file both times and is
  refused as dead. It is an option of `freeze` only, not of manifest mode.

## Provenance

Own practice, 2026-08 to 2026-09: a media pipeline regression caught only by the byte-level baseline;
two experiment rounds whose baseline arm was dead (a capped input meant the mechanism under study never
started), so eight comparisons had to be thrown away. No external source.

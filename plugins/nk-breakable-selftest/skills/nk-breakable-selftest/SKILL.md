---
name: nk-breakable-selftest
description: Make a checker, validator, linter, gate or test suite prove it can fail. Use when you write or change a self-test, when a report says "all green" or "selftest passes", or before trusting a detector's clean result. Runs a break matrix — mutate the guarded code one line at a time; the self-test must go red on the named assertion, never via a crash, and an unmutated control must stay green — and lists decorative checks that no sample covers. Not for designing the checker's own rules.
license: MIT
metadata:
  provenance: own practice (2026-08 to 2026-09); no external source
  version: 0.1.4
---
# Breakable self-test

**A self-test that cannot be made to fail proves nothing.** Break the line it guards; the self-test must go
red. If it stays green, the self-test is decoration and its green light is worse than no light: it stops
people from doubting.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- You wrote or changed a checker, validator, linter, gate, hook or test file.
- Someone (you, an agent, a CI job) reports "all checks pass", "selftest green", "0 findings".
- You are about to act on a detector's clean report over real data.

## Procedure

1. **Same code path.** The self-test must call the production function(s). A second implementation that
   "looks the same" tests itself, not the checker. If the check lives inline, extract it into a function
   and call that from both places.
2. **One sample per rule, exclusive.** Every rule gets a sample that trips *only* that rule. A sample that
   trips two rules cannot tell you when one of them dies (`references/incidents.md`, case 4).
3. **A clean control.** One sample that must produce zero findings. Without it, a checker that is always
   red passes every "does it catch X" test.
4. **Run the break matrix.**
   - Python checker with a `--selftest` (or any command that exits 0 when green):
     `python3 <skill-dir>/scripts/breakcheck.py --root <dir> --cmd "python3 checker.py --selftest" --auto checker.py`
     Every line matching `--pattern` (default: `append((`, `assert`, `raise`, `sys.exit(1)`, `return 1`) is
     neutralised one at a time in a sandbox copy. If no line matches, the run stops with exit 2 ("0 mutations …
     proves nothing"): pass a `--pattern` for this checker's style, e.g. `'print\("FAIL|findings\.append\('`,
     or write the breaks with `--spec`.
   - Any language, hand-picked breaks: write `mutations.json`
     (`{"mutations":[{"name":..,"file":..,"find":..,"replace":..,"must_mention":..}]}`) and run with `--spec`.
     `must_mention` counts only on failure lines: the first non-space character is `✘`, `✗` or `×`, or
     the first word is FAIL, FAILED, FAILURE or ERROR (any case, optionally followed by `:`).
     A name on a passing line cannot satisfy it; output with no failure lines cannot satisfy it either.
   - The script's own `--selftest` runs first and aborts everything if it fails.
5. **Read the verdicts.** `CAUGHT` is the only good one.
   `UNCOVERED` = the line is decorative or no sample exercises it → add an exclusive sample or delete the line.
   `CRASH` = your mutation broke syntax; a traceback is not a detection → pick a different break.
   `RED-ELSEWHERE` = it went red for an unrelated reason → the matrix would degrade into "always red"; fix the sample.
   `CONTROL-RED` = the command fails without any mutation → nothing else in the table means anything.
6. **Pick break points that can actually change behaviour.** Removing a `break` inside a loop that is
   guarded by another condition changes nothing and looks like "uncovered". When a break is reported
   UNCOVERED, first confirm by hand that the mutation alters an output; only then blame the self-test.
7. **Detectors fail loud, guardrails fail open.** A detector that errors must abort and print nothing that
   could be read as green. A pre-command guardrail that errors must let the command through (a broken
   guardrail that blocks everything is worse than none). Decide which one you are writing and say so in
   the header.
8. **Name what was not scanned.** Files skipped, extensions ignored, archives not opened: list them in the
   report. "All green" is read as "everything was checked".
9. **Do not mix apertures.** "Committed version matches", "working tree matches", "no drift at all" are
   three states; one number covering two of them creates the next incident.
10. **Ask the inverse question once.** The matrix asks "is deliberate breakage caught?". Also try a sample
    that satisfies the rule while doing the job badly (a lazy satisfier). If it passes, the rule measures
    the wrong thing.

## Evidence to keep

Paste the matrix table (control row included) and the exact command next to the change. A claim that the
self-test "works" without the table is the thing this skill exists to stop.

## Boundaries

- `--auto` only understands Python line structure; for shell/JS/other files use `--spec`.
- `--auto` skips docstrings (0.1.3); a pattern word inside any other string still counts as a line.
- To see a matrix before pointing it at your own code: `python3 <skill-dir>/scripts/breakcheck.py --demo`.
- Point `--auto` at the file that does the checking, not at the self-test's own assertions: neutralising an
  assertion can only make the self-test *more* lenient, so every such row reads UNCOVERED by construction.
- Neutralising a line that is part of a multi-line expression yields `CRASH`; use `--spec` for those.
- The matrix proves the self-test reacts to the breaks you listed. It says nothing about failure modes
  nobody wrote a rule for (see rule 8).

## Provenance

Own practice, 2026-08 to 2026-09: the rule came from a detector whose self-test stayed green while the
real run emitted 266 false positives, and was refined by the cases in `references/incidents.md`. The four
break-matrix criteria (red / control green / not a crash / red on the named assertion) were written after an
audit showed a matrix could be satisfied for the wrong reason. No external source was used.

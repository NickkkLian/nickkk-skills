---
name: nk-handoff-package
description: Hand a line of work to an executor that has no context — another agent, a contractor, a future session — so that the work comes back checkable. Use when delegating a whole task or a round of work to a second agent, when receiving such work back, or when a brief keeps being re-explained. Builds a self-contained package (boundary written as orders, read-only reference layer with a sealed manifest, output layer with evidence and pending-sync templates, a receipt with an "unsure" section, a generic hand-back check with three exit states, project gates as a plugin), pins a trust root outside the package, and runs an acceptance checklist with a declared denominator. Not a project-management tool.
license: MIT
metadata:
  provenance: own practice (2026-09); no external source
  version: 0.1.2
---
# Handoff package

**The hard part of delegating is not copying the files; it is moving the discipline with them, and
making the result checkable by someone who was not there.** Five delegations in a row taught the same
lesson: a brief says "don't push to the remote"; the executor, meaning well, syncs anyway; the receipt
says "all tests pass"; nobody can tell whether the checker that said so was the one you shipped.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## The shape

```
<task>/
  START.md                  boundary as orders · reading order · completeness check · what to hand back
  TASK.md                   this round only; replaced wholesale each round
  reference/                read-only inputs, sealed by MANIFEST.sha256
  output/
    handback_check.py       generic gates, one ruler for both sides (three exit states: 0 pass / 1 FAIL / 2 crashed)
                            (a copy of <skill-dir>/scripts/handback_check.py, placed by handoff_init.py)
    project_gates.py        project-specific gates, checks(pkg, out) -> (location, description, is_fail)
    RECEIPT.md              what I did · how I verified · Unsure · Boundary crossings
    evidence/               one file per claim, first line "$ <re-run command>", then raw output
    work/                   the deliverable
    pending/{commit-messages,devlog,memory,decisions}/   records in template shape; the acceptor moves them
  .templates.sha256         unfilled templates are exempt by hash, not by name
  .acceptance.txt           the package declares its own acceptance steps (the denominator)
<task>-trust-root-<date>.txt   OUTSIDE the package: sha256 of START.md, both checkers, both manifests
```

## Procedure — handing out

1. `python3 <skill-dir>/scripts/handoff_init.py <workspace> <task> [--form full|round|asset]`
   Refuses to touch a non-empty package. Then fill every `<<< FILL` slot in START.md and TASK.md.
2. Put the inputs in `reference/` and seal: `handoff_init.py <workspace> <task> --seal`.
3. Write `output/project_gates.py` for anything project-specific (thresholds, required files, forbidden
   imports). Each gate says what it cannot catch. Generic vs project-specific test: *would this still hold
   on another project?* If yes it belongs in the generic checker; if not, here.
4. Pin the trust root outside the package: `handoff_init.py <workspace> <task> --trust-root`.
   A package cannot vouch for itself: delete a file and its manifest line, edit text and re-hash, or
   replace the checker with `print("all pass")` — all three exit 0. The hashes live outside.
5. Keep your acceptance material outside too (this file, the trust root, expected answers). Ask of every
   file: does the executor need it to do the work, or do I need it to check the work?

## Procedure — receiving

1. `python3 <skill-dir>/scripts/handoff_verify.py <package> --trust-root <file> [--source DIR]`
   runs the steps the package declared: trust root first (was the checker replaced?), then the hand-back
   check on a copy (raw output kept; crash ≠ FAIL ≠ pass), then drift (was the read-only layer altered;
   with `--source`, is it stale against the true source — staleness and tampering are different questions).
   It prints `planned N / ran M / failed K`; a step that could not run is NOT RUN, never a pass.
2. Replay `output/pending/` by hand into the real systems.
3. Dispatch an independent auditor on `output/evidence/` — someone who did not do the work and did not
   write the gates. Three verdicts, no fourth.
4. Stop rule: the audit loop ends when the deliverable's blocking items are resolved, not when nothing
   more can be found. Decide the threat model first: the executor is a colleague who makes mistakes, not an
   adversary; walls against an imagined adversary have no upper bound and once made the gate machinery
   2.3× the size of the deliverable it checked.

## Rules that came from incidents

- **Boundaries are orders, not capability statements.** "You have no write access to X" is either false
  (then it is a signpost to X) or redundant. Write "do not write to X" and say why.
- **Reason = collaboration.** A remote write from the executor does not fail; it overwrites a line of
  work silently. Saying so is what stops the helpful "let me sync this".
- **Empty is not green.** A fresh, unfilled package must FAIL its own check; twelve gates that pass on
  an untouched package are twelve gates that test nothing.
- **Templates are exempt by equation, not by name.** A file is skipped only if it is byte-identical to
  the shipped template; a renamed or half-filled template is checked.
- **The receipt's "Unsure" section is the most valuable line in the package.** Empty means unfilled, not
  confident; write "none" only when it is true.
- **Per-suite floors.** If the acceptance counts red cases across suites against one total, an entire
  suite can be deleted and the total still passes.
- **Cross-review the blind spots.** When two people build packages in parallel, the first question is
  "what is self-evident on your side?" — that is where the other one's package will be wrong.

## Boundaries

- The checks read shapes (a `$` line, a filled section, a hash). A plausible fabrication passes; the
  auditor and the evidence exist for that reason.
- Without `--source`, drift only proves the executor did not alter its inputs, not that the inputs are
  current.

## Provenance

Own practice, 2026-09: five delegations of whole projects to an outside agent, two of them cross-reviewed
for eight rounds each; a trust root added after three in-package ways of turning red into green were
measured; a stop rule added after an eleven-round audit loop. No external source.

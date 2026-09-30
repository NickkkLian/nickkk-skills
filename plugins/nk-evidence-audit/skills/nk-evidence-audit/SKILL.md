---
name: nk-evidence-audit
description: Turn "done, fixed, tested" into evidence a second agent judges. Use when you are about to report a task as complete, when an agent or teammate claims something works, or before acting on a "tests pass / 0 findings / all green" report. The claimer captures raw command output with a re-runnable command (scripts/evidence.py); an auditor who did not do the work reads only the evidence and returns one of three verdicts — supported, not supported, insufficient — never a fourth. Includes the table of things that look like evidence but are not.
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09); no external source
  version: 0.1.0
---
# Evidence audit

**A claim of completion is the thing under review, not evidence for itself.** The person or agent who did
the work hands over raw output plus the command that produced it; someone who did not do the work decides
whether that output proves the sentence. Self-review confirms itself; that is why the two roles are separate.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- You are about to write "fixed", "tested", "deployed", "verified", "clean" in a report.
- An agent, a subagent or a teammate reports one of those and someone will act on it.
- A green CI run, a passing self-test or a "0 findings" scan is being taken as the final word.

## Part 1 — if you are the claimer

1. **Write the claim as one sentence** that can be false: "the login button opens the modal on mobile",
   not "UI fixed".
2. **Capture, do not transcribe.** Run the proving command through the bundler so the raw output, exit code,
   working directory, git head and hashes are saved together:
   `python3 <skill-dir>/scripts/evidence.py run --dir evidence --label login-modal --claim "login button opens the modal on mobile" -- <command>`
   Anything you would have to retype from a screen is not evidence yet. Web changes need a screenshot
   next to the bundle. Test data stays in place so the reviewer can look at it.
3. **Include the negative.** One run that shows the check can fail (an input that must be rejected, a
   deliberately broken sample). A checker nobody has watched fail proves nothing.
4. **List what you did not test**, in the report, before the verdict is asked for.
5. Hand over: the claim, the bundle directory (`evidence.py index --dir evidence` prints it), the
   screenshots, the untested list. Do not summarise the outputs in prose.

## Part 2 — if you are the auditor

Read `references/auditor-brief.md` (it doubles as a subagent prompt). The only question: **does this
evidence prove this sentence?** Three verdicts, no fourth:

| Verdict | Means | Must include |
|---|---|---|
| supported | the evidence directly proves the claim | which file, which line, supports which words of the claim |
| not supported | the evidence shows the claim false, or contradicts itself | the contradicting lines, quoted |
| insufficient | evidence missing, paraphrased, out of scope, or suspicious | what is missing and what would settle it |

Rules that keep the verdict honest:
- No evidence list from the claimer → `insufficient`. The burden is on the claimer; do not go and find it.
- "Looks fine", "probably ok", "common sense says" → `insufficient`, never `supported`.
- Output that is too clean (0 matches, all pass, one-second run for a five-second job, absurd numbers) →
  first suspect the tool that produced it; run `evidence.py verify` to see whether bundles were edited.
- Re-running a command is allowed as a check; say exactly what you re-ran.
- Audit only the sentence you were given; note anything else in one line.
- One line of verdict; expand only for `not supported` / `insufficient`: what is missing, what is
  suspicious, what would settle it.

## Part 3 — things that are not evidence

Full table in `references/not-evidence.md`. The ones met most often: a process is running ≠ it runs the
new code · exit 0 ≠ the command did the work (a search that quietly matched nothing) · `curl` works ≠ the
browser works · "push succeeded" ≠ live · same file count ≠ same content · documented ≠ current · self-check
green ≠ no holes (it only knows the failures someone wrote down) · passed on empty test data ≠ passes on
real data · an agent's "it works" ≠ its raw output · a paraphrase ≠ the output · test data deleted after
the run ≠ reviewable.

## Reporting findings (either role)

A finding carries three things or it is not finished: **where it was measured** (which files, which
scope), **how confident** (proven / supported but other causes not excluded / neither confirmed nor
refuted), and **the command that reproduces it**. "I could not prove it is wrong" is not "it is right".
Format in `references/finding-format.md`.

## Cost gate

Run the audit for claims someone will act on: shipped, fixed, migrated, cleaned, safe. Not for searches,
analyses, or reports that draw no conclusion. Every low-value audit weakens the ones that matter, and
an audit loop with no stop condition turns into building walls against an adversary who is not there —
decide up front who the auditor is protecting against (a colleague who makes mistakes, not a liar).

## Boundaries

- The bundler records what a command printed; it cannot tell whether the command was the right one.
- `verify` detects edited bundles, not staged ones — a claimer can run a different command. The auditor
  reads `command.txt` for that reason.

## Provenance

Own practice, 2026-07 to 2026-09. The role split came from a run of incidents where "tested" reports
were accepted and later found to rest on a paraphrase, an empty dataset, a hand-typed log with impossible
timestamps, or a sentinel whose alert nobody read for three days. The three-verdict rule and the
not-evidence table were written from those cases. No external source.

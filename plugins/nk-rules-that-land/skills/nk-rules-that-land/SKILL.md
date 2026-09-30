---
name: nk-rules-that-land
description: Write rules for an AI agent that actually change what it does. Use when editing CLAUDE.md, AGENTS.md, a system prompt or a team playbook, when the same mistake happens again with the rule already written down, or when a brief has grown a long list of must/never. Three tests for every rule — it names its incident, it is enforced by something that exists and runs, and it is a checkable step at the point where the default behaviour happens rather than a prohibition — plus scripts/rules_check.py to audit a rules file for rules that only exist on paper. Not a prompt-writing guide.
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09), learned partly from reading published prompt-engineering material and then rebuilt from own incidents; see Provenance
  version: 0.1.0
---
# Rules that land

**A prohibition only works at the moment someone remembers it; the mistake happens during the default
action, when nobody is remembering anything.** "Never simplify the analysis" was read at the top of every
session and violated six times in a row, because compressing is what writing does by default. It stopped
the first time the rule became a step: a coverage check at the end of the procedure that the writer had
to pass. Same for "never `git add -A`": a line in a document did nothing; a hook that denies it and prints
the replacement command did.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## Three tests for a rule

1. **It names its incident.** A rule without a dated event behind it is an imagined risk; imagined risks
   fire on normal work, and a few false alarms teach the reader to ignore all alarms. Write
   `Incident: <date> <what happened>` on the rule. If there is no incident, do not add the rule yet.
2. **It is enforced by something that exists and runs.** `Enforced by: <script or hook or checklist>`.
   A rule enforced by memory is a wish. The enforcement should live on the path the work actually takes
   (a pre-commit hook, a step in the release script, a self-test) — a gate that exists next to the path is
   the same as no gate.
3. **It is a positive, checkable step at the point where the default happens**, not a "never". Convert:
   `never X` → find the default action that produces X → add a check there that can fail → decide what
   happens when it fails (stop / ask / fix). "Never lose content when rewriting" became "after a rewrite,
   list the old headings and bold terms and account for each one".

## When the same mistake repeats

The memory was read and did not help. Do not write it down a third time; fix the procedure:
- find the step where the mistake is made (usually the default action),
- add a checkable criterion with a trigger (a checklist line, a script, a required output),
- check whether the wording of the procedure itself invites the mistake ("summarise", "table format").

## When the rules keep growing

Every correction that adds a permanent constraint shrinks the space the next attempt may use. Ten rounds
of "also never…" produced outputs that got smaller each round. Before adding a rule: retract the last
one that was about the previous attempt; if a brief carries more than a handful of must/never lines,
stop and ask what the one real objective is. `rules_check.py` flags a file with more than twelve.

## Audit a rules file

`python3 <skill-dir>/scripts/rules_check.py CLAUDE.md [--run]`
finds every directive (must / never / always / do not …) and reports:

| Finding | Meaning |
|---|---|
| NO-INCIDENT | no `Incident:` / `Why:` in the rule's block |
| NO-ENFORCEMENT | no `Enforced by:` / `gate:` / `hook:` / `check:` |
| MISSING-TARGET | the enforcement path does not exist |
| FAILED-RUN | with `--run`, the enforcement command exited non-zero |
| OVERFIT | more than twelve directives in one file |

Read the result as a to-do list: each NO-ENFORCEMENT is a rule that will be broken on a busy day.

## Writing the rule itself (form)

- One rule, one line, one reason. `Never push while behind origin. Incident: 2026-07-11 a stale build
  overwrote live work. Enforced by: hooks/guardrail.py`.
- The reason is for the reader who is about to break it, so it says what breaks.
- Put the rule where it will be seen at the moment it matters (the hook's own message, the checklist
  step), and only a pointer in the long document. One home per rule; copies drift.

## Boundaries

- The audit finds tags, not truth: a fake `Enforced by:` passes. `--run` catches enforcement that is
  broken, not enforcement that is off the path.
- Directive detection is keyword-based; a rule phrased without must/never/always is not counted.

## Provenance

Own practice, 2026-07 to 2026-09. The habit of reading published prompt-engineering advice ("write
prohibitions", "explain why") came first; the three tests above were rebuilt from what actually
changed behaviour in daily use: incident-backed rules, machine enforcement on the real path, and a
checkable step instead of a prohibition. The overfit rule came from ten rounds of shrinking outputs.
No text from external material is reproduced here.

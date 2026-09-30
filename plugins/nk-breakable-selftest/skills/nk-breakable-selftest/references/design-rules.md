# Design rules for checkers and their self-tests

## 1. Self-test and real check share one function
The failure mode is always the same: the self-test builds its own little pipeline that resembles the real
one. Then the real one is edited (a flag dropped, a regex changed) and the self-test keeps testing the copy.
Extract the check into a function; the real run and the self-test both call it. If you cannot extract it,
have the self-test run the real entry point on synthetic input (a temp directory, a temp git repo).

## 2. Exclusive samples, and a clean control
- For every rule R, a sample S_R such that check(S_R) == {R}. Not "contains R": equals.
- A clean sample C with check(C) == {}.
- Compute the assertion count; never hardcode it (a hardcoded "14 passed" survives deleted assertions).

## 3. The break matrix (four criteria, all required)
| # | Criterion | What it prevents |
|---|---|---|
| 1 | each mutation → non-zero exit | decorative checks |
| 2 | unmutated control → zero exit | an always-red detector passing the matrix |
| 3 | red is an assertion failure, not a traceback | counting a crash as a detection |
| 4 | red lands on the named assertion | an unrelated failure scoring as a catch |

Per-suite floors: if you count "how many sabotage cases went red" as one total, deleting an entire suite
can still pass. Keep a floor per suite.

## 4. Fail loud vs fail open
| You are writing a… | On internal error it must… | Why |
|---|---|---|
| detector / validator / gate | abort, exit non-zero, print no result | a silent pass is a fake green light |
| pre-command guardrail (hook) | let the command through, log nothing | a broken guardrail that blocks all work is worse than none |

Write which one it is in the file header. Mixing them is how a guardrail becomes a denial-of-service and a
detector becomes a rubber stamp.

## 5. Unscanned must be listed
Every report ends with a section naming what was not covered: skipped directories, unopened archives,
binary files, timeouts. If that section is empty, say "nothing skipped" explicitly.

## 6. One number per state
Split "aligned", "aligned only in the working tree", "drifted" into three counts. A single "0 drift" that
absorbs "committed version is 28 lines behind" is not a summary, it is a lie by rounding.

## 7. Thresholds must say what they protect
A round number chosen for comfort will be adjusted the next time someone needs to pass. Tie every threshold
to the thing it prevents ("two more index lines must still fit") and record when you changed it and whether
you were passing at the time.

## 8. Choose break points that change behaviour
Two "breaks" that a guard renders inert both look like "self-test did not react". Before concluding a
check is uncovered, confirm by hand that the mutated program produces a different output.

## 9. The inverse question (lazy satisfier)
The matrix asks whether deliberate breakage is caught. Separately construct a sample that meets the rule
while doing the job badly (satisfies the letter, not the purpose). If the rule stays green, the rule
measures a proxy. Rows where the matrix is green and the lazy sample passes are the real holes.

## 10. Positive control for searches
When a search (grep, find, a scanner) returns nothing, first run it against an input that must match.
Two kinds of "empty output" look identical: "nothing there" and "the tool did not run the way you think".

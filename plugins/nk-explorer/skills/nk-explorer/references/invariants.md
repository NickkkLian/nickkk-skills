# The five invariants

A page from this skill puts a formula where people can move it. The part that can go wrong is quiet: a slider that
moves nothing, a formula line that says one thing while the page computes another, a practice question that marks a
wrong reading right. Each of those teaches something false, and none of them looks broken.

These five hold for every page. A page that breaks one is not from this family. The **Checked by** column names the
rules that cover each: E rules read the file (`explorer_check.py`, and `make_explorer.py` before it builds), P rules
run it (`probe_check.py`).

| # | Invariant | How you can tell by looking | Checked by |
|---|---|---|---|
| 1 | **Every control is in the formula, and every move shows.** Moving a slider rewrites the formula line with the new number and marks it, moves the curve or its scale, and — somewhere along its range — changes the result. | Move each slider in turn. The number that moved is highlighted in the second line, and the chart changes. A slider that changes nothing on the screen is a fail. | E03, E04, P1 |
| 2 | **The formula shown is the formula computed.** The line with names, the line with numbers and the result are written from one parsed formula, by a small language that knows only numbers, the page's controls and a fixed list of functions — no eval (the page's policy forbids it in the browser too), no hand-typed formula text. The line with numbers writes each number of the formula as it was typed and a negative value in brackets, so it works out to the result; values and results are shown at six significant digits by one rule. | Change a value and do the sum yourself on the second line: it gives the third. Open the page with `?probe=1`: the lines at each state it records were compared with an independent Python implementation. | E08, E09, E10, P2 |
| 3 | **A question is graded on the result.** An answer passes when it is within the tolerance, however it was worked out and however it is written (plainly, with more decimals, with its unit, with thousands separators). The tolerance is smaller than the nearest other answer a slider can give, so a misread slider is marked wrong, and the prompt states every value the answer is computed with. | Type the answer three ways: all pass. Type an answer two tolerances off: it fails. Press "Show it on the controls": the sliders move to the question's values. | E06, P3 |
| 4 | **A reach question asks for something.** It fixes all but one or two controls, the page's starting values do not already pass it, some setting does, and "the fewest" or "the highest" means no setting further toward that end meets the goal, however far along. | Press Try it: the fixed sliders lock at the question's values. Set the answer: Check passes. Set one step past it, or a later setting that also meets the goal: Check names a smaller (or larger) one that also works. | E07, P4 |
| 5 | **The page says what the formula leaves out, where it comes from, and that it is not advice.** The notes and the source come from the concept; the footer says the page explains a concept and does not verify whether the formula fits anyone's case. | Read the footer. It names at least one thing the formula ignores. | E13 |

## What is not in the family

- **A calculator dressed as a lesson.** A page with one input box and one answer, and no formula on the screen,
  explains nothing. The formula line with numbers is the point.
- **A slider for decoration.** Every control is in the formula and moves the result somewhere in its range; a
  control that only looks interactive is refused.
- **Advice.** A page may explain how a loan payment depends on the rate; it does not tell anybody which loan to
  take, and it says so.

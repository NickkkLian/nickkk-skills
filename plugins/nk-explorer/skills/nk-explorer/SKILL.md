---
name: nk-explorer
description: Turn one formula into a self-contained offline HTML explorer with the person's question, a headline answer with its unit, one principal slider and a curve, expandable formula working and other settings, and practice graded on the result. Use when lessons, posts or README examples need to show how a formula behaves by changing its inputs. Build from JSON with scripts/make_explorer.py, validate with scripts/explorer_check.py, and use scripts/probe_check.py for Chrome interaction checks. One formula and sliders only; no systems of equations or table queries.
license: MIT
metadata:
  compatibility: "standard library only, no packages and no build step; the page it writes has no dependencies, evaluates its formula without eval, and carries a Content-Security-Policy intended to restrict resources to its own inline scripts and styles. The browser self-test checks an edited page with mismatched script hashes; broader policy enforcement was not separately audited. probe_check.py needs Google Chrome or Chromium; without one, the page is designed to show a manual report with ?probe=1 in a modern browser; that fallback and other browsers were not checked."
  provenance: own practice (2026-09) — the "show the query behind every click, grade on the result" idea from Query Mirror, a SQL teaching tool of mine, carried over to formulas; see Provenance
  version: 0.1.7
---
# Concept explorer

**A formula is easier to believe once you have moved it.** Read "the amount grows by (1 + r)^n" and it is a
sentence; drag the rate from 5% to 7% and watch the same ten years turn a thousand pounds into about £1,967 instead of
£1,629, and it is something you know. The page opens with the person's question, a headline answer with its unit,
one principal slider and its curve. Other settings expand inside the controls panel; the working expands below: the formula written
with names, the same formula written with the numbers you have set (the one you just moved is marked), and a legend.
Every line is written from the formula the page computes with,
so what you read is what it calculated.

The layout is designed for a 1366 × 768 CSS-pixel laptop viewport, at 100% zoom with a 16px root font and the
expandable sections closed. Above 760px the controls and curve share a row; at 760px or narrower the curve follows
the controls. Opening the answer and whole curve without scrolling is a design target. A reviewer inspected
the first screen at 1366 × 768 and recorded passing Chrome page and self-tests; see README.md for the tested
environment, counts and earlier 45/47 run. Keyboard/focus, phone-size appearance, other browsers, Windows,
Linux, source-panel interaction and appearance persistence remain unchecked.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## File locations and side effects

Put the authored `concept.json` and final `page.html` in the user's requested output folder, rather than in the
skill. Relative paths are relative to the command's working directory; the builder overwrites its `-o` file
and requires the parent folder to exist. It never edits the input or the skill.

Temporary files use Python's temporary directory (`TMPDIR` when set, otherwise the system default). For a
restricted workspace, make a scratch folder there and set an absolute path **before** launching Python:

```bash
mkdir -p scratch
export TMPDIR="$PWD/scratch"
```

| Script | Normal command leaves behind | `--selftest` side effects |
|---|---|---|
| `formula.py`, `concept.py`, `explorer_check.py` | Prints results/findings; no output files. | No persistent output files. |
| `make_explorer.py` | The requested `-o` HTML only; `--concept-of` prints JSON. | Temporary concept/HTML files under `TMPDIR`, removed on normal completion. |
| `numsrc.py check` | Prints findings; no output files. | No persistent output files. |
| `probe_check.py` | Launches Chrome; creates an `explorer-probe-…` profile under `TMPDIR`, removes it in `finally`. | Temporary pages, fake Chrome executables and browser profiles, removed on normal completion. |

If `PROBE_CACHE` names a directory, `probe_check.py` also creates it and keeps JSON reports there. Leave it unset
for an uncached check after edits. An interrupted process can leave temporary files. Chrome may have its own
platform side effects; these locations describe the scripts' writes, not a promise about everything Chrome does.
The normal file checks and builder need only Python's standard library. The browser probe and its self-test
need Chrome/Chromium and permission to launch it. In a browser-restricted environment, run the file checks,
report the browser check as unrun, and independently check extracted page logic if a JavaScript runtime is available.

## When this applies

- Someone asks how a formula behaves — interest, repayments, a probability, a physics or pricing formula — and a
  paragraph of explanation is not landing.
- A lesson, a post or a README needs an example people can move, in an HTML page designed to open locally in a modern browser without a server.
- The same "what if the rate were higher / the loan shorter / the chance smaller" question keeps being asked.

## Procedure

1. **Pick one formula.** The page explains one formula with one result — not a model, not a derivation. If the
   concept needs two formulas, it is two pages. Write it in the page's small language: numbers, the names of your
   controls, `+ - * /`, `^` for powers, parentheses, and `min max abs sqrt exp ln log10 floor ceil round`
   (`python3 <skill-dir>/scripts/formula.py "P * (1 + r/100)^n" P=1000 r=5 n=10` tries one out).
2. **Write the concept** as JSON. Start from `assets/concepts/compound-interest.json`; every field is described in
   `references/concept-format.md`. One to six controls, each a slider with a label, a unit, a range, a step and a
   starting value; the control the chart runs along; what the formula leaves out and where it comes from.
   Carry units from the request into `result.unit` and each control's `unit`; convert units in the formula when
   needed. For a requested percent, compute a value on the 0–100 scale before adding `%`. If no unit is implied,
   leave it out (a dimensionless number). If a bill's currency is unspecified, choose a symbol and say in the notes
   that the currency is illustrative. Currency results default to two decimal places; other results default to six
   significant digits. Optional `result.decimals` (0–8) sets fixed decimal places, including trailing zeros; use it
   when the request calls for a particular precision. Optional `result.unavailable` supplies a plain sentence
   explaining invalid settings in this concept and what to change. Otherwise the page explains the arithmetic error.
   Set `chart.locale` to the request's language and region for axis numbers and currency placement (for example
   `en-GB` or `de-DE`). Axes group thousands and show only decimals needed by tick spacing; headline and answer
   parsing rules stay as above. If the locale is unspecified, the axis defaults by result currency (`£`: en-GB,
   `$`: en-US, `€`: de-DE, `¥`: ja-JP; otherwise en-US); disclose an illustrative choice for ambiguous currencies.
3. **Choose ranges a person would try.** A rate from 0 to 15%, not from 0 to 100; a loan from one year to 35. The
   starting values are what the page opens on, so make them an ordinary case, not an extreme one. Write `question`
   as a short question in the person's words; it becomes the main heading. Choose `chart.x` as the one slider most
   worth trying first; it is the only slider initially exposed. Other settings expand in the same panel, beside
   the curve on wide screens. The curve uses the other starting values until they are changed. Keep the title as
   a short context label. Optional `chart.comparison` selects two distinct on-grid positions, `from` and `to`,
   whose results are finite at the opening settings. Use a relevant comparison or a requested threshold; do not
   claim an optimum or fastest change without calculating it. Otherwise the page compares the opening position
   with a position about one fifth of the slider range away. The pair stays fixed while results update with other
   settings; if a later setting makes an endpoint undefined, the comparison says so.
4. **Write the practice questions.** A *compute* question sets every control and asks for the result. Its prompt
   states every value it uses in numerals, each with its unit (`£2,000`, `3%`, `5 years`) or as `x = -2` — the
   checker pairs every value with a number of its own and refuses a 5 that the prompt gives to another control
   ("3% for 5 years" does not state a 5% rate), and a number that only says how to answer or which question this is
   stands for no value. That is judged by where the number stands, not by a list of phrasings: a label ("Task 2:",
   "Question 3 of 4:", "(Part 2)"), a bracket holding only a count ("(2 marks)", "(4 s.f.)"), or a precision ("to 2
   decimals", "to 4 s.f.", "in 2 lines", "to the nearest 10"); `references/concept-format.md` gives the exact rule. Its tolerance is smaller than the nearest other answer any one slider gives: every position
   of each slider is tried, the others at the question's values, since a curve that turns back can bring a far
   position close. A *reach*
   question fixes all but one or two controls and asks for a setting that meets a goal (at least, at most, or within
   a tolerance of a target); its prompt states the fixed values, the target and a within goal's tolerance the same
   way. Add `"lowest"` or `"highest"` when the question is "the fewest years", "the earliest time", "the highest
   rate": the answer is then the setting with no other position further toward that end that also meets the goal.
5. **Build the page**: `python3 <skill-dir>/scripts/make_explorer.py concept.json -o page.html`. It checks
   the concept first (E01-E07) and writes nothing when a rule is broken: a control the formula never uses or that
   never changes the result, a starting value between slider positions, a page that would open on an error, a
   question that leaves a control unset or never states a value it uses, a tolerance another answer would pass, a
   reach question nothing passes or that the starting values already pass, a slider position that would show more
   digits than a readout has. The page is the template with your concept in it and the design tokens written in:
   one file — its Content-Security-Policy names the page's own four scripts by their SHA-256 and is intended to
   restrict resources and execution accordingly. File checks validate the policy text and hashes; browser
   enforcement is not established by those checks. While you are still shaping the concept,
   `python3 <skill-dir>/scripts/concept.py concept.json` lists the problems without building anything.
6. **Check the file**: `python3 <skill-dir>/scripts/explorer_check.py page.html` — the concept rules again,
   read back out of the page, plus E08 the formula language is this skill's, unchanged · E09 the page opens with its
   policy, the policy is the one make_explorer.py writes and still matches the page's scripts, and the usual ways a
   page asks for something from outside are named so they can be taken out (an outside address in an attribute or a
   style, a link to any file, srcset, @import, a meta refresh, fetch and the rest; a file next to the page, such as
   src="px.png", is not named — the policy is intended to prevent loading it, but that neighbouring-file case was not browser-tested) · E10 text written as text, none of the
   usual ways of writing markup from script (innerHTML and the others it lists), and not the name eval anywhere in
   the script · E11 colours from the tokens ·
   E12 no icon characters · E13 a footer that says what is left out, where the formula comes from, and that it is
   not advice · E14 the page reads its concept and carries its probe.
7. **Run it**: `python3 <skill-dir>/scripts/probe_check.py page.html` opens the page in Chrome with
   `?probe=1`. The page moves every slider, types answers and presses its own Check buttons, and writes what it saw;
   the script recomputes what it recorded with the Python twin: P1 every move changes the formula line, marks the
   moved number and changes the curve, dot, axis labels or chart note · P2 at each state it records (the start, each control at its ends and middle,
   all at their lowest, all at their highest), every formula line, result and readout is exactly what Python writes ·
   P3 compute answers pass written three ways and half a tolerance off, and fail two tolerances off or empty · P4
   reach questions pass and fail on the same settings as Python, lock their fixed controls, and one step past a
   lowest or highest answer fails, as does the first setting further on where a curve that turns back meets the
   goal again. Axis labels, chart notes, slider end labels and verdict texts are not compared with Python. Without a runnable Chrome, try `page.html?probe=1` in the intended modern browser; the design puts its own summary
   at the foot of the page. This manual fallback and other browsers were not checked; it does not supply independent recomputation.
8. **Open it and move everything** — `references/acceptance.md` is the walk-through: what a person checks that no
   script can, such as whether the ranges make sense and whether the notes say what the formula really leaves out.

With Node available, `node <skill-dir>/scripts/chart_check.js --selftest` executes the template's formula
and chart functions against axis and scale regressions using a minimal SVG document. It reads files and prints
results only. This optional check needs no packages and does not replace Chrome or human layout inspection.

## Clickable number sources

Click the result or a control's readout and a panel shows where it comes from: for the result, the formula with the
numbers as they are set now (brought up to date after every move) and the concept's notes on what the formula leaves
out; for a readout, the slider's range. The runtime is the page's fourth script, named by its hash in the page's policy
like the other three.

The panel uses `scripts/numsrc.py`, `assets/numsrc.js` and `assets/numsrc.css`. Its intended interaction is: Tab to
a number, Enter or Space opens it, Esc closes it and puts the focus back; printed, the numbers are plain text.
These source-panel browser behaviours were not checked. The three files were compared with the shared number-source layer during integration. `python3
<skill-dir>/scripts/numsrc.py check page.html` checks a page: every marked number has an entry, every entry says
where from, how and what was not checked, and the runtime is the shipped one, byte for byte. Static checks can
warn about unused control entries because those readouts are inserted by the application at runtime.

## Rules that keep it honest

- **The formula shown is the formula computed.** The formula with names, with numbers, and the headline result are
  written from one parsed formula. Nobody types the formula text into the page, and a page whose formula language
  differs from this skill's by one character is refused (E08).
- **No eval.** The formula is parsed by a small language that knows only numbers, the page's own controls and a
  fixed list of functions. A name it does not know is an error, not a lookup, so the concept cannot reach anything
  else on the page. The page's policy is intended to disallow eval and scripts without matching hashes. The recorded Chrome self-test covers a mismatched-script-hash page; other policy cases were not separately audited.
- **The line with numbers works out.** A number in the formula is written as it was typed, and a negative value in
  brackets (`1 × (-3)^2`, not `1 × -3^2`), so doing the sum on the substituted line gives the headline at its display
  precision. Python formula unit tests and Node probe comparisons cover the shipped fixtures; an exhaustive
  JavaScript/Python parity matrix was not run for this release.
- **round, floor and ceil round what a person gets by hand.** Before they round, they finish their argument's working
  in decimal, exactly, on the numbers as the line with numbers writes them: `round(8.5 × 10.45, 2)` is 88.83 and
  `ceil(2.1 ÷ 0.3)` is 7, where rounding the computer's binary result would give 88.82 and 8. A step with no exact
  decimal result (`sqrt`, `exp`, `ln`, `log10`, a fractional power) is taken as the number the page computes for it.
- **Precision serves the quantity.** Slider and formula readouts retain the six-significant-digit formatter (whole
  numbers below 10^15 stay plain); controls must still read exactly. The headline includes its unit, with two fixed
  decimal places for currency or `result.decimals` when supplied. Fixed decimals round the computed binary value
  half away from zero; magnitudes of 10^21 or more fall back to the ordinary formatter. Grading uses the unrounded
  result; if a tolerance is tighter than the display precision, the rounded headline alone may not pass it.
  The probe compares headline and readout text against Python character for character.
- **Graded on the result.** An answer passes if it is within the tolerance, however it was worked out or written
  (plainly, with more decimals, with its unit). The tolerance itself is checked: one wide enough to pass the nearest
  other answer a slider can give — one step away for most formulas, further for a staircase like `ceil` — cannot
  tell a right reading from a misread one, and is refused.
- **It says what it leaves out.** Every page has notes on what the formula ignores and a line on where it comes
  from, and the footer says it explains a concept and is not advice.

## Boundaries

- **One formula, one result, sliders only.** No systems of equations, no step-by-step derivations, no dropdowns or
  switches. Each control is a number on a grid of at most 2,000 steps, and a page has one to six of them.
- **Formulas only, not code or queries.** A concept that is really a query over a table (GROUP BY, a join) is outside
  this version's scope.
- **The chart moves one control and holds the rest where they are.** It is a slice, not a map of everything.
  It samples 201 points. Undefined samples break the curve. When the finite range exceeds eight times its
  positive interquartile spread, the retained interval spans the quartiles minus/plus three spreads, extended to
  include zero. Samples beyond that interval are omitted from the plotted curve and scale,
  with a note giving the count and visible range. This preserves low values on bounded plateaus.
  The answer is still computed normally; a dot outside
  the range is omitted and explicitly described. This heuristic can also omit valid extreme values. It cannot find
  every discontinuity or narrow feature between samples; inspect such formulas before sharing.
- **Answers are read as plain numbers.** The result's unit, a currency sign and % are removed; commas may only
  separate groups of three digits (2,318.55), and e-notation is read because the page writes very large and very
  small results that way. A decimal comma (2318,55), a misplaced comma (23,18.55) and hex (0x90F) are not numbers
  here: the page says "Type a number."
- **It cannot tell whether the formula fits a case.** The page says where the formula comes from and what it
  leaves out; whether it applies to somebody's own loan or experiment is theirs to judge, and the footer says so.
- **The checks read the page as built, and the policy does not hold every edit.** The page's policy is intended
  to stop an outside font, image or stylesheet, an @import and eval, and scripts without matching hashes.
  File checks inspect the policy and hashes. The recorded Chrome self-test rejects an edited page with
  mismatched script hashes; broader policy enforcement was not separately audited. The policy does not cover: an edit that removes or loosens the policy line (explorer_check.py refuses that page,
  E09); content placed before the policy line, which may execute or load before the policy takes effect (E09 names such a page);
  a meta refresh (E09 names it); a script that navigates away (`location.assign`, `location =`, `window.open`), which
  explorer_check.py does not name; and a script whose hashes are rewritten after editing, so it can be permitted
  by the revised policy. These broader edited-page cases were not browser-tested.
  Text can be changed to say anything. Run explorer_check.py and probe_check.py again after any edit, or build the
  page again.
- **E10 covers the usual ways of writing markup, not all of them.** It names innerHTML, outerHTML,
  insertAdjacentHTML and the others it lists, written that way; `el["inner" + "HTML"] = …` or `setHTMLUnsafe(…)`
  added to a page with its hashes written again gets no finding.
- **The checkers' own command lines are not break-tested.** The break matrices cover the lines that report a
  finding, not the lines that print the findings and set the exit code, nor explorer_check.py's line that passes on
  concept.py's findings. Changing explorer_check.py's exit code to 0 left every self-test green; a run then prints
  its findings but exits 0.

## Provenance

Own practice, 2026-09. The two ideas at the centre come from [Query Mirror](https://github.com/NickkkLian/SQL-Viz-for-Edu),
a SQL teaching tool of mine: every click on the table becomes the SQL behind it, and practice is graded on the
result set rather than on how the query was written. This skill carries both over to formulas and none of the code.
The formula language, its Python twin, the page's self-test and the rules on questions are new here. The rule that a
tolerance must be tighter than one slider step came from asking what a tolerance is for; the rule that a prompt
states every value it uses came from the easiest mistake to make when writing one — changing a number in the data
and not in the sentence. The appearance comes from the token file shared with the other pages in this family.

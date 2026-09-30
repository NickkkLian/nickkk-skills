# Acceptance: what a person checks before the page goes anywhere

The checkers read the file and run it. These are the things they cannot see. Walk them in order with the page
open; each row says what to do and what counts as a pass. The **Rule** column names the machine rule that covers
part of the same ground, where there is one — rows with none are the ones only a person can settle.

| # | Do this | Passes when | Rule |
|---|---|---|---|
| 1 | Read the title, the question and the formula, without touching anything. | You could say what each letter in the formula stands for — the legend under the result names every one, with its unit. | — |
| 2 | Look at each slider's range. | Every range is one a person would actually try (a rate of 0 to 15%, not 0 to 100%), and the page opens on an ordinary case, not an extreme. | — |
| 3 | Read the notes in the footer. | They name what the formula really leaves out for this concept — fees, compounding more than once a year, the chance changing between tries — not a generic disclaimer. | E13 |
| 4 | Read where the formula comes from. | It is a formula a reader could look up by that name. | E13 |
| 5 | Move each slider from one end to the other. | The marked number in the second line follows the slider, the result changes, and the chart changes (for a slider that only scales the result, the axis labels change). | P1 |
| 6 | Do the sum on the second line yourself, once, with a calculator. | You get the third line, to the digits shown. | P2 |
| 7 | Move a slider to where the formula has no value, if there is one (a zero in a denominator). | The result says "no value" and gives the reason, and the chart leaves a gap rather than drawing through it. | P2 |
| 8 | Answer the compute question: wrong first, then right. | The wrong answer is marked not yet; the right one passes, and so does the same answer with its unit or more decimals. "Show it on the controls" moves the sliders to the question's values. | E06, P3 |
| 9 | Do the reach question: press Try it, move the free slider, press Check. | The fixed sliders lock at the question's values and the text under the question says which ones; the answer passes; for a "fewest" or "highest" question, one step past the answer, or any later setting that also meets the goal, is refused with the nearer one named. Unlock the controls afterwards. | E07, P4 |
| 10 | Read the practice prompts against the data. | Each prompt states the values it uses, and the question makes sense without the page open. | E06, E07 |
| 11 | Open the page with `?probe=1` on the end (or run `scripts/probe_check.py page.html`). | The summary at the foot says pass on every line. probe_check.py also compares the formula lines, results and readouts at each state the probe records, and every grading, with its Python twin. | P1–P4 |
| 12 | Turn the appearance button to dark, reload. | It comes back dark, and nothing flashes light on the way. | — |
| 13 | Narrow the window to a phone width. | Nothing overflows sideways, the panels stack, the chart's labels stay readable, and a long formula wraps. | — |
| 14 | Use the keyboard only. | Every slider moves with the arrow keys, every button can be reached with Tab and shows a focus ring, and Enter in an answer box checks it. | — |
| 15 | Open the file with the network switched off. | It renders and works. | E09 |
| 16 | Read the page's source, second line of its head. | A Content-Security-Policy with `default-src 'none'` and four `sha256-` hashes: the browser runs those four scripts (the template's three and the number-sources runtime) and loads nothing. | E09 |

Eleven of these sixteen rows name a machine rule; five (1, 2, 12, 13 and 14) have none.
Even a named rule covers only part of its row: E13 can see that the footer has notes, not that they are
honest, and P1 can see that a slider moves the formula, not that its range is one a person would try — which is
why rows 2 and 3 come before the rows the scripts can check.

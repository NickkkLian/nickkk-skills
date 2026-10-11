# Acceptance: what a person checks before the page goes anywhere

The checkers read the file and run it. These are the things they cannot see. Walk them in order with the page
open; each row says what to do and what counts as a pass. The **Rule** column names the machine rule that covers
part of the same ground, where there is one — rows with none are the ones only a person can settle.

| # | Do this | Passes when | Rule |
|---|---|---|---|
| 1 | At 1366 × 768 CSS pixels, 100% zoom and a 16px root font, load with both expandable sections closed; then open Other settings and the formula working. | Initially the answer and whole curve fit without scrolling. Controls and curve share a row. The comparison explains a useful difference without inventing curvature or an optimum. Other settings expand beside the curve; working below it names every letter with its unit. The first screen was inspected at this viewport; this does not establish fit for every authored page. | — |
| 2 | Look at each slider's range. | Every range is one a person would actually try (a rate of 0 to 15%, not 0 to 100%), and the page opens on an ordinary case, not an extreme. | — |
| 3 | Read the notes in the footer. | They name what the formula really leaves out for this concept — fees, compounding more than once a year, the chance changing between tries — not a generic disclaimer. | E13 |
| 4 | Read where the formula comes from. | It is a formula a reader could look up by that name. | E13 |
| 5 | Move each slider from one end to the other. | The marked number in the second line follows the slider, the result changes, and the chart changes (for a slider that only scales the result, the axis labels change). | P1 |
| 6 | Do the sum on the substituted formula line yourself, once, with a calculator. | You get the headline answer, rounded to its stated display precision. | P2 |
| 7 | Move a slider to where the formula is undefined or very large, if possible. | A plain sentence explains an invalid setting and what to change. Undefined or omitted samples leave gaps; the note explains omissions and an off-range dot. Ordinary values remain readable, and both axes identify units. | P2 partly |
| 8 | Answer the compute question: wrong first, then right. | The wrong answer is marked not yet; the right one passes, and so does the same answer with its unit or more decimals. "Show it on the controls" moves the sliders to the question's values. | E06, P3 |
| 9 | Do the reach question: press Try it, move the free slider, press Check. | The fixed sliders lock at the question's values and the text under the question says which ones; the answer passes; for a "fewest" or "highest" question, one step past the answer, or any later setting that also meets the goal, is refused with the nearer one named. Unlock the controls afterwards. | E07, P4 |
| 10 | Read the practice prompts against the data. | Each prompt states the values it uses, and the question makes sense without the page open. | E06, E07 |
| 11 | Open the page with `?probe=1` on the end (or run `scripts/probe_check.py page.html`). | The summary at the foot says pass on every line. probe_check.py also compares the formula lines, results and readouts at each state the probe records, and every grading, with its Python twin. | P1–P4 |
| 12 | Turn the appearance button to dark, reload. | It comes back dark, and nothing flashes light on the way. | — |
| 13 | Narrow to 390 × 844 CSS pixels, also check the 760px breakpoint. | The curve follows the controls; nothing overflows sideways, chart labels remain readable, and long formulas wrap. A phone can scroll vertically. | — |
| 14 | Use the keyboard only. | Every slider moves with the arrow keys, every button can be reached with Tab and shows a focus ring, and Enter in an answer box checks it. | — |
| 15 | Open the file with the network switched off. | It renders and works. | E09 |
| 16 | Read the policy near the start of the head, then separately test browser enforcement. | The file has `default-src 'none'` and four matching `sha256-` hashes. E09 checks the text/hashes; it does not establish browser enforcement. The recorded Chrome self-test checks an edited page with mismatched hashes; broader policy enforcement was not separately audited. | E09 |

Eleven of these sixteen rows name a machine rule; five (1, 2, 12, 13 and 14) have none.
Even a named rule covers only part of its row: E13 can see that the footer has notes, not that they are
honest, and P1 can see that a slider moves the formula, not that its range is one a person would try — which is
why rows 2 and 3 come before the rows the scripts can check.

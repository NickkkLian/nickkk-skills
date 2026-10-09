# Acceptance: what "looks like a finished product" means (16 checks)

The machine rules are in `scripts/ui_check.py` (C01–C16). They read files; they cannot prove layout, actual
drawing or runtime number sources. Every row except the external-request check still needs a browser or a person.
C16 declares and wires a form; row 16 verifies what that form really draws. `ui_check.py` C16b checks the recorded choice; shared `numsrc.py` is unchanged.
C16g catches untraced digits in caption text and caption-function literals; it cannot evaluate dynamic values.
C16h requires the independent early build guard, its static cross and completion after drawing; it cannot execute JavaScript.
The single `ui_check.py page.html` command prints UI and all shared number-source results with one exit code.
Run `render_check.py page.html` next and quote its result: built with the tick, built with the cross and why,
script error and text, or no browser found, not rendered (a blocked launch is not rendered). An earlier starter
without the build guard reports “built before this check existed, not judged” (exit 3), not a checked build. File checks alone
never justify calling a page verified. A headless tick still needs the rendered checks below.

| # | Check | How |
|---|---|---|
| 1 | First screen at 1280×800 shows: mark, product name, positioning with guard clause, `Demo` marker, exactly one primary button | screenshot; C01 |
| 2 | First screen has its chosen form and adds-up line; change the seed / scenario and the numbers change; no totals hard-coded in text nodes | C08 (the sum strip and a chip exist), C16 (form wired); change seed, compare screenshots; `rg` for literal totals |
| 3 | Every table sortable (`<th>` button + `aria-sort`), at most eight columns including Source and Actions, a filter row, row actions reachable by keyboard | C03 counts authored header columns (`colspan` included) and checks the bounded, labelled, focusable `.tablewrap` scroll contract. Runtime-created columns need browser counting. Tab to the scroll box and headers; Enter on a row opens its details. |
| 4 | Every empty state = title + reason + action | filter to empty, screenshot each |
| 5 | Every slow action shows a loading state after ≥300 ms; every fallible action has an error state (cause + fix + action, no apology) | import a bad file; go offline and click |
| 6 | Every palette holds in light and dark: no hard-coded colours outside the token block (exceptions carry a `why:` comment); a saved choice comes back on reload without a flash of the default | C02, C13; one screenshot per palette and scheme (`?theme=paper&scheme=dark` …); choose Ink, reload |
| 7 | Contrast: text ≥ 4.5:1, UI borders and focus ring ≥ 3:1, every palette in both schemes, the anchor band included | a contrast script over token pairs; axe |
| 8 | Keyboard walks the main flow; focus visible (on the anchor band too); modals trap, Esc closes and returns focus | C05 (focus never removed silently); unplug the mouse |
| 9 | 1280, 768, 390 and 320 px wide, light and dark, 40 then 150 rows: cells wrap between words before a table grows past its bounded box; every column shows initially when wrapping can fit them. Narrow tables may scroll locally, with no horizontally pinned column covering another | C03 checks the container contract; C11 checks `minmax(0,1fr)`. Browser: at scroll zero check all columns, especially Status beside Open; on a narrow screen pan to the last column and click Open. Page `scrollWidth <= clientWidth` with all rows loaded — an empty state proves nothing. |
| 10 | Motion: no `transition: all`; only transform/opacity; reduced-motion respected | C04; OS setting on |
| 11 | Honesty: no real names/logos, no invented stats, simulated actions labelled, footer block present | C06, C07, C12 (no real-looking contacts); read the footer |
| 12 | External requests: one font service and the source link only | C09 |
| 13 | Opens offline; the main flow still works | disconnect, open the file |
| 14 | URL reflects state (tab, filter, selection); refresh keeps it; a shared link opens the same view | copy the URL into a new tab |
| 15 | Meta complete: title, description, SVG favicon, one theme-color meta that follows the chosen surface, lang; README has a 1280-wide screenshot, demo link and positioning line | C10; switch the scheme and read the meta; look at the README |

| 16 | Only the declared form has marks; mark count and identity equal the rows; every plate number opens its runtime source | C16 cannot decide this. Browser: count `.sum-bar > span` (non-empty parts plus unknown hatch), `.gap-row` (nonzero rows drawn + rest row, heading excluded), `.wait-cells > i` (waiting + decided squares up to the cap; above it continuous blocks with `data-count` summing to rows), `.step` (configured steps + exits). Other forms have zero marks. Re-add the identity from all table rows, not a filtered subset. Open every `data-nk-src`; confirm matching values/row ids, Enter/Space opens, Esc restores focus. |

Not applicable items are written as "N/A + reason", never skipped.

Load-error check for row 2: throw an Error in the row generator, then in configuration; also introduce a syntax
error in that editable script. Reload each: the adds-up line shows a cross and plain “Page did not build:” with the
actual error text, never a tick. Restore the script: marks, equation and rows draw before the tick. `render_check.py`
must report each script error with its text.

Keyboard order: skip link, appearance toggle and Source, plate marks' number sources followed by new equation
numbers, filters, table scroll box, headers, table rows, details. Repeated values have one Tab stop per source id; title duplicates can
still be clicked. Numeric configuration labels and fixed dates are stated sources, not invented measurements.
Marks alone (bars/squares and bar tracks) are hidden from screen readers and not focusable; their adjacent words/counts
remain readable. Stage boxes contain text, so do not hide the whole box. Confirm names remain visible at phone width.
Capture 1280×800 and 390×844 at minimum. Confirm adds-up line is visible in the first phone screen; caption can follow it.
The current upgrade was not rendered. Touch targets remain small, and screen-reader/keyboard behavior, fonts missing,
all palettes at intermediate widths, seven long stage names and large amounts still need checks. No new motion exists.

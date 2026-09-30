# Acceptance: what "looks like a finished product" means (15 checks)

The machine rules are in `scripts/ui_check.py` (C01–C14). They are not a subset of this list and they do not
cover it: ten of the fifteen checks below name at least one C code, five (4, 5, 7, 13, 14) have no machine rule
at all, and only #12 is settled by the checker alone — every other row still needs a browser or a person.

| # | Check | How |
|---|---|---|
| 1 | First screen at 1280×800 shows: mark, product name, positioning with guard clause, `Demo` marker, exactly one primary button | screenshot; C01 |
| 2 | First screen has the reconciliation bar; change the seed / scenario and the numbers change; no totals hard-coded in text nodes | C08 (the bar and a chip exist); change seed, compare screenshots; `grep` for literal totals |
| 3 | Every table sortable (`<th>` button + `aria-sort`), a filter row, row actions reachable by keyboard | C03; Tab to a header, Enter |
| 4 | Every empty state = title + reason + action | filter to empty, screenshot each |
| 5 | Every slow action shows a loading state after ≥300 ms; every fallible action has an error state (cause + fix + action, no apology) | import a bad file; go offline and click |
| 6 | Every palette holds in light and dark: no hard-coded colours outside the token block (exceptions carry a `why:` comment); a saved choice comes back on reload without a flash of the default | C02, C13; one screenshot per palette and scheme (`?theme=paper&scheme=dark` …); choose Ink, reload |
| 7 | Contrast: text ≥ 4.5:1, UI borders and focus ring ≥ 3:1, every palette in both schemes, the anchor band included | a contrast script over token pairs; axe |
| 8 | Keyboard walks the main flow; focus visible (on the anchor band too); modals trap, Esc closes and returns focus | C05 (focus never removed silently); unplug the mouse |
| 9 | 375 px wide: no horizontal scroll with real data volume; tables scroll inside their own container | C11 (`minmax(0,1fr)`); `scrollWidth <= clientWidth` with all rows loaded — an empty state proves nothing |
| 10 | Motion: no `transition: all`; only transform/opacity; reduced-motion respected | C04; OS setting on |
| 11 | Honesty: no real names/logos, no invented stats, simulated actions labelled, footer block present | C06, C07, C12 (no real-looking contacts); read the footer |
| 12 | External requests: one font service and the source link only | C09 |
| 13 | Opens offline; the main flow still works | disconnect, open the file |
| 14 | URL reflects state (tab, filter, selection); refresh keeps it; a shared link opens the same view | copy the URL into a new tab |
| 15 | Meta complete: title, description, SVG favicon, one theme-color meta that follows the chosen surface, lang; README has a 1280-wide screenshot, demo link and positioning line | C10; switch the scheme and read the meta; look at the README |

Not applicable items are written as "N/A + reason", never skipped.

# Component specs (what each piece is, how it behaves, where it fails)

All components consume semantic tokens only; `assets/starter.html` implements every one of them. Sizes come from
the token file: top bar `--topbar-h`, table row `--row-h`, control `--control-h`, touch target `--touch-min`,
content width `--content-max`. The page is built on the anchor band (`--band`, text `--on-band`, `--on-band-2`)
for the top bar, the signature plate and the footer, and on `--bg` / `--paper` for the work area.

**Top bar** — on the band, sticky, 1px `--band-line` at the bottom, opaque (no blur). Order: mark → product name
→ one-line positioning with its guard clause → `Demo ·` pill → flexible space → light/dark toggle (a half-filled
circle drawn as line SVG, `aria-pressed`) → Source link. Only the positioning may shrink: it shows in full on wide screens, truncates with an
ellipsis as the bar narrows, and is hidden below about 720px; the name, pill, toggle and Source never shrink or
overlap, and the toggle and Source stay pinned to the right. The bar holds no page action: an accent-filled button
on the band can disappear, because in some palettes the accent is the band colour. Focus rings on the band use
`--on-band`.

**Mark** — built by rule, never drawn as a picture: a 24px rounded cell, a small seal filled with `--point` in the
top-right, one to three strokes for the product. The favicon is the same rule as an inline SVG data URI; a favicon
cannot read CSS variables, so its colours are literals of the default palette and carry a `why:` comment.

**Demo pill** — `● Demo · synthetic data · seed 42` in the top bar: an outline pill (`--band-line`), monospace
`--text-2xs`, text in `--on-band-2`, the dot in `--on-band-warning` (the dot is decoration; the word carries the
meaning). Its `title` carries the full sentence ("Synthetic data generated in this page; nothing here is a real record."),
and the long form is visually hidden on narrow bars and kept for screen readers. It is a warning, not information:
a reminder not to take the numbers as real.

**Signature plate** — the first screen, on the band: eyebrow, page title in the display face, a one-paragraph lede
that says what the page does to its rows, a short `--point` rule, then the reconciliation bar. It holds no buttons.

**Reconciliation bar** (class `sum-strip`) — `role="group"`, and the question it answers is its `aria-label` ("where did
the input rows go, and do the parts add up?"). An 8px segmented bar with 2px gaps: the first group in `--point`, the next in
`--on-band-2`, then `--on-band-3`; rows whose value is unknown are a hatched segment sized from the data and kept
out of the sums. Below it, a legend (swatch + label + monospace count) and one monospace equation line computed
from the loaded rows: `26 + 8 + 6 = 40 rows · 19,527.19 + 3,632.67 + 7,103.32 = 30,263.18`, then a check mark and
`reconciles to the cent`. The total after each `=` comes from a separate pass over every input row, in whole cents,
so a row that lands in no group, or a cent lost in a group, turns the check mark into a cross in danger colour:
`off by 4 rows and 6,232.17` when a status is left out of every group, `off by 0.01` when one cent goes astray.
Comparing rounded strings instead of integers would make the cross impossible; that is the failure to look for.

**Provenance chip** — monospace `--text-2xs`, 1px `--border`, `--neutral-tint`, key in `--text-3` and value in bold
`--text-2`: `src A:6`, `rule prefix`, `rev 1`, `seed 42`. In the table the first column shows only the source cell
(`A:6`); the labelled chips sit in the details panel, beside the equation and in the change history. On the band a
chip is an outline in `--band-line`. A clickable chip is a link with an underline; otherwise a span. The key carries
`translate="no"` so a page translator leaves `src`, `rule` and `rev` alone.

**Status tag** — 21px pill, `--text-2xs` / medium. The vocabulary is fixed: Needs review (warning) · Approved /
Booked / Sent (success) · Rejected / Failed / Unparseable (danger) · Draft (dashed border, hollow) · Simulated (info)
· Excluded / Closed / Opted out (neutral) · Blocked (danger). Colour is never the only channel: a dot for most tags,
a check mark for success, a stop sign for danger and blocked; the mark is hidden from screen readers because the
word says it. Every mark on the page — these, the sort arrows, the close cross, the theme toggle — is a line SVG
(inline, or a CSS mask), never a symbol or emoji character typed into the page (ui_check C14). Never
translated or abbreviated; never clickable (use a button).

**Category** — dotted text, not a pill: a 7px square in `--brand-sage` and the name in `--text-2`. A row with no
category shows a dashed hollow square and muted text, so "none" is visible rather than blank.

**Table** — in a scroll container (`overflow:auto`, 1px `--border`, `--radius-md`, `--paper`) so a wide table never
widens the page. Two line weights: the container border outside, `--hairline` between rows. Header row sticky on
`--surface-2`, caps `--text-2xs`. Numbers right-aligned, monospace, tabular. Sorting: a `<button>` inside each
`<th>`, `aria-sort` on the `<th>`, cycle ascending → descending → none. One filter row above (search, status select,
Clear filters) and a `showing 40 of 40` chip that is announced politely (`aria-live`) as filters change. Each row has
a ghost "Open" button for the mouse, taken out of the tab order because the row itself is focusable. Keyboard: rows are focusable, ↑ and ↓ move, Enter opens the row, Esc
closes the panel; a hint under the table says so. The selected row: `aria-selected`, `--accent-tint`, a 3px accent
bar on its first cell, and muted text stepped up to `--text-2`. Filter text, status, sort and the open row live in
the URL (`q`, `status`, `sort`, `dir`, `row`), written with `replaceState`, default values left out, so a copied link
opens the same view. Over about 2,000 rows: paginate or virtualise, and say so in the README.

**Details panel** (the inspector) — beside the table on wide screens, below it on narrow ones: title, status tag,
close. Body grouped Source (the labelled chips) / Category / Amount / Reason / History, then the actions. The one
primary button of the page lives here ("Approve row"), next to a secondary ("Reject row", or "Send back to review"
for rows already decided). Under the actions: "Decisions change this tab only; nothing is saved or sent." Focus
moves to the title on open; Esc closes and returns focus to the row. A decision is announced through a visually
hidden `aria-live` line.

**Buttons** — Primary (accent, exactly one on the page) · Secondary (paper + input border) · Ghost (transparent) ·
Danger (only for irreversible actions, paired with confirm or undo) · Disabled keeps a `title` saying why. Height
`--control-h`, `--touch-min` on coarse pointers, radius `--radius-sm`. Labels say the consequence: "Approve row",
"Export workbook", not "OK". Pressing scales by `--press-scale`; under reduced motion the press is a colour change
instead. Loading: the label becomes "Exporting…" with the width kept.

**Forms** — label above, help text below, an error replaces the help text and is linked with `aria-describedby`;
inputs sit on `--paper`, whose border reaches 3:1 where the canvas colour may not.

**Settings card** — the appearance picker. Palette: three cards, each a three-stripe swatch (`--bg`, `--band`,
`--point`) previewing its own palette through a nested `data-theme`, labelled Water lilies, Morning light and Dusk
(code values `plaster`, `paper`, `ink`). Appearance: a segmented System / Light / Dark control. The choice is saved
in `nl-theme` / `nl-scheme`; the defaults (Water lilies, System) remove the attribute instead of writing one. A
choice is saved on click as well as on change, because after a `?theme=` link the matching radio is already checked
and fires no change; choosing also removes `theme` and `scheme` from the address, or a reload would bring the link's
palette back. One `theme-color` meta follows the live `--band`.

**Review card** (for queues that need a decision per item) — header with status tag; body with Before → After as two
small columns, changed cells in warning tint; reasons list; footer with the two decisions as buttons and a keyboard
hint. Under 640px the queue becomes cards; other tables stay tables.

**Empty / loading / error states** — empty = title + reason + action ("No rows match. Clear filters"); loading
appears only after 300 ms (skeleton, no spinner for tables); error = cause + fix + action, no apology, danger colour,
on the screen where it happened.

**Chart container** — title that states the takeaway, one-line explanation, "Table ⇄ Chart" toggle, canvas, legend
when there are two or more series (direct labels when four or fewer). Single axis only; categorical colours in fixed
slot order, never cycled; a single-series categorical bar uses one colour; labels in text tokens, tabular numbers.
Hand-written SVG or canvas, no chart library from a CDN. One data point → a hero number, not a chart.

**Nav** (only when the tool has more than one section; the starter has one) — icon + label + live count (monospace,
tertiary text); selected: `--surface-2` background, a 2px accent bar, `aria-current="page"`. Collapsed: icons only,
label in `title` and `aria-label`. Links that all lead to the same place are worse than no nav.

**Footer (honesty block)** — on the band, three fixed headings: About this demo · Not verified here · Source.
`--text-xs` in `--on-band-2`, headings and links in `--on-band`. No navigation, no social icons, no "made with ♥". A
footer, not a modal, because the statement has to be visible without a click and present in every screenshot.

**Motion** — durations `--dur-fast` / `--dur-base` / `--dur-slow`; only transform and opacity move; transitions list
their properties one by one (`transition: all` is banned); table rows and queue switches get no entrance animation;
`prefers-reduced-motion` sets durations to 1ms (not 0, which never fires `transitionend`) and turns the press scale
into a colour change. The paper grain is a fixed layer under the content, never at a negative z-index (it would land
behind the body background).

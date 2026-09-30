---
name: nk-design
description: Build a single-file data tool from one sentence (a review queue, a ledger, a tracker, an admin panel) in a design system where every number shows where it came from and what was not checked. The page carries provenance chips beside derived values, a reconciliation bar on the first screen whose parts are computed live and add up, a fixed status vocabulary that never relies on colour alone, a Demo marker for synthetic data and a footer that says what is not verified. Three palettes and light/dark come from one token file, restored before first paint. Ships the token file, a working starter page and scripts/ui_check.py with fifteen machine rules. Use when asked for a dashboard, queue, ledger, tracker or internal tool, when a demo has to read as a real product in thirty seconds, or to review such a page. Not a marketing-site style and not a component library.
license: MIT
metadata:
  provenance: the author's own product-family design system (2026-09), rebuilt after four public data tools shipped with different looks and no visible sources; see Provenance
  version: 0.1.5
---
# Evidence-visible design

**A data tool is believed when its numbers can be traced, added up and questioned on the screen, not when
it is pretty.** This skill turns that into rules a page either meets or does not: every derived value has a
provenance chip next to it, the first screen opens on a reconciliation bar whose sum is computed live, the
status words are a fixed vocabulary, simulated actions say so, and the footer says what is not verified.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- Someone describes a data tool in one sentence ("an invoice review queue for a three-person bookkeeping
  firm") and wants a page that works, not a mock-up.
- Building a dashboard, workbench, admin panel, review queue, ledger, tracker, importer, "internal tool".
- A demo that has to convince a stranger in thirty seconds that it is a product and that the author knows
  what has and has not been checked.
- Reviewing such a page: run the checker first, then the browser list.
- Not for marketing sites, landing pages or general visual polish: the signature only means something where
  data is loaded, counted and decided on.

## Procedure

1. **Start from the starter page**, not from a blank file: copy `<skill-dir>/assets/starter.html` and
   `<skill-dir>/assets/design-tokens.css` into the same folder. The starter already works: seeded
   synthetic rows, a reconciliation bar computed from them, a sortable and filterable table, a row inspector,
   a theme picker and the honest footer. The page only consumes semantic tokens (`--surface`, `--anchor`,
   `--danger` …); raw values live in the token file and nowhere else.
2. **Map the sentence onto the starter's three parts**: what one row is (its fields, statuses and source),
   what the first screen has to add up (the reconciliation bar's segments and total), and what a person
   decides for a row (the inspector's actions). Replace the data generator and the labels; keep the structure.
3. **Keep the seven invariants** (`references/invariants.md`): top bar on the anchor band, mark built by
   rule, the signature plate with the reconciliation bar, a provenance chip beside every derived value, the
   status vocabulary, the honesty block, one token file with the appearance contract.
4. **Spend boldness in one place.** The deep anchor colour carries the top bar, the signature plate, the
   footer and the one primary button; one point colour stays on a small share of the page; everything else
   converges: one display face for titles, one sans for the interface, one monospace face for numbers and
   identifiers, small radii, borders before shadows.
5. **Use the status vocabulary as given** (`references/components.md` §tag): Needs review · Approved / Booked
   / Sent · Rejected / Failed · Draft · Simulated · Excluded · Blocked. A second channel beside the word — a dot,
   a check mark or a stop sign, drawn as line SVG and never typed as a symbol or emoji — never colour alone.
6. **Be honest by construction** (`references/honesty.md`): synthetic data looks synthetic and is labelled
   `Demo ·`; every number on the page is computed from the loaded data; nothing simulated shows as sent;
   the footer carries About this demo / Not verified here / Source.
7. **Keep the appearance contract.** A small script in `<head>`, before the first stylesheet, reads the saved
   palette and scheme (or `?theme=` / `?scheme=` in the URL) and sets `data-theme` / `data-scheme` before the
   first paint. The defaults write no attribute, so the page as served has neither. The picker lives in a
   Settings card; one `theme-color` meta follows the chosen surface.
8. **Check before you show it**: `python3 <skill-dir>/scripts/ui_check.py index.html` runs fifteen
   rules (one primary button, no hard-coded colours outside the token block, sortable tables, no
   `transition: all` and a reduced-motion block, focus never removed silently, honesty words, demo marker,
   chip and reconciliation bar present, only font and GitHub hosts, meta tags, `minmax(0,1fr)`, no
   real-looking contacts, the appearance contract, icons drawn as SVG rather than typed as characters, every marked number opening its source). Then the browser list in `references/acceptance.md`
   (first screen at 1280×800, 375 px wide with real data volume, keyboard path, every palette in light and
   dark, contrast).
9. **Ship with the page**: a 1280-wide screenshot in the README, the demo link, the one-line positioning
   sentence with its guard clause ("… — every row stays traceable").

## Clickable number sources

In the starter, every number in the reconciliation bar can be clicked: a panel shows the rows it counts or sums, how it
was computed and what was not checked. The words of each entry live in the page's `nk-sources` manifest; `traceStrip()`
brings the value and the rows up to date after every decision. When you replace the data generator, keep each number's
`data-nk-src` and rewrite its entry; a chip that shows a derived value can carry one too. C15 refuses a page without the
layer or with an entry that does not say where from, how and what was not checked.

The panel is the shared number-sources layer that nk-design, nk-data-story, nk-deck, nk-model and nk-explorer all
use, the same three files in each (`scripts/numsrc.py`, `assets/numsrc.js`, `assets/numsrc.css`): Tab to a number, Enter
or Space opens it, Esc closes it and puts the focus back; printed, the numbers are plain text. `python3
<skill-dir>/scripts/numsrc.py check page.html` checks a page: every marked number has an entry, every entry says
where from, how and what was not checked, and the runtime is the shipped one, byte for byte.

## Boundaries

- The checker reads the file; it cannot see layout, contrast on a rendered page, or a screenshot.
  `references/acceptance.md` lists the checks that need a browser and how to do them.
- The token file is a starting palette: change the brand names, and if you change colours keep the contrast
  pairs (every text colour in the file was solved against the hardest surface of its theme).
- No external component library and no CDN scripts. Web fonts are the only optional external request: the
  page must open offline with system fonts in their place and nothing else changed.
- The starter ships synthetic data only. Loading real records is the user's decision, and it changes what
  the footer has to say.

## Provenance

The author's own product-family design system, 2026-09. The first version was written after four public
data tools each shipped with a different look and none of them showed where their numbers came from; the
seven invariants, the signature elements and the honesty constraints were written for what a stranger
checks in the first thirty seconds. The current version kept those rules and fixed what screenshots
measured in the first: almost no dark mass (1.28% of the rendered light-theme pixels below L* 40) and no
real colour (95th-percentile chroma 0.090), so it added a deep anchor surface and one point colour, and a
palette and light/dark choice that survives a reload. No external design system was copied; where a public
method informed a decision (an accent-in-one-place rule, named easing curves), the reference file says so.

---
name: nk-design
description: Build a one-page data tool from one sentence, with every number traceable to its rows. The first screen uses one of four forms chosen from the shape of the data (parts of a whole, two sources compared, things waiting, things moving through steps), each ending in a sum computed live that adds up. Provenance chips, a fixed status vocabulary with a second channel, a Demo marker and an honesty footer carry the tracing promise. Ships tokens for three palettes in light/dark, a working offline starter and sixteen machine rules. Use when asked for a dashboard, queue, ledger, tracker or internal tool, or to review such a page. Not for marketing sites or component libraries.
license: MIT
metadata:
  provenance: the author's own product-family design system (2026-09), rebuilt after four public data tools shipped with different looks and no visible sources; see Provenance
  version: 0.2.0
---
# Evidence-visible design

**A data tool is believed when its numbers can be traced, added up and questioned on the screen, not when
it is pretty.** This skill turns that into rules a page either meets or does not: every derived value has a
provenance chip next to it, the first screen takes one of four forms ending in a sum computed live, the
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

Digits written into headings and sentences are checked like every other number: compute and trace them, or use words.

1. **Start from the starter page**, not from a blank file: copy `<skill-dir>/assets/starter.html` and
   `<skill-dir>/assets/design-tokens.css` into the same folder. The starter already works: seeded
   synthetic rows, four first-screen forms computed from them, a sortable and filterable table, a row inspector,
   a theme picker and the honest footer. The page only consumes semantic tokens (`--surface`, `--anchor`,
   `--danger` …); raw values live in the token file and nowhere else.
2. **Say what one row is, then choose the first screen’s form.** Write one line: ‘One row is a … ; it carries … .’ Answer the four questions in `references/forms.md` in order and stop at the first yes: two records compared row by row → `gaps`; three or more stages in order → `steps`; rows waiting for someone’s decision → `waiting`; otherwise `split`. Set `data-form` on the plate, fill that form’s SHAPE block, replace the data generator and the labels, and write the `form` entry in the manifest. The four drawings are in the starter: do not write a fifth, and do not bend one form to draw another’s data. Then decide what a person does to a row (the details panel’s actions). Read only your form’s section of `forms.md` after the choosing rule. Run `python3 <skill-dir>/scripts/ui_check.py --wire-form index.html` to fill its fixed live source ids; leave the shared runtime unchanged. Never build two forms to compare.
3. **Keep the seven invariants** (`references/invariants.md`): top bar on the anchor band, mark built by
   rule, the signature plate: one of the four forms, always ending in the adds-up line, a provenance chip beside every derived value, the
   status vocabulary, the honesty block, one token file with the appearance contract.
4. **Spend boldness in one place.** The deep anchor colour carries the top bar, the signature plate, the
   footer and the one primary button; one point colour stays on a small share of the page; everything else
   converges: one display face for titles, one sans for the interface, one monospace face for numbers and
   identifiers, small radii, borders before shadows.
5. **Use the status vocabulary as given** (`references/components.md` §tag): Needs review · Approved / Booked
   / Sent · Rejected / Failed · Draft · Simulated · Excluded · Blocked. A second channel beside the word — a dot,
   a check mark or a stop sign, drawn as line SVG and never typed as a symbol or emoji — never colour alone.
6. **Be honest by construction** (`references/honesty.md`): synthetic data is invented (believable
   made-up names, never a real customer or company) and the page is labelled `Demo ·`; every number on the page is computed from the loaded data; nothing simulated shows as sent;
   the footer carries About this demo / Not verified here / Source.
7. **Keep the appearance contract.** A small script in `<head>`, before the first stylesheet, reads the saved
   palette and scheme (or `?theme=` / `?scheme=` in the URL) and sets `data-theme` / `data-scheme` before the
   first paint. The defaults write no attribute, so the page as served has neither. The picker lives in a
   Settings card; one `theme-color` meta follows the chosen surface.
8. **Check before you show it**: `python3 <skill-dir>/scripts/ui_check.py index.html` runs all sixteen UI
   rules (one primary button, no hard-coded colours outside the token block, sortable tables, no
   `transition: all` and a reduced-motion block, focus never removed silently, honesty words, demo marker,
   chip and first-screen sum strip present, only font and GitHub hosts, meta tags, `minmax(0,1fr)`, no
   real-looking contacts, the appearance contract, icons drawn as SVG rather than typed as characters, every marked number opening its source, the form declared and wired (C16)) **and all shared `numsrc.py` checks**. Both results print; one non-zero exit refuses either checker's errors. Keep the starter's independent `nk-build-guard` first in the head, its static cross in `sum-eq`, and `nkBuild.complete()` after the drawing calls. A load error must show “Page did not build:” and the error in that line; a tick waits for drawings and sums to finish.
   **Render next:** `python3 <skill-dir>/scripts/render_check.py index.html` uses installed Chrome/Chromium offline with a temporary, empty profile (never your saved profile), then reads the rendered DOM. It prints **built with the tick**, **built with the cross: [why]**, **script error: [text]**, or **no browser found, not rendered**. A blocked or failed browser start prints **not rendered: [reason]**. If it answers **not rendered**, report exactly that; do not start a browser with its own protections switched off to look at the page. A page from an earlier starter without the build guard reports **built before this check existed, not judged** (exit 3); rebuild from the current starter before claiming a checked build. Repair any cross or script error and repeat both commands. File checks alone never establish rendering. Then the browser list in `references/acceptance.md`
   (first screen at 1280×800, 375 px wide with real data volume, keyboard path, every palette in light and
   dark, contrast).
9. **Ship with the page**: a 1280-wide screenshot in the README, the demo link, the one-line positioning
   sentence with its guard clause ("… — every row stays traceable"). In the final report quote the render command's result in the words above, including any error/reason. If no browser ran, say **not rendered**; never call that page **verified** or claim a screenshot. A tick confirms the build and sums ran; layout, sources and interaction still need the browser list.

## Clickable number sources

In the starter, every number in the plate can be clicked: a panel shows the rows it counts or sums, how it
was computed and what was not checked. The words of each entry live in the page's `nk-sources` manifest; the form’s `trace()`
brings the value and the rows up to date after every decision. When you replace the data generator, keep each number's
`data-nk-src` and rewrite its entry; a chip that shows a derived value can carry one too. C15 refuses a page without the
layer or with an entry that does not say where from, how and what was not checked.

The panel is the shared number-sources layer that nk-design, nk-data-story, nk-deck, nk-model and nk-explorer all
use, the same three files in each (`scripts/numsrc.py`, `assets/numsrc.js`, `assets/numsrc.css`): Tab to a number, Enter
or Space opens it, Esc closes it and puts the focus back; printed, the numbers are plain text. `python3
<skill-dir>/scripts/numsrc.py check page.html` checks a page: every marked number has an entry, every entry says
where from, how and what was not checked, and the runtime is the shipped one, byte for byte.

## Boundaries

- The combined file checker reads the file; C16 cannot see whether the declared form is actually drawn. The render command distinguishes a finished tick, a cross, script errors and no rendering; it does not check layout or interactions. Acceptance row 16 counts rendered marks, re-adds the identity and checks every runtime source id.
  `references/acceptance.md` lists the checks that need a browser and how to do them.
- The token file is a starting palette: change the brand names, and if you change colours keep the contrast
  pairs (every text colour in the file was solved against the hardest surface of its theme).
- No external component library and no CDN scripts. Web fonts are the only optional external request: the
  page must open offline with system fonts in their place and nothing else changed.
- The starter ships synthetic data only. Loading real records is the user's decision, and it changes what
  the footer has to say.
- At phone width the starter's table scrolls sideways inside its own box. At 375 px the first two columns show,
  the third is cut, and the amount, the status and the Open button need a swipe; the page itself does not scroll
  sideways.
- On phones: split’s legend wraps; gaps puts names and signed numbers over full-width bars; waiting has one band per line with decided groups under a rule; steps stacks its boxes with downward chevrons. A merged waiting block pans inside its group while the page stays within the viewport. No browser check was run for this upgrade: keyboard order, screen readers, touch, widths and full volume require acceptance checks.
- The clickable numbers are small touch targets. A click lands on a box about 25 px wide and 21 px tall around a
  single digit, below the 44 px usually asked of a touch target. They were clicked by script in headless Chrome;
  nobody has tried them with a finger.

## Provenance

The author's own product-family design system, 2026-09. The first version was written after four public
data tools each shipped with a different look and none of them showed where their numbers came from; the
seven invariants, the signature elements and the honesty constraints were written for what a stranger
checks in the first thirty seconds. The current version kept those rules and fixed what screenshots
measured in the first: almost no dark mass (1.28% of the rendered light-theme pixels below L* 40) and no
real colour (95th-percentile chroma 0.090), so it added a deep anchor surface and one point colour, and a
palette and light/dark choice that survives a reload. No external design system was copied; where a public
method informed a decision (an accent-in-one-place rule, named easing curves), the reference file says so.

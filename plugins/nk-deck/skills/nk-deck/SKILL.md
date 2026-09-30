---
name: nk-deck
description: "Turn one sentence — a topic and who it is for — into a ten-slide single-file HTML deck whose titles carry the argument on their own, five points at most per slide, a source under every number, and a printout that is the same deck page for page. Use when a decision, a proposal or a status needs to be read in two minutes or printed, when a slide deck has to work offline and from the keyboard, or when a PowerPoint would be more ceremony than the content deserves. scripts/make_deck.py writes the file from a JSON outline, scripts/deck_check.py checks twelve rules on it (labels for titles, a sixth point, a number with no source, a print layout that leaks, a source that cannot be opened), and scripts/print_check.py prints it in Chrome and counts the pages. Not a design tool: one layout, one token file, no images."
license: MIT
compatibility: the deck and make_deck.py / deck_check.py are standard library only; print_check.py needs Google Chrome or Chromium to print.
metadata:
  provenance: own practice (2026-09) — two portfolio decks that had to print cleanly, and a design system built for pages that say where their numbers come from; see Provenance
  version: 0.1.3
---
# Deck: ten slides, titles that argue

**A deck is read in a hurry.** Somebody flicks through it before the meeting, or prints it and reads the
titles only. So in this deck the titles carry the argument, the points carry the evidence, and the printout is
the deck — ten slides, ten pages, nothing cut off.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- A decision, a proposal or a status update has to be read in two minutes, or printed and read later.
- A deck must open offline and work from the keyboard — a link that opens at slide 7, arrow keys, P to print.
- The content is an argument, not a brand showcase: no photos, no icon per bullet, no "thank you" slide.

## Procedure

1. **Write the argument before the slides.** From the one sentence, write the ten titles as one paragraph —
   each title a sentence that states a conclusion, in the order the reader needs them. Read the paragraph back.
   If it does not make the case on its own, the deck will not either. The last title is the decision or the ask.
2. **Fill in the outline**: `python3 <skill-dir>/scripts/make_deck.py --init deck.json` gives the
   example; replace every slide. Each slide has a `title`, and either a `sub` (one sentence) or up to five
   `points`. A point that measures something — digits, or words like "four of the last six", "doubled", "two
   thirds" — carries a `source`; dates, times and years do not count, and a small count that only describes
   reads best in words ("two people"). If the numbers are made up for a draft, set `"illustrative": true`: the
   cover then says so, and any source you give one starts with "illustrative —".
3. **Write the file**: `python3 <skill-dir>/scripts/make_deck.py deck.json --out deck.html`. It
   refuses an outline that breaks the rules below, rather than writing a deck that fails in the meeting.
4. **Check it**: `python3 <skill-dir>/scripts/deck_check.py deck.html --single` (D01 the outline is read,
   not hard-coded · D02 three to twenty slides · D03 titles are conclusions, not labels · D04 five points, each
   under 140 characters · D05 a source under every measurement · D06 print CSS that keeps one slide per page,
   changes nothing on a slide, and leaves the phone layout on screens · D07 arrows, space, Home/End, P, and #n · D08 nothing fetched ·
   D09 colours from tokens · D10 one file · D11 no thank-you slide · D12 every sourced point opens its source).
5. **Print it**: `python3 <skill-dir>/scripts/print_check.py deck.html` prints it in Chrome and checks
   the PDF has one page per slide and no slide is too full. Open `deck.html?check=1` to see the same
   measurement in the page; it measures the 1280×720 slide at any window width. Inside an agent's sandbox Chrome's own sandbox often cannot start; the script then
   prints once more with `--no-sandbox` and says so in a `note:` line. If it still cannot print, report that —
   do not describe the printout as checked.
6. **Read the titles alone**, top to bottom, out loud. Then open it offline and walk it with the keyboard.

## Clickable number sources

In a point that names a source, click a number (or the source note, when the point has no digits) and a panel shows
the source as the outline states it, marked as stated: nobody opened the source or compared the number with it. The
manifest is written by make_deck.py from the outline; D12 refuses a deck whose sourced points cannot open.

The panel is the shared number-sources layer that nk-design, nk-data-story, nk-deck, nk-model and nk-explorer all
use, the same three files in each (`scripts/numsrc.py`, `assets/numsrc.js`, `assets/numsrc.css`): Tab to a number, Enter
or Space opens it, Esc closes it and puts the focus back; printed, the numbers are plain text. `python3
<skill-dir>/scripts/numsrc.py check page.html` checks a page: every marked number has an entry, every entry says
where from, how and what was not checked, and the runtime is the shipped one, byte for byte.

## Rules that keep it honest

- **A title is a sentence that could be wrong.** "Results" cannot be wrong, so it says nothing.
  "Custom orders lost money every December" can be — and that is what makes it worth a slide.
- **Five points, one idea each.** A sixth point is a second slide; a point that needs two lines is two points.
- **Every measurement names its source**, in the small note under it. Illustrative numbers are allowed in a
  draft: the deck says so on its cover, and a source it gives one says "illustrative" too. They are never
  presented as findings.
- **The last slide is the decision or the ask**, with what happens if nobody decides.

## Boundaries

- **The checker judges shape, not truth.** It catches labels, overlong points and unsourced numbers; it cannot
  tell whether a title is correct or whether the argument holds. That is the person's read in step 6.
- **One layout.** 1280×720, one token file, no images. If the content needs a chart, the chart is a separate
  artefact linked from a point.
- **The title and number rules read English, and they are heuristics.** D03 knows English label words and
  wants three words or more ("Churn doubled" is refused; "Churn doubled in March" is not). A Chinese or Japanese
  title is only measured — four characters or more — and its label words are not recognised. D05 reads digits
  in any language but number words only in English; it knows English and Chinese dates and times, and the
  Chinese word for "illustrative" (the forms are listed in `references/invariants.md`). It takes a threshold ("below half of last December") or "one of the
  two ovens" for a measurement: give those a source, or rephrase. `references/invariants.md` lists what else
  they get wrong. The template's own words — the "source:" label, the cover notice, the key hint — are English.
- **Which numbers D05 takes for dates.** Only where a number cannot also be a count: a day before a month
  ("1 November"), a month then a day with an ordinal, a year or nothing after it ("November 1st", "on November
  1."), "the 15th", a year after since, until, during and the like, or one that closes the phrase ("in 2025,"),
  a quarter or a financial year ("Q3", "FY24"), and times ("7am", "10:30"). Every other digit asks for a source —
  "In March 12 customers cancelled", "A backlog of 2000 orders", "In 2025 we opened a second shop".
- **What a print rule may change.** Inside `@media print`, D06 allows page breaks, what shows, colours, and — on
  the template's own frame (html, body, .viewport, .stage, .slide, the key hint) — the box that makes one slide
  one page. Anything else is refused, even a change that would print fine: print_check measures the slides as
  they are on screen, so the print must not differ from them.
- **Printing needs Chrome** for print_check.py. The deck itself prints from any browser with P.

## Provenance

Own practice, 2026-09. The layout, the keyboard handling and the print rules come from portfolio decks of my
own that had to print as PDFs. Rule D06 and print_check.py cover the two ways a printout stops being the deck:
a phone layout that reaches the print — in this template it keeps the page count and prints phone type and
phone margins, so only a rule on the file sees it — and a slide that is allowed to grow, which pushes the rest
onto extra pages and shows up in the page count. None of those decks' content is in this skill; the example
deck is invented, and says so on its cover.

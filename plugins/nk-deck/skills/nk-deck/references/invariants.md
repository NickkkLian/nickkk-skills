# The five invariants

A deck is read in a hurry: somebody flicks through it before a meeting, or prints it and reads the titles
only. So the titles carry the argument, the points carry the evidence, and the printout is the same deck as the
screen. These five hold for every deck this skill writes; a deck that breaks one is not from this family.

| # | Invariant | How you can tell by looking |
|---|---|---|
| 1 | **Every title states its conclusion.** A reader who reads only the titles, in order, gets the argument. "Results" is a label; "Custom orders lost money every December" is a conclusion. | Read the titles alone, top to bottom, as one paragraph. It should make sense and say something. |
| 2 | **Five points at most, one idea each.** A sixth point is a second slide. | Count the bullets on the busiest slide. |
| 3 | **Every number says where it came from**, in a small note under the point — or the deck says on its first slide that its numbers are illustrative, and then any source it gives one says so too. | Pick any number; the note beside it names a source, or the cover says "illustrative" and the note, if there is one, starts with it. |
| 4 | **The printout is the deck.** One slide, one page, nothing cut off, nothing from the phone layout leaking into the print, and the type the size it is on screen. | Print to PDF: the page count equals the slide count, the last line of the fullest slide is on its page, and a title on paper is as big as on screen. |
| 5 | **It works without a mouse, and without a network.** Arrow keys, space, Home/End and P; a link to slide 7 opens slide 7; nothing is fetched when it opens. | Open the file offline and walk it with the keyboard; open it with #7 on the end. |

## What is not in the family

- **Decoration standing in for an argument.** No stock photos, no icons beside every bullet, no "Thank you!"
  slide. The last slide is the ask or the decision.
- **Invented numbers presented as findings.** A sample deck may use illustrative numbers, but it says so where
  a reader will see it — on the cover, and in any source it gives them — and a real deck's numbers carry their
  source.

## What the checks get wrong

D03 and D05 read text with patterns, in English. Measured on 2026-09-22 with phrasings chosen to find the edges
(so these are examples, not error rates):

- **Labels that pass D03**: a label with one word outside its list — "Revenue overview for the quarter" is caught,
  "Tuesdays: the data" and "Why we should close on Tuesdays" are not. A question is not a conclusion either. Verbs
  are not label words, so "Results are in" passes; "The roadmap is at risk" passes because it argues.
- **Arguments D03 refuses**: two-word titles ("Churn doubled", "We won"). Add what, where or when.
- **Chinese and Japanese titles** are measured in characters (four at least); their label words are not known.
  The Chinese forms D05 reads, and one it does not:

  | In English | Chinese form | Read as |
  |---|---|---|
  | a date, "from 1 October" | 10 月 1 日起 | a date — needs no source |
  | a time, "half past three in the afternoon" | 下午 3 点半 | a time — needs no source |
  | a quarter, "Q3" | 第 3 季度 | a period — needs no source |
  | "illustrative", in a source or on the page | 示意 | the same as the English word |
  | a ratio in digits, "4 of the last 6 Tuesdays" | 最近 6 个周二有 4 个 | a measurement — needs a source |
  | a ratio in number words, "four of six Tuesdays" | 六个周二里有四个 | **not read** — check these by hand |
- **Measurements D05 misses**: number words in other languages, and phrasings outside its list ("a handful of",
  "most of").
- **Descriptions D05 flags**: a small count in digits ("2 people"), "one of the two ovens", a threshold ("below
  half of last December"). Write the count in words, rephrase, or give the threshold a source.
- **Dates, times and years it does not ask a source for**: "on 1 November", "on November 1.", "the 15th", "since
  2019", "in 2025," (a year that closes the phrase), "7am", "Q3" and "Q3 2025". A number that could also be a count
  stays a number and asks for one: "In March 12 customers cancelled", "In December 40% of orders…", "A backlog of
  2000 orders", "In Q3 40% of orders were late". So does a year at the start ("2019 was our best year") or one
  followed by more words ("In 2025 we opened a second shop" — write "In 2025, we opened…", or give a source).
- **Print rules D06 allows**: page breaks, what shows, colours, and on the template's slide frame only the box that
  makes one slide one page. Anything else inside `@media print` — a font, a margin, a gap, a scale — is refused,
  including changes that would be harmless: print_check measures the screen layout, so D06 keeps the two the same.
- **What counts as the notice**: words in the page's markup, or a string its script puts on the screen. A comment,
  an attribute, a class name or a variable called "illustrative" does not.

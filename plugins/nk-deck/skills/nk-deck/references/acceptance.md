# Acceptance: what a person checks before the deck goes anywhere

The checkers read the file and print it. These are the things only a person can settle, plus the ones a person
should see with their own eyes once. **Rule** names the machine rule that covers part of the same ground.

| # | Do this | Passes when | Rule |
|---|---|---|---|
| 1 | Read the ten titles alone, in order, out loud. | They make the case as one paragraph, and the last one is the decision or the ask. | D03, D11 |
| 2 | For each title, ask whether it could be wrong. | Every title could be — none is a label or a truism. | D03 |
| 3 | Look at the busiest slide. | Five points or fewer, each one idea, none needing a second line to make sense. | D04 |
| 4 | Pick three numbers at random. | Each has a source under it, or the cover says the deck is illustrative and any source under it says so too. | D05 |
| 5 | Check each source actually says the number. | Open the source; the number is there. | — |
| 6 | Walk it with the keyboard only: →, ←, space, Home, End. | Every key does what it says, and the slide counter follows. | D07 |
| 7 | Open it with `#7` on the end. | It opens on slide 7. | D07 |
| 8 | Run `print_check.py`. | One printed page per slide, no slide reported too full. | D06 |
| 9 | Open the PDF and look at the fullest slide. | Its last line is on its page and nothing overlaps the footer. | D06 |
| 10 | Open it on a phone, or narrow the window below 900 px. | The slides become a column of cards that reads top to bottom. | D06 |
| 11 | Open the file with the network switched off. | It renders and works. | D08, D10 |
| 12 | Read the cover and the last slide as a pair. | The cover says what is being decided; the last slide decides it. | — |

Ten of these twelve name a machine rule; two (5 and 12) have none, and row 5 is the one that makes the deck
honest rather than tidy: a checker can see that a source is there, not that it says what the point says.

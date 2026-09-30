# Acceptance: what a person checks before the page goes anywhere

The checker reads the file. These are the things it cannot see. Walk them in order with the page open; each
row says what to do and what counts as a pass. The **Rule** column names the machine rule that covers part of
the same ground, where there is one — rows with none are the ones only a person can settle.

| # | Do this | Passes when | Rule |
|---|---|---|---|
| 1 | Read the page without booking anything. | You could tell a friend what the place does, what it costs and when it is open, from memory. | — |
| 2 | Look at the price ranges. | Each one has a sentence about what moves it within the range. "Contact us" is a fail. | — |
| 3 | Read the four questions. | At least one has an answer the business would rather not give (no, we don't; not on Mondays; only if you bring it in). | — |
| 4 | Book a slot. | The status says it is waiting for a person and nothing appears in the outbox. | L05 |
| 5 | Approve it at the desk. | Two outbox rows appear — the message and the calendar write — each saying "not sent", each naming the request and the revision. | L02 |
| 6 | Press "Replay the last approval". | It is refused, and the refusal says the approval was already used. | L06 |
| 7 | Press "Approve from the customer side". | It is refused, and the refusal says approvals come from the desk. | L06, L07 |
| 8 | Press "Change the draft after approval". | It is refused, and the refusal says the draft is not the text that was approved. | L06 |
| 9 | Pick a different slot, press "Change my slot", then replay the approval. | The request comes back as a new revision, and the old approval is refused for being for the previous one. | L06 |
| 9b | Open the page with `?probe=1` on the end (or run `scripts/probe_check.py page.html`). | The table at the bottom says every case behaved as promised: the two approved actions went out, and the same message twice, other words, another slot, a reminder, a customer-side approval, a built-in object dressed as an approval, an approval the desk did not issue, another request's approval and a changed phone number were each refused. | L06 |
| 10 | Turn the appearance picker to Dark, reload. | It comes back dark, and nothing flashes light on the way. | — |
| 11 | Narrow the window to a phone width. | Nothing overflows sideways, the slot pills wrap, and the desk sits under the form rather than beside it. | — |
| 12 | Tab through the page with the keyboard only. | Every field, slot and button can be reached, and the focus ring is visible on each. | L08 |
| 13 | Read the footer. | It says the business and its numbers are made up, and it does not claim customers the page has not had. | L03, L12 |
| 14 | Search the file for the phone number. | It is in the 555-01xx range, and there is no e-mail outside an example domain. | L04 |
| 15 | Open the file with the network switched off. | It renders and works. | L09, L11 |

Eleven of these sixteen name a machine rule; five (1, 2, 3, 10, 11) have none, and rows 9b, 10 and 11 need a
browser rather than a reader. The checker can say a live region exists; it cannot say the page is worth reading —
and it can say the guard compares the right things but not that the comparisons work, which is why row 9b
runs the guard itself.

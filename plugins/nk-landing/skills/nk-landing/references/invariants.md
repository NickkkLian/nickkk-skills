# The five invariants

A page from this skill is a shop window with a door in it. The window is ordinary: services, hours, prices,
questions people actually ask. The door is the part that can go wrong — a booking is a promise, and a promise
that goes out without anyone reading it is how a small business ends up double-booked, or apologising to
somebody it never meant to write to.

These five hold for every page. A page that breaks one is not from this family.

| # | Invariant | How you can tell by looking |
|---|---|---|
| 1 | **Nothing leaves the page without an approval by a person, and an approval covers only what it names.** A confirmation to the customer and the calendar entry for the slot sit as drafts until a member of staff approves them; anything else — a reminder, a second message — would need an approval of its own. | Book a slot as a visitor: the screen says the request is waiting, and nothing appears in the outbox until the staff panel approves it. Open the page with `?probe=1`: a reminder or other words under a real approval are refused. |
| 2 | **An approval names what it approved.** It carries the request, the revision, the exact words and the slot. What goes out is compared with those — not with whatever the request says now — and if the request changes afterwards, the approval no longer applies. | Book, then change the slot: the desk shows the new revision. In `?probe=1`, other words, another slot, another request's approval and a phone number changed after approval are each refused. |
| 3 | **An approval works once.** The same approval cannot be replayed to send a second message or write a second calendar entry. | Approve, then press "Replay the last approval": it is refused and the refusal is shown, not swallowed. |
| 4 | **The visitor's side cannot approve.** Approval exists only in the staff view; nothing on the public form can stand in for it, and a forged approval is refused: the guard accepts only an approval the desk itself issued. This holds for the page as shipped; it is not a defence against someone who edits the page or injects a script into it. | The customer form has no control that approves. In `?probe=1`, an approval marked as coming from the customer side is refused, and so are a copy of a real approval with other words in it and a built-in object dressed as an approval under the name it is inherited by — the desk keeps a record of what it issued, with nothing inherited in it, and the guard accepts those very approvals, not lookalikes. It is still the rule made visible, not a security control: all of it runs in the visitor's browser, where whoever can edit the page can edit the guard, and a real system checks approvals on its own side. |
| 5 | **A page with no backend says so on the screen.** Demo mode is stated where a person will read it, and the outbox says what would have been sent and to whom, rather than implying it went. | The header carries the demo notice; every outbox row says "not sent". |

## What is not in the family

- **Invented social proof.** No testimonials, no star ratings, no client logos, no "trusted by" counts. A new
  page has no customers yet, and a page that pretends otherwise is the thing this skill exists not to be.
- **Real contact details in anything public.** Sample and demo pages use fictional businesses and the
  reserved 555-01xx numbers. A real shop's page is the shop owner's to publish, not a demo.
- **A booking that is really an e-mail form.** If the page collects a slot, the slot has to mean something:
  the request carries the slot, the approval carries the slot, and the outbox row carries the slot.

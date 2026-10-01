---
name: nk-landing
description: "Turn a written description of a small business — hours, services, price ranges, the questions customers actually ask — into one self-contained HTML page with a booking door, where every confirmation and every calendar write waits for a member of staff to approve that exact draft. Use when a shop, studio or practice needs a page people can book from, when a booking form has to be added to an existing page without a backend, or when a demo of a booking flow is needed that cannot accidentally message anybody. scripts/make_page.py writes the page from a JSON description, scripts/page_check.py checks the twelve rules that keep it honest, scripts/probe_check.py runs the page's own attack battery in Chrome, and the page ships in demo mode: it says on the screen that nothing is sent, and the outbox shows what would have gone and to whom."
license: MIT
compatibility: standard library only, no packages and no build step; the page it writes has no dependencies and fetches nothing when it opens. probe_check.py needs Google Chrome or Chromium; without one, open the page with ?probe=1 in any browser.
metadata:
  provenance: own practice (2026-09) — an offline booking-desk template with a staff-approval guard, and a design system built for pages whose numbers can be checked; see Provenance
  version: 0.1.5
---
# Landing page with a booking door

**A booking is a promise, and a promise that goes out without anyone reading it is how a small shop ends up
double-booked or apologising to somebody it never meant to write to.** The page this skill builds is an
ordinary shop window — services, hours, prices, the four questions people actually ask — with one part built
carefully: nothing leaves it until a person approves the exact words that are about to go.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- A small business — a workshop, a studio, a clinic, a bakery — needs one page that people can book from.
- A booking flow has to be shown to somebody before any of it is wired up, and it must not be able to send.
- An existing page needs a booking door that a person controls, rather than a form that e-mails itself.

## Procedure

1. **Write the description down** as JSON: `python3 <skill-dir>/scripts/make_page.py --init business.json`
   gives you a filled-in example to edit — name, one line about the place, four facts (where, when, how to
   pay, how to reach), three services with a real price range and a sentence of what it involves, the
   questions that actually get asked, and the slots that are free. Ask for the price ranges; a page with
   "contact us for pricing" is the page people leave.
2. **Keep it fictional while it is a demo.** With `"demo": true` the generator refuses a phone number outside
   the reserved 555-01xx range and any e-mail that is not at an example domain. A demo of a business that does
   not exist should not be able to ring a real telephone.
3. **Write the page**: `python3 <skill-dir>/scripts/make_page.py business.json --out page.html`.
   One file: the token file and its three fonts are inlined, nothing is fetched when it opens, and the behaviour comes from
   `assets/starter.html` unchanged — the script fills in content and never writes behaviour.
4. **Read the five invariants** in `references/invariants.md` before you change the template. They are what
   makes the booking door worth having: nothing leaves without an approval; an approval names the revision and
   the text it approved; an approval works once; the visitor's side cannot approve; a page with no backend
   says so on the screen.
5. **Check it**: `python3 <skill-dir>/scripts/page_check.py page.html --single --public`
   (L01 the description is read, not hard-coded · L02 demo mode is on the screen and the outbox says "not
   sent" · L03 no testimonials, ratings or logos · L04 reserved numbers and example domains · L05 every write
   to the outbox goes through the guard · L06 the guard compares each approval with what goes out and accepts
   only ones the desk issued · L07 nothing on the form approves · L08 labels, a live region, focus left alone ·
   L09 nothing fetched at load · L10 colours from the token file · L11 one file · L12 a footer that says what is
   made up).
6. **Try the guard.** `python3 <skill-dir>/scripts/probe_check.py page.html` opens the page in Chrome with
   `?probe=1`: the page tries eleven things against its own guard — the two approved actions, and nine that must
   be refused (the same message twice, other words or another slot under a real approval, a reminder the approval
   never covered, an approval from the customer side, a built-in object dressed as an approval, an approval the
   desk did not issue, another request's approval, a phone number changed after approval) — and the script reads the table. Without Chrome, open
   `page.html?probe=1` in any browser and read it. page_check.py can see that the guard compares the right
   things; only this shows that the comparisons work.
7. **Open it and book something.** Pick a slot, send the request, watch it sit in the staff desk, approve it,
   and read the outbox. Then press the three buttons under "Try the guard". A page where those three do nothing
   visible is not finished.
8. **A person wires it up.** To make it send, connect the outbox to something that sends — and keep the
   approval step in front of it. Every outbox row carries the request id, the revision and the approval, so
   whatever sends can check them again on its own side.

## Rules that keep it honest

- **No social proof a new page has not earned.** No testimonials, no star ratings, no review counts, no
  "trusted by" logos. The checker refuses them, and there is no flag to turn that off.
- **Prices are ranges with a reason**, not "from $X". A range and a sentence about what changes it is what a
  person needs to decide whether to walk in.
- **The questions are the ones that get asked**, including the ones with an unwelcome answer ("no, we do not
  do gluten-free, one oven"). A FAQ that only asks flattering questions is advertising copy.
- **The slots mean something.** The request carries the slot, the approval carries the slot, the outbox row
  carries the slot. A booking form that is really an e-mail box is worse than a phone number.

## Boundaries

- **It does not send anything, and it has no backend.** Demo mode is the only mode the skill ships. Wiring it
  to a real messenger, calendar or database is a person's job, on their own infrastructure.
- **The guard is a demonstration of a rule, not a security control.** It runs in the visitor's own browser,
  where anything can be edited: whoever can change the page or inject a script into it can get past every check
  it makes. So "a forged approval is refused" (invariant 4) holds for the page as shipped — approvals made through
  it and its own code — not against someone who rewrites the page. What the guard is for is to make the rule
  visible and to define what the real system must enforce on its side.
- **It does not design a brand.** One token file, one layout. If you want a different look, change the tokens.
- **It cannot tell whether the description is true.** Hours, prices and the promise that somebody reads the
  desk are the owner's to keep.

## Provenance

Own practice, 2026-09. The approval semantics — an approval carries the revision and the text it approved, it
works once, and the customer's side cannot produce one — come from an offline booking-desk template of mine
that replays 22 scenarios and refuses three attacks; this skill keeps the semantics and none of the code. The
appearance comes from the token file shared with the other pages in this family. The rules about social proof
and about fictional contact details in anything public come from the same practice: the first version of a
demo page for somebody else's shop carried their real phone number, in a file I was about to make public.

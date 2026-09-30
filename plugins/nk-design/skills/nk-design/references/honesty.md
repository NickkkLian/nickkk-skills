# Honesty constraints (the interface is not allowed to lie)

1. Never present: real customer names, real company logos, invented statistics (users, hours saved,
   accuracy), stars, testimonials, "trusted by".
2. Synthetic data looks synthetic and is not ugly: `Demo Utility 02`, `Test Customer 01`, phones only in
   the officially fictional ranges, `123 Example Road`; regular names and aligned numbers look like a ledger.
3. Every number on the page is computed from the loaded data when the page runs; a claim from the README
   is re-computed in the browser or shown as "as of build <date>".
4. Anything that did not really go out or get written carries `Simulated`; there is no "Sent ✓" without it.
5. No API call, no "AI": the demo button is "Simulate suggestions (canned)"; a real key lives in memory
   only, with a "Forget key" action; suggestions go to a review queue, never straight into the data.
6. The footer repeats the README's "not tested / not exercised / not suitable" items word for word.
7. Bad results are shown on the first screen in the danger colour — a failed check, a sum that does not
   reconcile, a write that failed — never only in a log.
8. A fact is never dropped to make text fit. If the plate's lede has to say one more thing and the first screen
   gets tight, change the plate's spacing or move the secondary fact below the fold — do not delete it. The two
   standing rules are that the first screen is understandable in ten seconds and that nothing on the page is
   invented or quietly left out.

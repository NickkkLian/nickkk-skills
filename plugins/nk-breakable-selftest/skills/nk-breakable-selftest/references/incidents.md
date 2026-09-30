# Incidents behind the rules (anonymised, all real)

1. **Green self-test, 266 false positives.** A copy-alignment detector listed tracked files with a git
   option that stops non-ASCII file names from being octal-escaped. Its self-test created a temp repo with
   such names and round-tripped them — through its *own* second listing command. Removing the option from
   the real path: self-test green, real run 266 false positives. Fix: one `list_tracked_files()` used by both.
2. **Lookalike implementation.** A validator's self-test re-implemented the extractor inline. Sabotaging
   the real extractor produced no reaction and the validator misidentified the auth guard actually used by
   the project (two false findings). Fix: the self-test imports the same module the validator uses.
3. **Scorer with a hidden `+4`.** A screening test asserted "scores come only from the rules file" by
   grepping the source for variable names the scorer did not use, and `all([])` is true. Inserting a
   conditional `+4` flipped the ranking with 28 assertions green. Fix: the break matrix with a named
   assertion per case, a control row, and crash ≠ detection.
4. **Fourteen green, two decorative.** A structural lint written the same afternoon as this skill passed
   14/14 self-test checks. The break matrix neutralised its twelve `append` lines one at a time: two stayed
   green. One sample tripped two branches at once, so killing either branch was invisible. Fix: exclusive
   samples; the matrix then reported 12/12 caught.
5. **A crash that looked like a catch.** Deleting a rule's `append` line together with its `if` body
   produced a SyntaxError and exit 1. Counted naively, that is "the self-test went red". It was a crash.
   Fix: criterion 3 (no traceback), and neutralise with `pass` instead of deleting.
6. **One total floor.** A sabotage scaffold counted red cases across two suites against a single floor;
   deleting an entire suite still passed. Fix: a floor per suite.
7. **Wrong break point, wrong conclusion.** Two attempted breaks of a monthly loop changed nothing because
   an inner guard made them inert; the tests were declared "not covering the boundary". The third break
   (moving the guard) went red at once. Rule 8.
8. **Dead `quiet` flag.** A sentinel's output condition contained `out and ... and not out`, a conjunction
   that is always false; the flag never changed any output. Found only by running all eight input
   combinations. Rule: exercise every branch of the reporting logic, not only the detection logic.

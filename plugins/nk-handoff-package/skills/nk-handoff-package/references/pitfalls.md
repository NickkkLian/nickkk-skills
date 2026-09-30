# Pitfalls met while building and using this (each cost at least one round)

1. **Existence check on the first token.** `command -v $cmd` on "python3 check.py" tests whether the
   interpreter exists, not the script. Check the file.
2. **A pipe swallows the exit code.** `check.py | tail` returns tail's status. Capture, then tail.
3. **Crash and FAIL sharing exit 1.** A checker that died halfway looked like a checker that found a
   problem. Three states, and the traceback printed to stdout.
4. **Denominator guessed by the runner.** When the package's shape changed, the guessed count silently
   shrank. The package declares its steps; a missing declaration refuses to run.
5. **Template passes.** A gate looked for the word "why" in a commit message; the word was in the template
   line. Exempt by hash of the unfilled template, check everything else.
6. **Empty set is green.** An untouched package passed eleven of thirteen gates with "0 items, all
   compliant". Every gate needs an input that makes it fail; an empty input is not a pass.
7. **One total floor.** Deleting an entire test suite still met the total sabotage count. Floor per suite.
8. **Fixing the mismatch instead of explaining it.** A trust-root mismatch is not resolved by editing the
   package until the hashes agree. It is resolved by finding out who changed what.
9. **Acceptance material inside the package.** Handing the executor the audit manual is handing them the
   bypass list. Keep it outside, on the drift-exemption list.
10. **Audit without a stop rule.** Eleven rounds and a gate 2.3× the size of the deliverable. Decide the
    threat model (a colleague, not an adversary) and the stop condition before the first round.

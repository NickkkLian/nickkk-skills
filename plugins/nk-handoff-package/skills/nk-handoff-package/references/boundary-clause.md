# START — <<< FILL project name >>>

> You have no context. This package is self-contained: read it in order and you can work. Do not skip.

## Step 0 — the boundary (thirty seconds; harder than everything after it)

**Your write scope is this package. Not one byte goes outside it.** Do not write to the owner's
repositories, to any shared directory, to any agent configuration directory, to any system location.
Anything that must leave the package goes into `output/pending/`, and the acceptor moves it. This is a
design, not distrust: the places outside this package have other lines of work writing to them right now,
and a write from you would silently overwrite someone else's work without an error.

**Remotes are read-only.** Clone, fetch, read — do not `git push`, do not create branches, tags, releases,
pull requests or issues, do not call any API that writes. This package is not a git repository and has no
remote; that is deliberate.

The reason is collaboration, not technology: a push from you would not fail and would not conflict; it
would overwrite what another line is doing, and nobody would notice at once. This is written down because
without it you might, with good intentions, "sync things up".

**If you already wrote to a remote: stop, and write in `output/RECEIPT.md` what, which repository, which
branch.** Reporting it is fine; being found by a diff is the problem.

## Step 1 — read the discipline layer
<<< FILL which files under reference/ carry the rules, and why reading them costs the most >>>

## Step 2 — read the project material, in this order
<<< FILL the reading order under reference/ >>>

## Step 3 — confirm the package is complete before working
<<< FILL a command that exercises the package (build, test, render); if it fails, the package is
incomplete — say so in the receipt instead of working around it >>>

## What you hand back

Everything goes under `output/`:
- `work/` — your working copy; the diff against `reference/` is your change
- `evidence/` — one file per completion claim, starting with the re-run command (`$ …`) and containing the
  raw output, not a summary
- `pending/{commit-messages,devlog,memory,decisions}/` — records in the shapes of the templates there
- `RECEIPT.md` — with a filled **Unsure** section (what you are not sure about) and **Boundary crossings**

Before handing back: `cd output && python3 handback_check.py` — exit code 0 is the condition for handing back.

## What happens after you hand back

1. The acceptor first compares the trust root kept outside the package (so the checker itself was not
   replaced) before trusting anything the package says about itself.
2. The acceptance runner executes the declared steps (trust root / self-check / drift against the source)
   and records how many were planned, how many ran, how many failed. A step that could not run is "not
   run", never "passed".
3. Every file in `output/pending/` is replayed by hand.
4. An independent auditor reads only `output/evidence/` — not the receipt's wording — and gives one of
   three verdicts: supported, not supported, insufficient.

What is valued most in a hand-back: something we had not thought of, and any gate you found you could
get around. Gates are of three kinds — mechanical, needing your participation to trigger, and depending
on your honest answer. The second and third are known weak spots; say what you saw.

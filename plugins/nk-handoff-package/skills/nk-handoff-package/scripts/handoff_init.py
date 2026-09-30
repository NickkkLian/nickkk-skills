#!/usr/bin/env python3
"""handoff_init.py — build a self-contained handoff package for an executor that has no context (another agent, a
contractor, a future you), seal its read-only layer, and pin a trust root outside the package.

    python3 handoff_init.py <root> <task> [--form full|round|asset]   # scaffold (refuses to touch a non-empty package)
    python3 handoff_init.py <root> <task> --seal                       # hash everything under reference/ into MANIFEST.sha256
    python3 handoff_init.py <root> <task> --trust-root [OUTFILE]       # pin the checker files' hashes OUTSIDE the package
    python3 handoff_init.py --selftest

Package layout: START.md (boundary clause as orders + reading order + completeness check) · TASK.md (this round) ·
reference/ (read-only inputs + MANIFEST.sha256) · output/{handback_check.py, project_gates.py, RECEIPT.md, evidence/,
work/, pending/{commit-messages,devlog,memory,decisions}/} · .templates.sha256 · .acceptance.txt (declared denominator).
"""
import datetime, hashlib, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FILL = "<<< FILL"
TEMPLATES = {
    "output/RECEIPT.md": "# Hand-back receipt\n\n## What I did\n<<< FILL one paragraph >>>\n\n## How I verified it\n<<< FILL commands and where their raw output is (output/evidence/) >>>\n\n## Unsure\n<<< FILL what you are unsure about; write 'none' only if true >>>\n\n## Boundary crossings\n<<< FILL anything written outside the package or to any remote; write 'none' if none >>>\n",
    "output/pending/commit-messages/_template.md": "# <<< FILL one line: what changed >>>\n\nWhy: <<< FILL the reason, dated >>>\nVerified by: <<< FILL the command and its evidence file >>>\n",
    "output/pending/devlog/_template.jsonl": '{"date": "<<< FILL YYYY-MM-DD >>>", "kind": "minor", "note": "<<< FILL one sentence >>>"}\n',
    "output/pending/memory/_template.md": "---\nname: <<< FILL slug >>>\ndescription: <<< FILL one line >>>\n---\n\n<<< FILL the fact >>>\n\n**Holds when:** <<< FILL conditions >>>\n",
    "output/pending/decisions/_template.md": "# Decision drafted on the owner's behalf\n\nWhat: <<< FILL >>>\nWhy: <<< FILL >>>\nVeto point: <<< FILL where the owner can still reverse this >>>\n",
    "output/project_gates.py": "# Project-specific gates. Return (location, description, is_fail) tuples; say what each gate cannot catch.\ndef checks(pkg, out):\n    return []\n",
    "TASK.md": "# This round\n\nGoal: <<< FILL one sentence >>>\n\nDeliverable: <<< FILL what goes in output/work/ >>>\n\nNot changing: <<< FILL what must stay as it is >>>\n\nDo not: <<< FILL e.g. do not edit handback_check.py or project_gates.py >>>\n",
}
ACCEPTANCE = {"full": ["trustroot", "selfcheck", "drift"], "round": ["trustroot", "selfcheck"], "asset": ["trustroot", "selfcheck", "drift"]}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def start_md():
    return open(os.path.join(HERE, "..", "references", "boundary-clause.md"), encoding="utf-8").read()


def scaffold(root, task, form="full"):
    pkg = os.path.join(os.path.abspath(root), task)
    if os.path.exists(pkg) and os.listdir(pkg):
        raise SystemExit(f"refusing: {pkg} exists and is not empty — never overwrite a live package")
    for d in ("reference", "output/evidence", "output/work", "output/pending/commit-messages", "output/pending/devlog", "output/pending/memory", "output/pending/decisions"):
        os.makedirs(os.path.join(pkg, d), exist_ok=True)
    open(os.path.join(pkg, "START.md"), "w", encoding="utf-8").write(start_md())
    for rel, txt in TEMPLATES.items():
        open(os.path.join(pkg, rel), "w", encoding="utf-8").write(txt)
    shutil.copy(os.path.join(HERE, "handback_check.py"), os.path.join(pkg, "output", "handback_check.py"))
    with open(os.path.join(pkg, ".templates.sha256"), "w") as fh:
        for rel in TEMPLATES:
            if rel != "output/project_gates.py" and rel != "TASK.md":
                fh.write(f"{sha(os.path.join(pkg, rel))}  {rel}\n")
    open(os.path.join(pkg, ".acceptance.txt"), "w").write("\n".join(ACCEPTANCE[form]) + "\n")
    return pkg


def seal(pkg):
    ref = os.path.join(pkg, "reference")
    rows = []
    for root, _, files in os.walk(ref):
        for f in sorted(files):
            if f == "MANIFEST.sha256":
                continue
            p = os.path.join(root, f)
            rows.append(f"{sha(p)}  {os.path.relpath(p, ref)}")
    open(os.path.join(ref, "MANIFEST.sha256"), "w").write("\n".join(rows) + ("\n" if rows else ""))
    return len(rows)


PINNED = ["START.md", "output/handback_check.py", "output/project_gates.py", ".templates.sha256", "reference/MANIFEST.sha256"]


def trust_root(pkg, outfile=None):
    present = [f for f in PINNED if os.path.isfile(os.path.join(pkg, f))]
    if "output/handback_check.py" not in present:
        raise SystemExit("nothing to pin: output/handback_check.py is missing")
    outfile = outfile or os.path.join(os.path.dirname(pkg), f"{os.path.basename(pkg)}-trust-root-{datetime.date.today()}.txt")
    with open(outfile, "w", encoding="utf-8") as fh:
        fh.write(f"# {os.path.basename(pkg)} · trust root · {datetime.datetime.now():%Y-%m-%d %H:%M}\n")
        fh.write("# Compare byte for byte at hand-back; any mismatch ⇒ nothing the package reports about itself counts.\n")
        fh.write("# A mismatch is not fixed by editing the package to match; it is explained.\n")
        for f in present:
            fh.write(f"{sha(os.path.join(pkg, f))}  {f}\n")
    return outfile, present


def fill_demo(pkg):
    """Fill a scaffolded package so that every generic gate passes (used by self-tests and as a worked example)."""
    open(os.path.join(pkg, "output", "RECEIPT.md"), "w").write("# Hand-back receipt\n\n## What I did\nAdded app.py.\n\n## How I verified it\n$ python3 output/work/app.py — see output/evidence/run.txt\n\n## Unsure\nnone\n\n## Boundary crossings\nnone\n")
    open(os.path.join(pkg, "output", "work", "app.py"), "w").write("print('hi')\n")
    open(os.path.join(pkg, "output", "evidence", "run.txt"), "w").write("$ python3 output/work/app.py\nhi\nexit=0\n")
    open(os.path.join(pkg, "output", "pending", "commit-messages", "app.md"), "w").write("# Add app.py\n\nWhy: 2026-09-15 demo.\nVerified by: python3 output/work/app.py (output/evidence/run.txt)\n")
    open(os.path.join(pkg, "output", "pending", "devlog", "app.jsonl"), "w").write('{"date": "2026-09-15", "kind": "minor", "note": "added app.py"}\n')


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory() as d:
        pkg = scaffold(d, "t1", "full")
        need = ["START.md", "TASK.md", "output/handback_check.py", "output/project_gates.py", "output/RECEIPT.md", ".templates.sha256", ".acceptance.txt", "output/pending/memory/_template.md"]
        chk(all(os.path.exists(os.path.join(pkg, f)) for f in need), "scaffold creates the skeleton")
        chk("write scope is this package" in open(os.path.join(pkg, "START.md")).read().lower() and "remotes are read-only" in open(os.path.join(pkg, "START.md")).read().lower(), "START.md carries the boundary clause (write scope + read-only remotes)")
        chk(open(os.path.join(pkg, ".acceptance.txt")).read().split() == ["trustroot", "selfcheck", "drift"], "form=full declares three acceptance steps")
        chk(scaffold(d, "t2", "round") and open(os.path.join(d, "t2", ".acceptance.txt")).read().split() == ["trustroot", "selfcheck"], "form=round declares two")
        open(os.path.join(pkg, "reference", "keep.txt"), "w").write("keep me\n")
        refused = False
        try:
            scaffold(d, "t1")
        except SystemExit:
            refused = True
        chk(refused and open(os.path.join(pkg, "reference", "keep.txt")).read() == "keep me\n", "a non-empty package is refused and left untouched")
        n = seal(pkg)
        chk(n == 1 and os.path.isfile(os.path.join(pkg, "reference", "MANIFEST.sha256")), "seal writes a manifest with one entry")
        out, present = trust_root(pkg, os.path.join(d, "root.txt"))
        txt = open(out).read()
        chk(len(present) == 5 and txt.count("\n") >= 8 and "output/handback_check.py" in txt, f"trust root pins 5 files outside the package ({present})")
        open(os.path.join(pkg, "output", "handback_check.py"), "a").write("# tampered\n")
        chk(sha(os.path.join(pkg, "output", "handback_check.py")) != [l.split()[0] for l in txt.splitlines() if l.endswith("output/handback_check.py")][0], "editing the checker changes its hash against the trust root")
        try:
            trust_root(os.path.join(d, "nope"))
            chk(False, "trust root on a missing package must refuse")
        except SystemExit:
            chk(True, "trust root on a missing package refuses")
    return ok, lines


def main(argv):
    if "--selftest" in argv:
        ok, lines = selftest()
        print(f"handoff_init selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 2:
        print(__doc__); return 2
    root, task = pos[0], pos[1]
    pkg = os.path.join(os.path.abspath(root), task)
    if "--seal" in argv:
        print(f"sealed reference/: {seal(pkg)} file(s) in MANIFEST.sha256"); return 0
    if "--trust-root" in argv:
        out, present = trust_root(pkg, pos[2] if len(pos) > 2 else None)
        print(f"trust root written outside the package: {out}\n  pinned {len(present)}/{len(PINNED)}: {present}"); return 0
    form = argv[argv.index("--form") + 1] if "--form" in argv else "full"
    pkg = scaffold(root, task, form)
    print(f"scaffolded {pkg} (form {form}). Next: fill every '{FILL}' slot, put inputs in reference/, then --seal and --trust-root.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

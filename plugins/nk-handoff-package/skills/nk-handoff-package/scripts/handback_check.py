#!/usr/bin/env python3
"""handback_check.py — the generic hand-back self-check of a handoff package. The executor runs it before handing
back; the acceptor runs the same file on their copy. One ruler, both sides.

    cd <package>/output && python3 handback_check.py          # or: python3 handback_check.py --pkg <package>
    python3 handback_check.py --selftest     # from the skill's scripts/ folder: it builds sample packages with handoff_init.py

Gates (generic — "would this still hold on another project?"; project-specific gates live in project_gates.py next to
this file, exposing checks(pkg, out) -> iterable of (location, description, is_fail) and are loaded automatically):
  G0 encoding      every text file under output/ decodes as UTF-8
  G1 skeleton      START.md, TASK.md, output/RECEIPT.md, output/evidence/, output/pending/*, .templates.sha256 exist
  G2 receipt       RECEIPT.md is not the verbatim template; "Unsure" and "Boundary crossings" sections are filled (not "<<< FILL")
  G3 evidence      every file in output/evidence/ starts with a re-run line ("$ <command>")
  G4 pending       every file under output/pending/ is either the verbatim template (hash in .templates.sha256) or filled
  G5 reference     reference/MANIFEST.sha256 still verifies (the read-only layer was not altered)
  G6 records       if output/work/ has files, at least one filled commit-message and one devlog line exist
  G7 project       project_gates.py loaded and its checks ran
Exit: 0 all pass · 1 some FAIL · 2 the check itself crashed (traceback printed to stdout so a swallowed stderr cannot
hide it). Three states, because "did not finish" and "found a problem" must not share an exit code.
"""
import hashlib, importlib.util, os, sys, tempfile, traceback

sys.dont_write_bytecode = True   # the self-test imports a sibling script; a .pyc in scripts/ would carry local paths into the package

FILL = "<<< FILL"
REQUIRED = ["START.md", "TASK.md", "output/RECEIPT.md", "output/evidence", "output/pending/commit-messages",
            "output/pending/devlog", "output/pending/memory", "output/pending/decisions", ".templates.sha256"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def read_manifest(p):
    out = {}
    if os.path.isfile(p):
        for line in open(p, encoding="utf-8"):
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and len(parts[0]) == 64:
                out[parts[1].strip()] = parts[0]
    return out


def section(text, title):
    lines, grab, buf = text.split("\n"), False, []
    for l in lines:
        if l.startswith("## "):
            grab = l[3:].strip().lower().startswith(title.lower())
            continue
        if grab:
            buf.append(l)
    return "\n".join(buf).strip()


def gates(pkg):
    """Yields (gate, location, message, is_fail)."""
    out_dir = os.path.join(pkg, "output")
    for root, _, files in os.walk(out_dir):
        for f in files:
            p = os.path.join(root, f)
            if f.endswith((".md", ".txt", ".py", ".json", ".jsonl", ".yaml", ".yml", ".sh")):
                try:
                    open(p, encoding="utf-8").read()
                except UnicodeDecodeError:
                    yield "G0", os.path.relpath(p, pkg), "not UTF-8", True
    for r in REQUIRED:
        yield "G1", r, "present" if os.path.exists(os.path.join(pkg, r)) else "missing", not os.path.exists(os.path.join(pkg, r))
    templates = read_manifest(os.path.join(pkg, ".templates.sha256"))
    rec_p = os.path.join(pkg, "output", "RECEIPT.md")
    if os.path.isfile(rec_p):
        rec = open(rec_p, encoding="utf-8").read()
        if templates.get("output/RECEIPT.md") == sha(rec_p):
            yield "G2", "output/RECEIPT.md", "still the verbatim template", True
        else:
            for title in ("Unsure", "Boundary crossings"):
                body = section(rec, title)
                bad = (not body) or (FILL in body)
                yield "G2", f"output/RECEIPT.md ## {title}", "filled" if not bad else "empty or template text (write 'none' if none)", bad
    ev = os.path.join(pkg, "output", "evidence")
    if os.path.isdir(ev):
        files = [f for f in sorted(os.listdir(ev)) if not f.startswith(".")]
        yield "G3", "output/evidence/", f"{len(files)} file(s)" if files else "no evidence files at all", not files
        for f in files:
            first = open(os.path.join(ev, f), encoding="utf-8", errors="replace").readline().strip()
            ok = first.startswith("$ ") and len(first) > 2
            yield "G3", f"output/evidence/{f}", "starts with a re-run command" if ok else f"first line is not '$ <command>': {first[:50]!r}", not ok
    pend = os.path.join(pkg, "output", "pending")
    filled_commit, filled_devlog = 0, 0
    if os.path.isdir(pend):
        for root, _, files in os.walk(pend):
            for f in files:
                p = os.path.join(root, f); rel = os.path.relpath(p, pkg)
                if templates.get(rel) == sha(p):
                    continue                                       # verbatim template: exempt, by equation not by name
                txt = open(p, encoding="utf-8", errors="replace").read()
                bad = FILL in txt or not txt.strip()
                yield "G4", rel, "filled" if not bad else "half-filled (template markers left) or empty", bad
                if not bad and "/commit-messages/" in rel + "/":
                    filled_commit += 1
                if not bad and "/devlog/" in rel + "/":
                    filled_devlog += 1
    man = os.path.join(pkg, "reference", "MANIFEST.sha256")
    if os.path.isfile(man):
        changed = [rel for rel, h in read_manifest(man).items() if not os.path.isfile(os.path.join(pkg, "reference", rel)) or sha(os.path.join(pkg, "reference", rel)) != h]
        yield "G5", "reference/", "read-only layer unchanged" if not changed else f"altered or missing: {changed[:5]}", bool(changed)
    else:
        yield "G5", "reference/MANIFEST.sha256", "no manifest — the read-only layer cannot be verified (seal the package)", True
    work = os.path.join(pkg, "output", "work")
    has_work = any(files for _, _, files in os.walk(work)) if os.path.isdir(work) else False
    if has_work:
        yield "G6", "output/pending/commit-messages", f"{filled_commit} filled" if filled_commit else "work delivered but no commit message written", filled_commit == 0
        yield "G6", "output/pending/devlog", f"{filled_devlog} filled" if filled_devlog else "work delivered but no devlog line written", filled_devlog == 0
    pg = os.path.join(pkg, "output", "project_gates.py")
    if os.path.isfile(pg):
        spec = importlib.util.spec_from_file_location("project_gates", pg)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        n = 0
        for loc, desc, fail in mod.checks(pkg, out_dir):
            n += 1
            yield "G7", loc, desc, bool(fail)
        yield "G7", "output/project_gates.py", f"loaded, {n} project check(s) ran", False
    else:
        yield "G7", "output/project_gates.py", "missing (write one, even if it only returns [])", True


def run(pkg):
    rows = list(gates(pkg))
    fails = [r for r in rows if r[3]]
    for g, loc, msg, fail in rows:
        print(f"  {'✘' if fail else '✔'} {g} {loc}: {msg}")
    print(f"{'✘' if fails else '✔'} handback check: {len(rows)} checks, {len(fails)} FAIL")
    return 1 if fails else 0


STANDALONE_NOTE = ("the self-test builds sample packages with handoff_init.py, which lives in the skill's scripts/ folder, not "
                   "inside a package. Run it there: python3 <skill>/scripts/handback_check.py --selftest. Inside a package, "
                   "this file is trusted through its pinned hash (handoff_verify.py --trust-root), not through a self-test.")


def selftest():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import handoff_init
    except ImportError:                                  # a copy inside a package: say what to do instead of a traceback
        return False, [f"  ✘ handoff_init.py is not next to this file: {STANDALONE_NOTE}"]
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    def fails(pkg):
        return {(g, loc) for g, loc, _, f in gates(pkg) if f}

    with tempfile.TemporaryDirectory() as d:
        pkg = handoff_init.scaffold(d, "demo", "full")
        open(os.path.join(pkg, "reference", "spec.md"), "w").write("the spec\n"); handoff_init.seal(pkg)
        f0 = fails(pkg)
        chk(any(g == "G2" for g, _ in f0) and ("G3", "output/evidence/") in f0, f"a fresh, unfilled package FAILS (receipt template, no evidence) — empty is not green: {sorted(f0)[:4]}")
        handoff_init.fill_demo(pkg)
        chk(not fails(pkg), f"a properly filled package passes every gate ({sorted(fails(pkg))})")
        open(os.path.join(pkg, "reference", "spec.md"), "a").write("tampered\n")
        chk(("G5", "reference/") in fails(pkg), "altering the read-only layer FAILS G5")
        open(os.path.join(pkg, "reference", "spec.md"), "w").write("the spec\n")
        open(os.path.join(pkg, "output", "evidence", "bad.txt"), "w").write("all tests passed\n")
        chk(("G3", "output/evidence/bad.txt") in fails(pkg), "an evidence file without a '$ ' re-run line FAILS G3")
        os.remove(os.path.join(pkg, "output", "evidence", "bad.txt"))
        rec = os.path.join(pkg, "output", "RECEIPT.md"); txt = open(rec).read()
        open(rec, "w").write(txt.replace("## Unsure\nnone\n", "## Unsure\n<<< FILL what you are unsure about >>>\n"))
        chk(("G2", "output/RECEIPT.md ## Unsure") in fails(pkg), "template text left in the receipt's Unsure section FAILS G2")
        open(rec, "w").write(txt)
        os.remove(os.path.join(pkg, "output", "pending", "commit-messages", "app.md"))
        cm = os.path.join(pkg, "output", "pending", "commit-messages", "work.md"); open(cm, "w").write("")
        chk(("G6", "output/pending/commit-messages") in fails(pkg) and ("G4", "output/pending/commit-messages/work.md") in fails(pkg), "work delivered with an empty commit message FAILS G4 and G6")
        handoff_init.fill_demo(pkg)
        tpl = os.path.join(pkg, "output", "pending", "memory", "_template.md"); keep = open(tpl).read()
        open(tpl, "w").write(keep.replace("<<< FILL the fact >>>", "a fact"))          # edited in place, still named _template
        chk(("G4", "output/pending/memory/_template.md") in fails(pkg), "a template edited in place (same name, different hash) is checked, not exempt")
        open(tpl, "w").write(keep)
        open(os.path.join(pkg, "output", "project_gates.py"), "w").write("def checks(pkg, out):\n    return [('output/work/app.py', 'must import nothing', True)]\n")
        chk(("G7", "output/work/app.py") in fails(pkg), "a failing project gate FAILS G7 with its location")
        open(os.path.join(pkg, "output", "project_gates.py"), "w").write("def checks(pkg, out):\n    raise RuntimeError('boom')\n")
        crashed = False
        try:
            list(gates(pkg))
        except RuntimeError:
            crashed = True
        chk(crashed, "a crashing project gate propagates (exit 2 in main), it is not reported as a pass")
        import subprocess
        alone = os.path.join(d, "alone"); os.makedirs(alone)
        shutil_copy = __import__("shutil").copy
        shutil_copy(os.path.abspath(__file__), os.path.join(alone, "handback_check.py"))
        r = subprocess.run([sys.executable, "-B", "handback_check.py", "--selftest"], cwd=alone, capture_output=True, text=True)
        chk(r.returncode == 2 and "handoff_init.py is not next to this file" in r.stdout and "Traceback" not in r.stdout + r.stderr,
            f"a copy of this file alone (as inside a package) explains where to run the self-test, exit 2, no traceback ({r.returncode})")
    return ok, lines


def main(argv):
    if "--selftest" in argv:
        ok, lines = selftest()
        print(f"handback_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    pkg = argv[argv.index("--pkg") + 1] if "--pkg" in argv else os.path.abspath(os.path.join(os.getcwd(), ".."))
    if not os.path.isfile(os.path.join(pkg, "START.md")):
        print(f"not a handoff package (no START.md): {pkg}"); return 2
    return run(pkg)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc(file=sys.stdout)
        print("✘ handback check CRASHED — this is exit 2, not a result")
        sys.exit(2)

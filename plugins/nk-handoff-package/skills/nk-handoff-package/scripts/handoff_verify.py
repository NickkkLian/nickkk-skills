#!/usr/bin/env python3
"""handoff_verify.py — the acceptor's entry point: an executable checklist with a declared denominator.

    python3 handoff_verify.py <package> --trust-root <file> [--source DIR]
    python3 handoff_verify.py --selftest

Reads the package's own .acceptance.txt (one step per line: trustroot / selfcheck / drift) — the package declares how
many steps apply, the runner does not guess. Steps:
  trustroot  every pinned file's sha256 equals the trust-root file kept outside the package; a mismatch voids every
             "green" the package reports about itself (the checker could have been replaced)
  selfcheck  runs output/handback_check.py on a COPY of the package and keeps the raw output; exit 0 = pass,
             1 = FAIL, 2 = the checker crashed (reported as CRASH, never as pass)
  drift      reference/MANIFEST.sha256 verifies (the executor did not alter its inputs); with --source DIR, every
             reference file is also compared with the true source by basename + content hash and stale ones listed
Prints "planned N / ran M / failed K"; a step that could not run counts as NOT RUN, never as pass. Exit 0 only when
every planned step ran and passed; 1 otherwise; 2 on usage error. Then dispatch an independent auditor on
output/evidence/ — this runner is the acceptor's own check, not the audit.
"""
import hashlib, os, shutil, subprocess, sys, tempfile

sys.dont_write_bytecode = True   # the self-test imports a sibling script; a .pyc in scripts/ would carry local paths into the package


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def read_manifest(p):
    out = {}
    for line in open(p, encoding="utf-8"):
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            out[parts[1].strip()] = parts[0]
    return out


def step_trustroot(pkg, root_file):
    if not root_file or not os.path.isfile(root_file):
        return "NOT RUN", "no trust-root file given or found"
    pins = read_manifest(root_file)
    bad = [f for f, h in pins.items() if not os.path.isfile(os.path.join(pkg, f)) or sha(os.path.join(pkg, f)) != h]
    return ("PASS", f"{len(pins)} pinned files match") if not bad else ("FAIL", f"mismatch: {bad} — nothing the package says about itself counts until this is explained")


def step_selfcheck(pkg):
    chk = os.path.join(pkg, "output", "handback_check.py")
    if not os.path.isfile(chk):
        return "NOT RUN", "output/handback_check.py missing", ""
    tmp = tempfile.mkdtemp(prefix="handoff_verify_")
    copy = os.path.join(tmp, "pkg"); shutil.copytree(pkg, copy)
    r = subprocess.run([sys.executable, "handback_check.py"], cwd=os.path.join(copy, "output"), capture_output=True, text=True, timeout=300)
    shutil.rmtree(tmp, ignore_errors=True)
    out = r.stdout + r.stderr
    state = "PASS" if r.returncode == 0 else "FAIL" if r.returncode == 1 else "CRASH"
    return state, f"exit {r.returncode}", out


def step_drift(pkg, source=None):
    man = os.path.join(pkg, "reference", "MANIFEST.sha256")
    if not os.path.isfile(man):
        return "NOT RUN", "reference/MANIFEST.sha256 missing (package never sealed)"
    pins = read_manifest(man)
    altered = [f for f, h in pins.items() if not os.path.isfile(os.path.join(pkg, "reference", f)) or sha(os.path.join(pkg, "reference", f)) != h]
    if altered:
        return "FAIL", f"read-only layer altered in the package: {altered[:5]}"
    if not source:
        return "PASS", f"{len(pins)} reference files unchanged (no --source given: staleness against the true source not checked)"
    index = {}
    for root, _, files in os.walk(source):
        for f in files:
            index.setdefault(f, set()).add(sha(os.path.join(root, f)))
    stale, unknown = [], []
    for f, h in pins.items():
        base = os.path.basename(f)
        if base not in index:
            unknown.append(f)
        elif h not in index[base]:
            stale.append(f)
    if stale or unknown:
        return "FAIL", f"stale vs source: {stale[:5]}; not found in source: {unknown[:5]}"
    return "PASS", f"{len(pins)} reference files unchanged and current vs source"


def verify(pkg, root_file=None, source=None):
    plan_p = os.path.join(pkg, ".acceptance.txt")
    if not os.path.isfile(plan_p):
        return 2, ["no .acceptance.txt — the package must declare its own denominator; refusing to guess"], {}
    planned = [l.strip() for l in open(plan_p) if l.strip()]
    lines, results, raw = [], {}, {}
    for step in planned:
        if step == "trustroot":
            st, msg = step_trustroot(pkg, root_file)
        elif step == "selfcheck":
            st, msg, out = step_selfcheck(pkg); raw["selfcheck"] = out
        elif step == "drift":
            st, msg = step_drift(pkg, source)
        else:
            st, msg = "NOT RUN", "unknown step name"
        results[step] = st
        lines.append(f"  {'✔' if st == 'PASS' else '✘'} {step:<10} {st:<8} {msg}")
    ran = sum(1 for s in results.values() if s in ("PASS", "FAIL", "CRASH"))
    failed = sum(1 for s in results.values() if s in ("FAIL", "CRASH"))
    lines.append(f"planned {len(planned)} / ran {ran} / failed {failed}" + (" — NOT RUN steps are not passes" if ran < len(planned) else ""))
    rc = 0 if ran == len(planned) and failed == 0 else 1
    lines.append("next: dispatch an independent auditor on output/evidence/ (this runner is not the audit)")
    return rc, lines, raw


def selftest():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import handoff_init
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "source"); os.makedirs(src); open(os.path.join(src, "spec.md"), "w").write("the spec\n")
        pkg = handoff_init.scaffold(os.path.join(d, "ws"), "job", "full")
        shutil.copy(os.path.join(src, "spec.md"), os.path.join(pkg, "reference", "spec.md")); handoff_init.seal(pkg)
        handoff_init.fill_demo(pkg)
        root, _ = handoff_init.trust_root(pkg, os.path.join(d, "root.txt"))
        rc, out, raw = verify(pkg, root, src)
        chk(rc == 0 and out[-2].startswith("planned 3 / ran 3 / failed 0"), f"control: filled, sealed, pinned package passes 3/3 ({out[-2]})")
        rc, out, _ = verify(pkg, None, src)
        chk(rc == 1 and "NOT RUN" in out[0] and "ran 2" in out[-2], "no trust-root file → trustroot NOT RUN, overall not a pass")
        open(os.path.join(pkg, "output", "handback_check.py"), "a").write("# swapped\n")
        rc, out, _ = verify(pkg, root, src)
        chk(rc == 1 and "FAIL" in out[0] and "handback_check.py" in out[0], "a modified checker fails the trust root by name")
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "handback_check.py"), os.path.join(pkg, "output", "handback_check.py"))
        open(os.path.join(pkg, "output", "evidence", "run.txt"), "w").write("no rerun line\n")
        rc, out, raw = verify(pkg, root, src)
        chk(rc == 1 and "FAIL" in out[1] and "G3" in raw["selfcheck"], "a broken evidence file fails selfcheck and the raw checker output is kept")
        open(os.path.join(pkg, "output", "evidence", "run.txt"), "w").write("$ python3 output/work/app.py\nhi\n")
        open(os.path.join(pkg, "output", "project_gates.py"), "w").write("def checks(pkg, out):\n    raise RuntimeError('boom')\n")
        rc, out, _ = verify(pkg, root, src)
        chk("CRASH" in out[1], "a crashing checker is CRASH, not FAIL and not pass")
        open(os.path.join(pkg, "output", "project_gates.py"), "w").write("def checks(pkg, out):\n    return []\n")
        open(os.path.join(src, "spec.md"), "w").write("the spec v2\n")
        rc, out, _ = verify(pkg, root, src)
        chk(rc == 1 and "stale vs source" in out[2], "a source file newer than the package copy is reported as stale (drift ≠ tamper)")
        open(os.path.join(pkg, "reference", "spec.md"), "a").write("x")
        rc, out, _ = verify(pkg, root, src)
        chk("altered in the package" in out[2], "an altered reference file is reported as altered")
        os.remove(os.path.join(pkg, ".acceptance.txt"))
        rc, out, _ = verify(pkg, root, src)
        chk(rc == 2, "a package without .acceptance.txt is refused (no guessed denominator)")
    return ok, lines


def main(argv):
    if "--selftest" in argv:
        ok, lines = selftest()
        print(f"handoff_verify selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    pos = [a for a in argv if not a.startswith("--") and (argv.index(a) == 0 or argv[argv.index(a) - 1] not in ("--trust-root", "--source"))]
    if not pos:
        print(__doc__); return 2
    root = argv[argv.index("--trust-root") + 1] if "--trust-root" in argv else None
    source = argv[argv.index("--source") + 1] if "--source" in argv else None
    rc, lines, raw = verify(os.path.abspath(pos[0]), root, source)
    print("\n".join(lines))
    if raw.get("selfcheck"):
        print("--- raw handback_check output ---"); print(raw["selfcheck"].rstrip())
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

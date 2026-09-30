#!/usr/bin/env python3
"""breakcheck.py — prove that a self-test goes red when the code it guards is broken.

    python3 breakcheck.py --root <dir> --cmd "python3 checker.py --selftest" --spec mutations.json
    python3 breakcheck.py --root <dir> --cmd "python3 checker.py --selftest" --auto checker.py [--pattern REGEX]
    python3 breakcheck.py --selftest

The target directory is copied to a temporary sandbox; only the copy is mutated. For every mutation four
things must hold (a "break matrix"):
  1. the mutated run exits non-zero              2. the unmutated control run exits zero
  3. the red is not a crash (no traceback)       4. if must_mention is set, the output names that assertion
--spec  : JSON {"mutations":[{"name","file","find","replace","must_mention"?}]}; find must occur exactly once.
--auto  : neutralise one line at a time (same-indent `pass`) for every line of the given Python file that
          matches --pattern (default: append((, assert, raise, sys.exit(1), return 1); a mutation that leaves
          the self-test green is reported as UNCOVERED — the line is decorative or the self-test has no
          sample for it. A mutation that produces a traceback is reported as CRASH (not a detection).
Exit: 0 every mutation caught and control green · 1 otherwise · 2 self-test failed / usage error / zero mutations
(a matrix that broke nothing proves nothing, so it is never green).
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

DEFAULT_PATTERN = r"\.append\(\(|\bassert\b|\braise\b|sys\.exit\(1\)|\breturn 1\b"


def run(cmd, cwd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def sandbox(root):
    tmp = tempfile.mkdtemp(prefix="breakcheck_")
    dst = os.path.join(tmp, "root")
    shutil.copytree(root, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
    return tmp, dst


def apply_mutation(dst, m):
    p = os.path.join(dst, m["file"])
    s = open(p, encoding="utf-8").read()
    n = s.count(m["find"])
    if n != 1:
        raise ValueError(f"anchor occurs {n} times (need exactly 1): {m['find']!r}")
    open(p, "w", encoding="utf-8").write(s.replace(m["find"], m["replace"], 1))


def auto_mutations(root, rel, pattern):
    lines = open(os.path.join(root, rel), encoding="utf-8").read().split("\n")
    rx, out = re.compile(pattern), []
    for i, line in enumerate(lines):
        st = line.strip()
        if not st or st.startswith("#") or not rx.search(line):
            continue
        indent = line[: len(line) - len(line.lstrip())]
        out.append({"name": f"L{i + 1}: {st[:60]}", "line": i, "file": rel, "indent": indent})
    return out


def apply_auto(dst, m):
    p = os.path.join(dst, m["file"])
    lines = open(p, encoding="utf-8").read().split("\n")
    lines[m["line"]] = m["indent"] + "pass  # breakcheck neutralised"
    open(p, "w", encoding="utf-8").write("\n".join(lines))


def judge(rc_control, rc, out, must_mention):
    if rc_control != 0:
        return "CONTROL-RED"
    if "Traceback" in out or "SyntaxError" in out or "IndentationError" in out:
        return "CRASH"
    if rc == 0:
        return "UNCOVERED"
    if must_mention and must_mention not in out:
        return "RED-ELSEWHERE"
    return "CAUGHT"


def matrix(root, cmd, mutations, auto=False):
    tmp, dst = sandbox(root)
    rc0, out0 = run(cmd, dst)
    rows = [("control (no mutation)", "green" if rc0 == 0 else "RED", "ok" if rc0 == 0 else "CONTROL-RED")]
    for m in mutations:
        shutil.rmtree(dst); shutil.copytree(root, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"))
        try:
            (apply_auto if auto else apply_mutation)(dst, m)
        except ValueError as e:
            rows.append((m["name"], "-", f"BAD-ANCHOR {e}")); continue
        rc, out = run(cmd, dst)
        rows.append((m["name"], "red" if rc else "green", judge(rc0, rc, out, m.get("must_mention"))))
    shutil.rmtree(tmp, ignore_errors=True)
    return rows


def report(rows):
    if len(rows) <= 1:                                   # only the control ran: nothing was broken, so nothing is proven
        print(f"  {'✔' if rows and rows[0][2] == 'ok' else '✘'} control only")
        print("✘ 0 mutations — nothing was broken, so this proves nothing. With --auto, pass --pattern for this file's "
              "style (e.g. 'print\\(\"FAIL|findings\\.append\\(') or write the mutations with --spec.")
        return 2
    bad = [r for r in rows if r[2] not in ("ok", "CAUGHT")]
    w = max(len(r[0]) for r in rows)
    for name, colour, verdict in rows:
        mark = "✔" if verdict in ("ok", "CAUGHT") else "✘"
        print(f"  {mark} {name.ljust(w)}  {colour:<6} {verdict}")
    print(f"{'✔' if not bad else '✘'} {len(rows) - 1} mutations, {len(bad)} problems"
          + ("" if not bad else " — UNCOVERED = decorative check or missing sample; CRASH = mutation invalid, not a detection"))
    return 0 if not bad else 1


# ── self-test: a tiny checker whose rule B has no self-test sample ────────────────────────────────
CHECKER = '''import sys
def check(s):
    out = []
    if "AAA" in s:
        out.append(("A", "rule A"))
    if "BBB" in s:
        out.append(("B", "rule B"))
    return out
def selftest():
    ok = check("xxAAAxx") == [("A", "rule A")] and check("clean") == []
    print("selftest ok" if ok else "FAIL: rule A sample not caught")
    return 0 if ok else 1
if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 0)
'''


def selftest():
    tmp = tempfile.mkdtemp(prefix="breakcheck_self_")
    open(os.path.join(tmp, "checker.py"), "w").write(CHECKER)
    cmd, lines, ok = f"{sys.executable} checker.py --selftest", [], True

    def chk(cond, label):
        nonlocal ok
        ok &= bool(cond); lines.append(f"  {'✔' if cond else '✘'} {label}")

    rows = matrix(tmp, cmd, auto_mutations(tmp, "checker.py", r"\.append\(\("), auto=True)
    verdicts = {r[0].split(":")[0]: r[2] for r in rows}
    chk(rows[0][2] == "ok", "control run is green")
    chk(verdicts.get("L5") == "CAUGHT", f"auto: neutralising rule A's append is CAUGHT ({verdicts.get('L5')})")
    chk(verdicts.get("L7") == "UNCOVERED", f"auto: neutralising rule B's append is UNCOVERED ({verdicts.get('L7')})")
    spec = [{"name": "flip rule A", "file": "checker.py", "find": 'if "AAA" in s:', "replace": "if False:", "must_mention": "rule A"},
            {"name": "syntax error", "file": "checker.py", "find": "def check(s):", "replace": "def check(s:"},
            {"name": "wrong anchor", "file": "checker.py", "find": "NOPE", "replace": "x"},
            {"name": "red elsewhere", "file": "checker.py", "find": 'if "AAA" in s:', "replace": "if False:", "must_mention": "rule Z"}]
    rows = matrix(tmp, cmd, spec)
    v = {r[0]: r[2] for r in rows}
    chk(v["flip rule A"] == "CAUGHT", f"spec: flipping rule A is CAUGHT and names 'rule A' ({v['flip rule A']})")
    chk(v["syntax error"] == "CRASH", f"spec: a syntax error is CRASH, not a detection ({v['syntax error']})")
    chk(v["wrong anchor"].startswith("BAD-ANCHOR"), f"spec: a missing anchor is refused ({v['wrong anchor'][:10]})")
    chk(v["red elsewhere"] == "RED-ELSEWHERE", f"spec: red on the wrong assertion is RED-ELSEWHERE ({v['red elsewhere']})")
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()) as quiet:
        zero = report(matrix(tmp, cmd, auto_mutations(tmp, "checker.py", r"NO_LINE_MATCHES_THIS"), auto=True))
    chk(zero == 2 and "proves nothing" in quiet.getvalue(), f"zero candidate lines is exit 2 'proves nothing', never a green 0 mutations ({zero})")
    rows = matrix(tmp, f"{sys.executable} -c 'import sys; sys.exit(1)'", spec[:1])
    chk(rows[0][2] == "CONTROL-RED" and rows[1][2] == "CONTROL-RED", "an always-red command is reported as CONTROL-RED, never as caught")
    shutil.rmtree(tmp, ignore_errors=True)
    return ok, lines


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--root"); ap.add_argument("--cmd"); ap.add_argument("--spec"); ap.add_argument("--auto")
    ap.add_argument("--pattern", default=DEFAULT_PATTERN); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    ok, lines = selftest()
    if a.selftest or not ok:
        print(f"breakcheck selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — results would not be trustworthy"); return 2
        if a.selftest:
            return 0
    if a.help or not (a.root and a.cmd and (a.spec or a.auto)):
        print(__doc__); return 2
    root = os.path.abspath(a.root)
    if a.auto:
        muts = auto_mutations(root, a.auto, a.pattern)
        print(f"auto mode: {len(muts)} candidate lines in {a.auto} matching /{a.pattern}/")
        return report(matrix(root, a.cmd, muts, auto=True))
    muts = json.load(open(a.spec))["mutations"]
    return report(matrix(root, a.cmd, muts))


if __name__ == "__main__":
    sys.exit(main())

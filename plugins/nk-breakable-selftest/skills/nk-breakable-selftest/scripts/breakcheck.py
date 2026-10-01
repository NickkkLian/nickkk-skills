#!/usr/bin/env python3
"""breakcheck.py — prove that a self-test goes red when the code it guards is broken.

    python3 breakcheck.py --root <dir> --cmd "python3 checker.py --selftest" --spec mutations.json
    python3 breakcheck.py --root <dir> --cmd "python3 checker.py --selftest" --auto checker.py [--pattern REGEX]
    python3 breakcheck.py --demo        # the same matrix on a bundled 12-line checker whose rule B has no sample
    python3 breakcheck.py --selftest

The target directory is copied to a temporary sandbox; only the copy is mutated. For every mutation four
things must hold (a "break matrix"):
  1. the mutated run exits non-zero              2. the unmutated control run exits zero
  3. the red is not a crash (no traceback)       4. if must_mention is set, a failure line names that assertion
--spec  : JSON {"mutations":[{"name","file","find","replace","must_mention"?}]}; find must occur exactly once.
--auto  : neutralise one line at a time (same-indent `pass`) for every line of the given Python file that
          matches --pattern (default: append((, assert, raise, sys.exit(1), return 1); a mutation that leaves
          the self-test green is reported as UNCOVERED — the line is decorative or the self-test has no
          sample for it. A mutation that produces a traceback is reported as CRASH (not a detection).
          Lines inside a docstring are skipped: they are text, not code.
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


def docstring_lines(src):
    """0-based numbers of the lines that sit inside a docstring (a module, class or function's first string). Until
    0.1.2 a docstring line that mentioned `raise` or `return 1` was neutralised like code and reported as UNCOVERED."""
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                out.update(range(first.lineno - 1, first.end_lineno))
    return out


def auto_mutations(root, rel, pattern):
    src = open(os.path.join(root, rel), encoding="utf-8").read()
    lines = src.split("\n")
    rx, out, doc = re.compile(pattern), [], docstring_lines(src) if rel.endswith(".py") else set()
    for i, line in enumerate(lines):
        st = line.strip()
        if not st or st.startswith("#") or i in doc or not rx.search(line):
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
    if must_mention and not any(
        must_mention in line and re.match(r"^\s*(?:[✘✗×]|(?:FAIL|FAILED|FAILURE|ERROR)\b)", line, re.IGNORECASE)
        for line in out.splitlines()
    ):
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
    n = len(rows) - 1
    print(f"{'✔' if not bad else '✘'} {n} mutation{'' if n == 1 else 's'}, {len(bad)} problem{'' if len(bad) == 1 else 's'}"
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


MIXED_CHECKER = CHECKER.split("def selftest():")[0] + '''def selftest():
    a = check("xxAAAxx") == [("A", "rule A")]
    b = check("xxBBBxx") == [("B", "rule B")]
    print("  ✔ rule A sample caught" if a else "  ✘ rule A sample not caught")
    print("  ✔ rule B sample caught" if b else "  ✘ rule B sample not caught")
    return 0 if a and b else 1
if __name__ == "__main__":
    sys.exit(selftest())
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
    got = lambda name: v.get(name, "no row")             # a missing row fails its check instead of crashing the self-test
    chk(got("flip rule A") == "CAUGHT", f"spec: flipping rule A is CAUGHT and names 'rule A' ({got('flip rule A')})")
    chk(got("syntax error") == "CRASH", f"spec: a syntax error is CRASH, not a detection ({got('syntax error')})")
    chk(got("wrong anchor").startswith("BAD-ANCHOR"), f"spec: a missing anchor is refused ({got('wrong anchor')[:10]})")
    chk(got("red elsewhere") == "RED-ELSEWHERE", f"spec: red on the wrong assertion is RED-ELSEWHERE ({got('red elsewhere')})")
    word = "rai" + "se"                                  # kept apart so that this line is not a candidate itself
    doc_checker = CHECKER.replace("def check(s):\n", f'def check(s):\n    """Collects findings; callers {word} on any."""\n')
    open(os.path.join(tmp, "doc.py"), "w").write(doc_checker)
    names = [m["name"] for m in auto_mutations(tmp, "doc.py", DEFAULT_PATTERN)]
    chk(len(names) == 2 and not any("Collects" in n for n in names), f"auto: a docstring line that matches the pattern is not a candidate ({len(names)} candidates)")
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()) as quiet:
        zero = report(matrix(tmp, cmd, auto_mutations(tmp, "checker.py", r"NO_LINE_MATCHES_THIS"), auto=True))
    chk(zero == 2 and "proves nothing" in quiet.getvalue(), f"zero candidate lines is exit 2 'proves nothing', never a green 0 mutations ({zero})")
    rows = matrix(tmp, f"{sys.executable} -c 'import sys; sys.exit(1)'", spec[:1])
    chk([r[2] for r in rows] == ["CONTROL-RED", "CONTROL-RED"], "an always-red command is reported as CONTROL-RED, never as caught")
    open(os.path.join(tmp, "checker.py"), "w").write(MIXED_CHECKER)
    rows = matrix(tmp, cmd, [{"name": "passing name only", "file": "checker.py", "find": 'if "BBB" in s:',
                              "replace": "if False:", "must_mention": "rule A"}])
    chk([r[2] for r in rows] == ["ok", "RED-ELSEWHERE"],
        f"spec: must_mention only on a passing line is RED-ELSEWHERE ({[r[2] for r in rows]})")
    for prefix in ("✘", "✗", "×", "FAIL", "FAILED:", "failure", "eRrOr:"):
        chk(judge(0, 1, f"  {prefix} rule A", "rule A") == "CAUGHT", f"failure prefix {prefix} names the assertion")
    for output in ("  ✔ rule A", "rule A", "  FAILEDLY rule A", "note: FAIL rule A", ""):
        chk(judge(0, 1, output, "rule A") == "RED-ELSEWHERE", f"no failure line cannot satisfy must_mention ({output!r})")
    shutil.rmtree(tmp, ignore_errors=True)
    return ok, lines


def demo():
    """The matrix on the bundled example: a checker with two rules and a self-test that has a sample for rule A only."""
    tmp = tempfile.mkdtemp(prefix="breakcheck_demo_")
    open(os.path.join(tmp, "checker.py"), "w").write(CHECKER)
    print("demo: a 12-line checker with rule A and rule B; its self-test has a sample for rule A only\n"
          "$ python3 checker.py --selftest   →  selftest ok (exit 0)\n"
          "$ breakcheck.py --root . --cmd \"python3 checker.py --selftest\" --auto checker.py --pattern '\\.append\\(\\('")
    code = report(matrix(tmp, f"{sys.executable} checker.py --selftest", auto_mutations(tmp, "checker.py", r"\.append\(\("), auto=True))
    shutil.rmtree(tmp, ignore_errors=True)
    return code


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--root"); ap.add_argument("--cmd"); ap.add_argument("--spec"); ap.add_argument("--auto")
    ap.add_argument("--pattern", default=DEFAULT_PATTERN); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--demo", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    ok, lines = selftest()
    if a.selftest or not ok:
        print(f"breakcheck selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — results would not be trustworthy"); return 2
        if a.selftest:
            return 0
    if a.demo:
        return demo()
    if a.help or not (a.root and a.cmd and (a.spec or a.auto)):
        print(__doc__); return 2
    root = os.path.abspath(a.root)
    if a.auto:
        muts = auto_mutations(root, a.auto, a.pattern)
        print(f"auto mode: {len(muts)} candidate line{'' if len(muts) == 1 else 's'} in {a.auto} matching /{a.pattern}/")
        return report(matrix(root, a.cmd, muts, auto=True))
    muts = json.load(open(a.spec))["mutations"]
    return report(matrix(root, a.cmd, muts))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""rules_check.py — audit a rules file (CLAUDE.md, AGENTS.md, a team playbook): does every rule name its incident,
and is it enforced by something that exists and runs?

    python3 rules_check.py <rules.md> [--base DIR] [--run] [--json OUT]
    python3 rules_check.py --selftest

A rule is a list item or paragraph that contains a directive (must / never / always / do not / don't / forbidden /
required / prohibited / refuse), or one of their Chinese equivalents (references/rule-format.md lists them). Inside
the same block the script looks for two tags:
  incident:   (or why:)          — the dated event that made the rule necessary
  enforced by:  (or gate: / hook: / check:) — a path (relative to --base, default: the rules file's directory) or a command
Findings:
  NO-INCIDENT    the rule cites no event; rules for imagined risks produce false positives and get clicked through
  NO-ENFORCEMENT the rule relies on being remembered; a prohibition alone does not change a default action
  MISSING-TARGET enforced by a path that does not exist
  FAILED-RUN     (--run) the enforcement command exited non-zero
  OVERFIT        more than 12 directives in one file: every added constraint shrinks what the reader is allowed to do
Exit: 0 clean · 1 findings · 2 selftest failed / usage.
"""
import json, os, re, shlex, subprocess, sys, tempfile

DIRECTIVE = re.compile(r"\b(must|never|always|do not|don't|forbidden|required|prohibited|refuse)\b|必须|不许|禁止|一律|绝不|不得", re.I)
INCIDENT = re.compile(r"(?i)\b(incident|why)\s*:")
ENFORCED = re.compile(r"(?i)\b(enforced by|gate|hook|check)\s*:\s*`?([^`\n]+?)`?\s*$", re.M)
OVERFIT_AT = 12


def blocks(md):
    """Split into rule blocks: list items (with their indented continuation lines) and paragraphs."""
    out, cur, start = [], [], 0
    for i, line in enumerate(md.split("\n"), 1):
        is_item = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", line)
        if (is_item or not line.strip()) and cur:
            out.append((start, "\n".join(cur))); cur = []
        if line.strip():
            if not cur:
                start = i
            cur.append(line)
    if cur:
        out.append((start, "\n".join(cur)))
    return out


def audit(path, base=None, run=False):
    md = open(path, encoding="utf-8").read()
    base = base or os.path.dirname(os.path.abspath(path))
    rules, findings = [], []
    for line_no, block in blocks(md):
        if not DIRECTIVE.search(block) or block.lstrip().startswith("#"):
            continue
        title = block.strip().split("\n")[0][:80]
        has_inc = bool(INCIDENT.search(block))
        m = ENFORCED.search(block)
        target = m.group(2).strip() if m else None
        rules.append({"line": line_no, "rule": title, "incident": has_inc, "enforced_by": target})
        if not has_inc:
            findings.append(("NO-INCIDENT", line_no, title))
        if not target:
            findings.append(("NO-ENFORCEMENT", line_no, title)); continue
        tokens = shlex.split(target)
        first, rest = tokens[0], tokens[1:]
        cand = os.path.expanduser(first) if os.path.isabs(os.path.expanduser(first)) else os.path.join(base, first)
        is_path = "/" in first or first.endswith((".py", ".sh", ".zsh", ".mjs", ".js", ".json", ".md"))
        if is_path and not os.path.exists(cand):
            findings.append(("MISSING-TARGET", line_no, f"{title}  → {first}"))
        elif run:
            interp = {".py": "python3", ".sh": "bash", ".zsh": "zsh", ".mjs": "node", ".js": "node"}.get(os.path.splitext(first)[1])
            argv = ([interp] if interp else []) + [cand if is_path else first] + rest
            try:
                r = subprocess.run(argv, cwd=base, capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    findings.append(("FAILED-RUN", line_no, f"{title}  → exit {r.returncode}: {(r.stderr or r.stdout).strip()[:80]}"))
            except (subprocess.TimeoutExpired, OSError) as e:
                findings.append(("FAILED-RUN", line_no, f"{title}  → {type(e).__name__}"))
    if len(rules) > OVERFIT_AT:
        findings.append(("OVERFIT", 0, f"{len(rules)} directives in one file; retract before adding"))
    return rules, findings


GOOD = """# Rules
- Never push with --force. Incident: 2026-08-05 a shared branch was rewritten. Enforced by: check.py --selftest
- Always run the gate before publishing.
  Why: 2026-07-30 a page went public unasked.
  Enforced by: gate.py
"""


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "check.py"), "w").write("import sys; sys.exit(0 if '--selftest' in sys.argv else 1)\n")
        open(os.path.join(d, "gate.py"), "w").write("import sys; sys.exit(0)\n")
        p = os.path.join(d, "RULES.md"); open(p, "w").write(GOOD)
        rules, f = audit(p)
        chk(len(rules) == 2 and not f, f"control: 2 annotated rules, 0 findings (got {len(rules)} rules, {f})")
        rules, f = audit(p, run=True)
        chk(not f, f"control --run: both enforcement commands exit 0 ({f})")
        open(p, "w").write(GOOD + "- You must not delete data files without a backup.\n")
        _, f = audit(p)
        chk({x[0] for x in f} == {"NO-INCIDENT", "NO-ENFORCEMENT"} and all(x[1] == 6 for x in f), f"a bare rule is NO-INCIDENT + NO-ENFORCEMENT at line 6 ({f})")
        open(p, "w").write(GOOD + "- Never commit secrets. Incident: 2026-06-01 key leaked. Enforced by: scan.py\n")
        _, f = audit(p)
        chk(f == [("MISSING-TARGET", 6, "- Never commit secrets. Incident: 2026-06-01 key leaked. Enforced by: scan.py  → scan.py")], f"a missing enforcement path is MISSING-TARGET ({f})")
        open(p, "w").write(GOOD + "- Never skip tests. Incident: 2026-06-02. Enforced by: check.py\n")
        _, f = audit(p, run=True)
        chk(len(f) == 1 and f[0][0] == "FAILED-RUN", f"--run: an enforcement command that exits 1 is FAILED-RUN ({f})")
        open(p, "w").write("# R\n" + "".join(f"- Rule {i}: you must do thing {i}. Incident: x. Enforced by: gate.py\n" for i in range(13)))
        _, f = audit(p)
        chk(f == [("OVERFIT", 0, "13 directives in one file; retract before adding")], f"13 directives → OVERFIT ({f})")
        open(p, "w").write("# Notes\n- The build takes about a minute.\n- See the README for details.\n")
        rules, f = audit(p)
        chk(not rules and not f, "non-directive text is not a rule")
    return ok, lines


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__); return 2
    ok, lines = selftest()
    if "--selftest" in argv or not ok:
        print(f"rules_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    files = [a for a in argv if not a.startswith("--") and (argv.index(a) == 0 or argv[argv.index(a) - 1] not in ("--base", "--json"))]
    if not files:
        print(__doc__); return 2
    base = argv[argv.index("--base") + 1] if "--base" in argv else None
    out = argv[argv.index("--json") + 1] if "--json" in argv else None
    rules, findings = audit(files[0], base, "--run" in argv)
    kinds = {k: sum(1 for f in findings if f[0] == k) for k in ("NO-INCIDENT", "NO-ENFORCEMENT", "MISSING-TARGET", "FAILED-RUN", "OVERFIT")}
    print(f"{files[0]}: {len(rules)} directives · " + " · ".join(f"{k} {v}" for k, v in kinds.items() if v))
    for kind, line, text in findings:
        print(f"  {kind:<15} L{line:<4} {text}")
    if out:
        json.dump({"rules": rules, "findings": findings}, open(out, "w"), indent=1, ensure_ascii=False)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

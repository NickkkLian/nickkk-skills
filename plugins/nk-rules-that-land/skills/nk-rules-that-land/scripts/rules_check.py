#!/usr/bin/env python3
"""rules_check.py — audit a rules file (CLAUDE.md, AGENTS.md, a team playbook): does every rule say why (its incident,
when there is one), and is it enforced by something that exists and runs?

    python3 rules_check.py <rules.md> [--base DIR] [--run] [--json OUT] [--why-tags a,b] [--enforced-tags a,b]
    python3 rules_check.py --selftest

It checks one convention and nothing else: it cannot tell a good rule from a bad one. On a rules file that does not use
the two tags below, every rule is listed; read that list as "these rely on being remembered", not as a verdict on the
file. If your file already marks reasons or enforcement with other words (Because:, Reason:, CI:, Test:), pass them with
--why-tags / --enforced-tags and they count too.

A rule is a list item or paragraph that contains a directive (must / never / always / do not / don't / forbidden /
required / prohibited / refuse), or one of their Chinese equivalents (references/rule-format.md lists them). Inside
the same block the script looks for two tags:
  incident:   (or why:)          — the event that made the rule necessary, or what breaks without it (a date is optional)
  enforced by:  (or gate: / hook: / check:) — a path (relative to --base, default: the rules file's directory) or a command
Findings:
  NO-INCIDENT    the rule gives no reason; rules for imagined risks produce false positives and get clicked through
  NO-ENFORCEMENT the rule relies on being remembered; a prohibition alone does not change a default action
  MISSING-TARGET enforced by a path that does not exist
  FAILED-RUN     (--run) the enforcement command exited non-zero
  OVERFIT        more than 12 directives in one file: every added constraint shrinks what the reader is allowed to do
Exit: 0 clean · 1 findings · 2 selftest failed / usage.
"""
import json, os, re, shlex, subprocess, sys, tempfile

DIRECTIVE = re.compile(r"\b(must|never|always|do not|don't|forbidden|required|prohibited|refuse)\b|必须|不许|禁止|一律|绝不|不得", re.I)
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


def tag_rx(words, tail):
    return re.compile(r"(?i)\b(" + "|".join(re.escape(w.strip()) for w in words if w.strip()) + r")\s*:" + tail, re.M)


def audit(path, base=None, run=False, why_tags=(), enforced_tags=()):
    """why_tags / enforced_tags: extra words accepted in front of the colon, next to the built-in ones."""
    INCIDENT = tag_rx(["incident", "why", *why_tags], "")
    ENFORCED = tag_rx(["enforced by", "gate", "hook", "check", *enforced_tags], r"\s*`?([^`\n]+?)`?\s*$")
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
            findings.append(("NO-ENFORCEMENT", line_no, title))
        if not target:
            continue
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
        open(p, "w").write(GOOD + "- Never edit the lock file by hand. Why: the next install rewrites it. Enforced by: gate.py\n")
        rules, f = audit(p)
        chk(len(rules) == 3 and not f, f"a reason with no date is enough: Why: without a date is not NO-INCIDENT ({f})")
        open(p, "w").write("# Notes\n- The build takes about a minute.\n- See the README for details.\n")
        rules, f = audit(p)
        chk(not rules and not f, "non-directive text is not a rule")
        open(p, "w").write("# R\n- Fine print.\n- You must keep backups.")          # no newline at the end of the file
        rules, f = audit(p)
        chk(len(rules) == 1 and {x[0] for x in f} == {"NO-INCIDENT", "NO-ENFORCEMENT"}, f"the last rule of a file with no final newline is still read ({f})")
        open(p, "w").write(GOOD + "- Never skip review. Why: a bad merge. Enforced by: no-such-command-xyz --now\n")
        _, f = audit(p, run=True)
        chk(len(f) == 1 and f[0][0] == "FAILED-RUN" and "Error" in f[0][2], f"--run: an enforcement command that cannot start is FAILED-RUN ({f})")
        open(p, "w").write("# R\n- Never push on Friday. Because: the 2026-05 outage. CI: gate.py\n")
        _, f = audit(p)
        _, f2 = audit(p, why_tags=["because"], enforced_tags=["ci"])
        chk({x[0] for x in f} == {"NO-INCIDENT", "NO-ENFORCEMENT"} and not f2, f"--why-tags / --enforced-tags make a file's own words count ({f} → {f2})")
        open(p, "w").write(GOOD); said = []
        chk(report(p, out=said.append) == 0 and said and "2 directives" in said[0], "the command exits 0 on a file with no findings")
        open(p, "w").write("# R\n- Always use tabs.\n- Never use npm.\n"); said = []
        chk(report(p, out=said.append) == 1 and any("None of the 2 rules" in x for x in said) and sum("NO-ENFORCEMENT" in x for x in said) == 3,
            "the command exits 1 on findings, and says so when a file does not use the tags at all")
    return ok, lines


def report(path, base=None, run=False, out_json=None, why_tags=(), enforced_tags=(), out=print):
    """Print the audit and return the exit code: 1 when there are findings, else 0."""
    rules, findings = audit(path, base, run, why_tags, enforced_tags)
    kinds = {k: sum(1 for f in findings if f[0] == k) for k in ("NO-INCIDENT", "NO-ENFORCEMENT", "MISSING-TARGET", "FAILED-RUN", "OVERFIT")}
    out(f"{path}: {len(rules)} directive{'' if len(rules) == 1 else 's'} · " + (" · ".join(f"{k} {v}" for k, v in kinds.items() if v) or "0 findings"))
    if rules and not any(r["incident"] or r["enforced_by"] for r in rules):
        out(f"  None of the {len(rules)} rules carries a why-tag or an enforced-by tag: this file does not use the convention this "
            "script checks. The list below is every rule that relies on being remembered, not a verdict on the file.")
    for kind, line, text in findings:
        out(f"  {kind:<15} L{line:<4} {text}")
    if out_json:
        json.dump({"rules": rules, "findings": findings}, open(out_json, "w"), indent=1, ensure_ascii=False)
    return 1 if findings else 0


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__); return 2
    ok, lines = selftest()
    if "--selftest" in argv or not ok:
        print(f"rules_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    valued = ("--base", "--json", "--why-tags", "--enforced-tags")
    files = [a for a in argv if not a.startswith("--") and (argv.index(a) == 0 or argv[argv.index(a) - 1] not in valued)]
    if not files:
        print(__doc__); return 2
    opt = lambda k: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else None
    tags = lambda k: [w for w in (opt(k) or "").split(",") if w.strip()]
    return report(files[0], opt("--base"), "--run" in argv, opt("--json"), tags("--why-tags"), tags("--enforced-tags"))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

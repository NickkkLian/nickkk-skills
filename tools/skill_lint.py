#!/usr/bin/env python3
"""skill_lint.py — structural gate for an agent skill folder (run before publish_gate.py).

    python3 skill_lint.py <skill-dir> [<skill-dir> ...]
    python3 skill_lint.py --selftest

Exit: 0 clean · 1 findings · 2 selftest failed / usage error (fail-loud: no results are printed if the
selftest fails). The selftest and the real run share check_skill(); each rule has a sample that only it
catches, plus a clean control sample that must produce zero findings.

Rules:
  L01 SKILL.md exists                         L02 frontmatter parses; unknown keys -> W01 (warning only)
  L03 name == dir name, kebab-case, <= 64     L04 description 1..1024 chars and says when to use it
  L05 body <= 500 lines                        L06 a '## Provenance' section exists
  L07 scripts referenced via ${CLAUDE_SKILL_DIR}, referenced scripts exist, shipped scripts are referenced
  L08 every shipped script supports --selftest L09 no post-kit/ inside the skill dir (launch drafts do not ship)
  L10 license field present                    L11 no local absolute paths (macOS/Linux home dirs, a home Desktop, Windows user dirs)
  L12 a skill that uses ${CLAUDE_SKILL_DIR} carries a path note for other agents (the placeholder written as
      ${…SKILL_DIR}, telling them to put in the skill folder's absolute path), placed before the first use —
      Codex, Cursor and Gemini CLI do not fill the variable in
"""
import os, re, sys, tempfile, shutil

ALLOWED_KEYS = {"name", "description", "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
                "user-invocable", "allowed-tools", "disallowed-tools", "model", "effort", "context", "agent",
                "background", "hooks", "paths", "shell", "metadata", "license", "compatibility", "version"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# written with \x2f / \x5c escapes so the lint does not flag its own source (a checker must scan itself clean)
PRIVATE_RE = re.compile(r"\x2fUsers\x2f|~\x2fDesktop|[A-Za-z]:\x5cUsers\x5c")
SCRIPT_EXT = (".py", ".sh", ".mjs", ".js", ".zsh")


def parse_frontmatter(text):
    """Tiny YAML subset: top-level key: value, folded '>' / '|' scalars, one-level nested maps."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, text
    fm, i, block = {}, 1, lines[1:end]
    i = 0
    while i < len(block):
        line = block[i]
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in ("", ">", "|", ">-", "|-"):
            sub, j = [], i + 1
            while j < len(block) and (block[j].startswith("  ") or block[j].strip() == ""):
                sub.append(block[j])
                j += 1
            if any(re.match(r"^\s+[\w-]+:\s", s) for s in sub):
                fm[key] = {re.match(r"^\s+([\w-]+):\s*(.*)$", s).group(1): re.match(r"^\s+([\w-]+):\s*(.*)$", s).group(2).strip().strip('"\'')
                           for s in sub if re.match(r"^\s+[\w-]+:\s", s)}
            else:
                fm[key] = " ".join(s.strip() for s in sub if s.strip())
            i = j
        else:
            fm[key] = val.strip().strip('"\'')
            i += 1
    return fm, "\n".join(lines[end + 1:])


def check_skill(d):
    out, d = [], os.path.abspath(d)
    name_dir = os.path.basename(d)
    sk = os.path.join(d, "SKILL.md")
    if not os.path.isfile(sk):
        return [("L01", "SKILL.md missing")]
    text = open(sk, encoding="utf-8").read()
    fm, body = parse_frontmatter(text)
    if fm is None:
        return [("L02", "frontmatter missing or unterminated")]
    for k in fm:
        if k not in ALLOWED_KEYS:
            out.append(("W01", f"unknown frontmatter key: {k}"))
    name = fm.get("name", "")
    if not name or name != name_dir or not NAME_RE.match(name) or len(name) > 64:
        out.append(("L03", f"name {name!r} must equal dir {name_dir!r}, kebab-case, <=64"))
    desc = fm.get("description", "") if isinstance(fm.get("description"), str) else ""
    if not (1 <= len(desc) <= 1024) or "when" not in desc.lower():
        out.append(("L04", f"description must be 1..1024 chars and say when to use it (len={len(desc)})"))
    if len(body.split("\n")) > 500:
        out.append(("L05", f"body has {len(body.splitlines())} lines (> 500)"))
    if not re.search(r"^## Provenance", body, re.M):
        out.append(("L06", "no '## Provenance' section"))
    scripts_dir = os.path.join(d, "scripts")
    shipped = sorted(f for f in os.listdir(scripts_dir) if f.endswith(SCRIPT_EXT)) if os.path.isdir(scripts_dir) else []
    refs = re.findall(r"\$\{CLAUDE_SKILL_DIR\}/scripts/([\w.\-]+)", body)
    bare = re.findall(r"(?<![\w/${}])scripts/([\w.\-]+\.(?:py|sh|mjs|js|zsh))", body)
    for f in set(refs):
        if f not in shipped:
            out.append(("L07", f"referenced script not shipped: scripts/{f}"))
    for f in set(bare) - set(refs):
        out.append(("L07", f"script referenced without ${{CLAUDE_SKILL_DIR}}: scripts/{f}"))
    for f in shipped:
        if f not in refs:
            out.append(("L07", f"shipped script never referenced from SKILL.md: scripts/{f}"))
        if "--selftest" not in open(os.path.join(scripts_dir, f), encoding="utf-8", errors="replace").read():
            out.append(("L08", f"script lacks --selftest: scripts/{f}"))
    if os.path.isdir(os.path.join(d, "post-kit")):
        out.append(("L09", "post-kit/ must not ship inside the skill dir"))
    if not fm.get("license"):
        out.append(("L10", "license field missing"))
    first_use = body.find("${CLAUDE_SKILL_DIR}")
    if first_use >= 0:
        note = body.find("${…SKILL_DIR}")
        if note < 0 or "absolute path" not in body[note:note + 600]:
            out.append(("L12", "uses ${CLAUDE_SKILL_DIR} but has no path note for other agents (${…SKILL_DIR} … absolute path)"))
        elif note > first_use:
            out.append(("L12", "the path note for other agents comes after the first ${CLAUDE_SKILL_DIR} use"))
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            try:
                s = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            if PRIVATE_RE.search(s):
                out.append(("L11", f"local absolute path in {os.path.relpath(p, d)}"))
    return out


# ── selftest: one sample per rule, each must trip exactly that rule; clean control must be empty ──
CLEAN_FM = ('---\nname: {n}\ndescription: Checks X. Use when you need Y and not when Z.\nlicense: MIT\n'
            'metadata:\n  provenance: own practice\n---\n')
PATH_NOTE = '> **Paths.** Commands start with `${…SKILL_DIR}`, this skill\'s folder. If your agent shows it as written, put in that folder\'s absolute path.\n\n'
CLEAN_BODY = '# T\n\n' + PATH_NOTE + 'Run `python3 ${CLAUDE_SKILL_DIR}/scripts/tool.py --selftest`.\n\n## Provenance\n\nown practice.\n'
CLEAN_SCRIPT = '#!/usr/bin/env python3\nimport sys\nif "--selftest" in sys.argv: print("ok")\n'


def _mk(tmp, name, fm=None, body=None, script=CLEAN_SCRIPT, extra=None):
    d = os.path.join(tmp, name)
    os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
    open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8").write((fm if fm is not None else CLEAN_FM.format(n=name)) + (body if body is not None else CLEAN_BODY))
    if script is not None:
        open(os.path.join(d, "scripts", "tool.py"), "w", encoding="utf-8").write(script)
    if extra:
        extra(d)
    return d


def selftest():
    ok, lines, tmp = True, [], tempfile.mkdtemp(prefix="skill_lint_")
    cases = [
        ("clean control -> no findings", _mk(tmp, "good-skill"), set()),
        ("L01 missing SKILL.md", _mk(tmp, "no-skill", extra=lambda d: os.remove(os.path.join(d, "SKILL.md"))), {"L01"}),
        ("L02 no frontmatter", _mk(tmp, "no-fm", fm="# nothing\n"), {"L02"}),
        ("L03 name != dir", _mk(tmp, "name-mismatch", fm=CLEAN_FM.format(n="other-name")), {"L03"}),
        ("L04 description without 'when'", _mk(tmp, "desc-bad", fm=CLEAN_FM.format(n="desc-bad").replace("Use when you need Y and not when Z", "Does Y")), {"L04"}),
        ("L05 body > 500 lines", _mk(tmp, "long-body", body=CLEAN_BODY + "x\n" * 501), {"L05"}),
        ("L06 no provenance", _mk(tmp, "no-prov", body=CLEAN_BODY.replace("## Provenance", "## Origin")), {"L06"}),
        # each L07 branch gets a sample that trips ONLY that branch (breakcheck --auto found two of them
        # uncovered on 2026-09-15: a bare reference to a shipped script also trips "never referenced")
        ("L07 referenced script not shipped", _mk(tmp, "ghost-ref", body=CLEAN_BODY.replace("--selftest`", "--selftest` and `${CLAUDE_SKILL_DIR}/scripts/ghost.py`")), {"L07"}),
        ("L07 script referenced without var", _mk(tmp, "bare-ref", body=CLEAN_BODY.replace("${CLAUDE_SKILL_DIR}/scripts/tool.py", "scripts/ghost.py"), script=None), {"L07"}),
        ("L07 shipped script unreferenced", _mk(tmp, "unref", extra=lambda d: open(os.path.join(d, "scripts", "extra.py"), "w").write(CLEAN_SCRIPT)), {"L07"}),
        ("L08 script lacks selftest", _mk(tmp, "no-selftest", script="print(1)\n"), {"L08"}),
        ("L09 post-kit inside", _mk(tmp, "has-kit", extra=lambda d: os.makedirs(os.path.join(d, "post-kit"))), {"L09"}),
        ("L10 no license", _mk(tmp, "no-license", fm=CLEAN_FM.format(n="no-license").replace("license: MIT\n", "")), {"L10"}),
        ("L11 private path", _mk(tmp, "priv-path", body=CLEAN_BODY + "\nsee \x2fUsers\x2fsomeone/x\n"), {"L11"}),
        ("L12 no path note for other agents", _mk(tmp, "no-note", body=CLEAN_BODY.replace(PATH_NOTE, "")), {"L12"}),
        ("L12 path note after the first use", _mk(tmp, "late-note", body=CLEAN_BODY.replace(PATH_NOTE, "").replace("## Provenance", PATH_NOTE + "## Provenance")), {"L12"}),
        ("W01 unknown key", _mk(tmp, "odd-key", fm=CLEAN_FM.format(n="odd-key").replace("license: MIT\n", "license: MIT\nfoo: bar\n")), {"W01"}),
    ]
    for label, d, want in cases:
        got = {c for c, _ in check_skill(d)}
        hit = got == want
        ok &= hit
        lines.append(f"  {'✔' if hit else '✘'} {label} (want {sorted(want)}, got {sorted(got)})")
    shutil.rmtree(tmp, ignore_errors=True)
    return ok, lines


def main(argv):
    ok, lines = selftest()
    if not ok or "--selftest" in argv:
        print(f"skill_lint selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed")
        print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — no results are trusted"); return 2
        return 0
    dirs = [a for a in argv if not a.startswith("-")]
    if not dirs:
        print(__doc__); return 2
    rc = 0
    for d in dirs:
        findings = check_skill(d)
        hard = [f for f in findings if not f[0].startswith("W")]
        rc |= 1 if hard else 0
        print(f"{'✘' if hard else '✔'} {d}: {len(hard)} findings, {len(findings) - len(hard)} warnings")
        for code, msg in findings:
            print(f"    {code}  {msg}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

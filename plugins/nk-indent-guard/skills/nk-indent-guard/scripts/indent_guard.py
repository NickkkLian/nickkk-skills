#!/usr/bin/env python3
"""indent_guard.py — refuse a data-file edit that re-indented the whole file and buried the real diff.

    python3 indent_guard.py [--ref HEAD] [--ext .json,.yaml,.yml] [paths...]
    python3 indent_guard.py --selftest

For every tracked file under the given paths (default: the repository) with a matching extension, the
indentation unit of the working copy is compared with the same file at --ref (default HEAD). A change of
unit (2 → 1, 4 → 2, spaces → tabs, pretty → single line) means the file was rewritten wholesale: the
validator is green, the counts are right, the content is right, and the diff went from 4 lines to 400 —
"what did this commit actually change" is gone for good. New files (no baseline) are listed, not judged.
Exit: 0 unchanged · 1 re-indented files found · 2 selftest failed / not a git repo.
"""
import os, re, subprocess, sys, tempfile

INDENT_LINE = re.compile(r"^([ \t]+)\S")


def indent_of(text, limit=200):
    """The indentation unit: whitespace of the first line that is indented deeper than the previous one.
    Returns e.g. '  ' (2 spaces), '\\t', or None (no indented line / single-line file)."""
    prev = 0
    for line in text.split("\n")[:limit]:
        m = INDENT_LINE.match(line)
        cur = len(m.group(1)) if m else 0
        if m and cur > prev:
            return m.group(1)[: cur - prev]
        if line.strip():
            prev = cur
    return None


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip())
    return r.stdout


def check(repo, ref="HEAD", exts=(".json", ".yaml", ".yml"), paths=()):
    files = git(repo, "ls-files", "-z", "--", *paths).decode("utf-8").split("\0")
    changed, new, same = [], [], 0
    for f in files:
        if not f or not f.lower().endswith(tuple(exts)):
            continue
        p = os.path.join(repo, f)
        if not os.path.isfile(p):
            continue
        now = indent_of(open(p, encoding="utf-8", errors="replace").read())
        try:
            was = indent_of(git(repo, "show", f"{ref}:{f}").decode("utf-8", "replace"))
        except RuntimeError:
            new.append(f); continue
        if was != now:
            changed.append((f, was, now))
        else:
            same += 1
    return changed, new, same


def show(u):
    return "none" if u is None else ("tab" if u == "\t" else f"{len(u)} spaces")


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    for text, want in [('{\n  "a": 1,\n  "b": [\n    2\n  ]\n}', "  "), ('{\n    "a": 1\n}', "    "), ('{\n\t"a": 1\n}', "\t"), ('{"a": 1}', None),
                       ('items:\n  - a\n  - b\nother:\n  x: 1\n', "  ")]:
        chk(indent_of(text) == want, f"indent_of → {show(want)}")
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        g = lambda *a: subprocess.run(["git", "-C", d, *a], check=True, capture_output=True, env=env)
        g("init", "-q"); os.makedirs(os.path.join(d, "data"))
        two = '{\n  "a": 1,\n  "b": {\n    "c": 2\n  }\n}\n'
        open(os.path.join(d, "data", "x.json"), "w").write(two); open(os.path.join(d, "data", "y.json"), "w").write(two)
        open(os.path.join(d, "notes.txt"), "w").write("  indented but not a data file\n")
        g("add", "."); g("commit", "-q", "-m", "base")
        changed, new, same = check(d)
        chk(not changed and not new and same == 2, f"control: untouched repo → 0 changed, 2 same (got {len(changed)}/{same})")
        open(os.path.join(d, "data", "x.json"), "w").write('{\n "a": 1,\n "b": {\n  "c": 3\n }\n}\n')   # indent=1 rewrite
        changed, new, same = check(d)
        chk(len(changed) == 1 and changed[0][0] == "data/x.json" and changed[0][1] == "  " and changed[0][2] == " ", "a 2→1 space rewrite is caught with the file named")
        open(os.path.join(d, "data", "x.json"), "w").write(two.replace('"c": 2', '"c": 3'))
        changed, _, _ = check(d)
        chk(not changed, "the same edit written back with the original indent passes")
        open(os.path.join(d, "data", "x.json"), "w").write('{"a": 1, "b": {"c": 3}}\n')
        changed, _, _ = check(d)
        chk(len(changed) == 1 and changed[0][2] is None, "pretty → single line is caught")
        open(os.path.join(d, "data", "x.json"), "w").write(two)
        open(os.path.join(d, "data", "z.json"), "w").write(two); g("add", "data/z.json")
        changed, new, _ = check(d)
        chk(not changed and new == ["data/z.json"], "a new file has no baseline: listed, not judged")
        changed, new, same = check(d, paths=("data/x.json",))
        chk(same == 1 and not changed, "path filter limits the check")
        open(os.path.join(d, "data", "x.json"), "w").write('{\n\t"a": 1,\n\t"b": {\n\t\t"c": 2\n\t}\n}\n')
        changed, _, _ = check(d)
        chk(len(changed) == 1 and changed[0][2] == "\t", "spaces → tabs is caught")
    return ok, lines


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__); return 2
    ok, lines = selftest()
    if "--selftest" in argv or not ok:
        print(f"indent_guard selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    ref, exts, paths, i = "HEAD", (".json", ".yaml", ".yml"), [], 0
    while i < len(argv):
        if argv[i] == "--ref":
            ref = argv[i + 1]; i += 2
        elif argv[i] == "--ext":
            exts = tuple(e if e.startswith(".") else "." + e for e in argv[i + 1].split(",")); i += 2
        else:
            paths.append(argv[i]); i += 1
    try:
        repo = git(".", "rev-parse", "--show-toplevel").decode().strip()
    except RuntimeError as e:
        print(f"not a git repository: {e}"); return 2
    changed, new, same = check(repo, ref, exts, tuple(paths))
    for f, was, now in changed:
        print(f"✘ {f}: {show(was)} → {show(now)}  (whole file re-indented; rewrite it with the original unit)")
    for f in new:
        print(f"· {f}: new file, no baseline at {ref}")
    print(f"{'✘' if changed else '✔'} {len(changed)} re-indented, {same} unchanged, {len(new)} new (vs {ref}, ext {','.join(exts)})")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

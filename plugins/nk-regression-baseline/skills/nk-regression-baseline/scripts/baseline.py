#!/usr/bin/env python3
"""baseline.py — freeze the byte-exact output of commands on their default inputs before you change production
code; compare after. New-feature tests never exercise the path existing users are on; this does.

    python3 baseline.py freeze  --dir <baseline-dir> --name <name> [--cwd DIR] [--files GLOB ...] [--normalize REGEX ...] -- <command> [args]
    python3 baseline.py compare --dir <baseline-dir> --name <name> [--cwd DIR]
    python3 baseline.py run     --dir <baseline-dir> --manifest baselines.json --mode freeze|compare
    python3 baseline.py list    --dir <baseline-dir>
    python3 baseline.py --selftest

freeze stores stdout, stderr, exit code and the sha256 of every file matched by --files (outputs the command
writes), plus the command, cwd and normalizers. compare re-runs the same command, applies the same normalizers
(regexes replaced by <NORM> — for timestamps, temp paths, run ids) and reports byte differences with a unified
diff of stdout/stderr and per-file hash changes. A baseline is only meaningful if the frozen run was alive:
freeze prints the exit code and output size so a silently empty baseline is noticed at freeze time.
manifest: [{"name": "…", "cmd": ["python3", "tool.py"], "files": ["out/*.json"], "normalize": ["\\d{4}-\\d{2}-\\d{2}"]}]
Exit: freeze/list 0 · compare 0 identical / 1 differences / 2 no such baseline · run: 1 if any compare differs.
"""
import argparse, difflib, glob, hashlib, json, os, re, subprocess, sys, tempfile


def sha(b):
    return hashlib.sha256(b).hexdigest()


def normalize(text, patterns):
    for p in patterns:
        text = re.sub(p, "<NORM>", text)
    return text


def run_cmd(cmd, cwd, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, b"", b"TIMEOUT"
    except FileNotFoundError as e:
        return 127, b"", str(e).encode()


def file_hashes(cwd, globs):
    out = {}
    for g in globs:
        for p in sorted(glob.glob(os.path.join(cwd, g), recursive=True)):
            if os.path.isfile(p):
                out[os.path.relpath(p, cwd)] = sha(open(p, "rb").read())
    return out


def freeze(bdir, name, cmd, cwd, files, norms):
    cwd = os.path.abspath(cwd or os.getcwd())
    rc, out, err = run_cmd(cmd, cwd)
    rec = {"name": name, "cmd": cmd, "cwd": cwd, "files": files, "normalize": norms, "exit": rc,
           "stdout": normalize(out.decode("utf-8", "replace"), norms), "stderr": normalize(err.decode("utf-8", "replace"), norms),
           "file_sha": file_hashes(cwd, files)}
    os.makedirs(bdir, exist_ok=True)
    json.dump(rec, open(os.path.join(bdir, name + ".json"), "w"), indent=1, ensure_ascii=False)
    return rec


def compare(bdir, name, cwd=None):
    p = os.path.join(bdir, name + ".json")
    if not os.path.isfile(p):
        return 2, [f"no baseline named {name!r} in {bdir}"]
    rec = json.load(open(p))
    cwd = os.path.abspath(cwd or rec["cwd"])
    rc, out, err = run_cmd(rec["cmd"], cwd)
    now_out, now_err = normalize(out.decode("utf-8", "replace"), rec["normalize"]), normalize(err.decode("utf-8", "replace"), rec["normalize"])
    lines = []
    if rc != rec["exit"]:
        lines.append(f"exit code {rec['exit']} → {rc}")
    for label, was, now in (("stdout", rec["stdout"], now_out), ("stderr", rec["stderr"], now_err)):
        if was != now:
            d = list(difflib.unified_diff(was.splitlines(), now.splitlines(), f"baseline/{label}", f"now/{label}", lineterm="", n=1))
            lines.append(f"{label} differs ({len(d)} diff lines):")
            lines.extend("  " + x for x in d[:40])
    now_files = file_hashes(cwd, rec["files"])
    for f in sorted(set(rec["file_sha"]) | set(now_files)):
        a, b = rec["file_sha"].get(f), now_files.get(f)
        if a != b:
            lines.append(f"file {f}: {'missing now' if b is None else 'new' if a is None else 'content changed'}")
    return (1 if lines else 0), lines


def nbytes(text):
    return len(text.encode("utf-8"))                      # sizes are UTF-8 bytes; len() of a str counts characters


def freeze_line(name, rec, with_stderr=True):
    return (f"frozen {name}: exit={rec['exit']} stdout={nbytes(rec['stdout'])}B"
            + (f" stderr={nbytes(rec['stderr'])}B" if with_stderr else "") + f" files={len(rec['file_sha'])}"
            + ("   ⚠️ empty output and no files — is the baseline alive?" if not rec["stdout"] and not rec["file_sha"] else ""))


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory() as d:
        tool = os.path.join(d, "tool.py"); bdir = os.path.join(d, "baselines")
        open(tool, "w").write("import json,sys,datetime\nprint('total', 42)\nprint('run at', datetime.datetime.now().isoformat())\njson.dump({'a':1}, open('out.json','w'))\nsys.exit(0)\n")
        cmd = [sys.executable, "tool.py"]
        rec = freeze(bdir, "totals", cmd, d, ["out.json"], [r"\d{4}-\d{2}-\d{2}T[\d:.]+"])
        chk(rec["exit"] == 0 and "total 42" in rec["stdout"] and "<NORM>" in rec["stdout"] and "out.json" in rec["file_sha"], "freeze records exit, normalised stdout and output-file hashes")
        chk("stdout=3B" in freeze_line("x", {"exit": 0, "stdout": "é\n", "stderr": "", "file_sha": {}}), "reported sizes are UTF-8 bytes, not characters ('é' plus a newline is 3 bytes)")
        rc, msg = compare(bdir, "totals")
        chk(rc == 0 and not msg, f"control: unchanged tool compares identical ({msg})")
        open(tool, "w").write("import json,sys,datetime\nprint('total', 43)\nprint('run at', datetime.datetime.now().isoformat())\njson.dump({'a':1}, open('out.json','w'))\nsys.exit(0)\n")
        rc, msg = compare(bdir, "totals")
        chk(rc == 1 and any("stdout differs" in m for m in msg) and any("-total 42" in m for m in msg) and any("+total 43" in m for m in msg), "a changed number is reported with a diff line")
        open(tool, "w").write("import json,sys\nprint('total', 42)\nprint('run at', 'x')\njson.dump({'a':2}, open('out.json','w'))\nsys.exit(0)\n")
        rc, msg = compare(bdir, "totals")
        chk(rc == 1 and any("out.json: content changed" in m for m in msg), "a changed output file is reported by hash")
        open(tool, "w").write("import sys\nprint('total', 42)\nprint('run at', 'x')\nsys.exit(3)\n")
        os.remove(os.path.join(d, "out.json"))   # a leftover from the previous run is not the tool's output
        rc, msg = compare(bdir, "totals")
        chk(rc == 1 and any("exit code 0 → 3" in m for m in msg) and any("out.json: missing now" in m for m in msg), "exit-code change and missing output file are both reported")
        rc, msg = compare(bdir, "nope")
        chk(rc == 2, "an unknown baseline name is exit 2, not a clean 0")
        open(tool, "w").write("print('total 42')\nprint('run at 2026-01-01T00:00:00')\nimport json; json.dump({'a':1}, open('out.json','w'))\n")
        rec = freeze(bdir, "t2", cmd, d, [], [r"\d{4}-\d{2}-\d{2}T[\d:.]+"])
        open(tool, "w").write("print('total 42')\nprint('run at 2027-05-05T11:22:33')\n")
        rc, _ = compare(bdir, "t2")
        chk(rc == 0, "normalizer hides a changed timestamp (control for volatile output)")
    return ok, lines


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("cmd", nargs="?", choices=["freeze", "compare", "run", "list"]); ap.add_argument("--dir"); ap.add_argument("--name")
    ap.add_argument("--cwd"); ap.add_argument("--files", nargs="*", default=[]); ap.add_argument("--normalize", nargs="*", default=[])
    ap.add_argument("--manifest"); ap.add_argument("--mode", choices=["freeze", "compare"]); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    a, rest = ap.parse_known_args()
    if a.help or (not a.cmd and not a.selftest):
        print(__doc__); return 2
    ok, lines = selftest()
    if a.selftest or not ok:
        print(f"baseline selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    if not a.dir:
        print("--dir is required"); return 2
    if a.cmd == "list":
        for f in sorted(glob.glob(os.path.join(a.dir, "*.json"))):
            r = json.load(open(f)); print(f"{r['name']:<24} exit={r['exit']} stdout={nbytes(r['stdout'])}B files={len(r['file_sha'])}  {' '.join(r['cmd'])[:60]}")
        return 0
    if a.cmd == "freeze":
        argv = rest[1:] if rest and rest[0] == "--" else rest
        if not a.name or not argv:
            print("freeze needs --name and a command after --"); return 2
        rec = freeze(a.dir, a.name, argv, a.cwd, a.files, a.normalize)
        print(freeze_line(a.name, rec))
        return 0
    if a.cmd == "compare":
        rc, msg = compare(a.dir, a.name, a.cwd)
        print(f"{'✔' if rc == 0 else '✘'} {a.name}: {'identical to baseline' if rc == 0 else 'differs' if rc == 1 else 'no baseline'}")
        print("\n".join(msg)); return rc
    items = json.load(open(a.manifest)); worst = 0
    for it in items:
        if a.mode == "freeze":
            rec = freeze(a.dir, it["name"], it["cmd"], it.get("cwd", a.cwd), it.get("files", []), it.get("normalize", []))
            print(freeze_line(it["name"], rec, with_stderr=False))
        else:
            rc, msg = compare(a.dir, it["name"], it.get("cwd", a.cwd)); worst = max(worst, rc)
            print(f"{'✔' if rc == 0 else '✘'} {it['name']}"); print("\n".join("  " + m for m in msg))
    return 0 if a.mode == "freeze" else (1 if worst else 0)


if __name__ == "__main__":
    sys.exit(main())

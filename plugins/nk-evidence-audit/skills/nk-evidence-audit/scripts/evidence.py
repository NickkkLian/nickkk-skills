#!/usr/bin/env python3
"""evidence.py — capture a command's raw output as an evidence bundle; index and verify bundles.

    python3 evidence.py run --dir <evidence-dir> --label <label> [--claim "<sentence it supports>"] -- <command> [args...]
    python3 evidence.py run --dir <evidence-dir> --label <label> --shell "<command line>"
    python3 evidence.py index --dir <evidence-dir>
    python3 evidence.py verify --dir <evidence-dir>
    python3 evidence.py --selftest

A bundle is <evidence-dir>/<stamp>-<label>/ holding command.txt (cwd + exact command, re-runnable), stdout.txt,
stderr.txt, exit.txt and meta.json (claim, start/end, duration, git HEAD when inside a repo, sha256 of the three
output files). Nothing is summarised or trimmed: the files are what the command printed.
`verify` re-hashes every bundle against its meta.json: EDITED or INCOMPLETE bundles are reported, because a
transcribed, trimmed or hand-typed output is not evidence. `index` prints one line per bundle.
Exit codes: run → the command's own exit code (the bundle is written either way); index → 0;
verify → 0 intact / 1 edited or incomplete; --selftest → 0 pass / 2 fail.
"""
import argparse, datetime, hashlib, json, os, re, shlex, subprocess, sys, tempfile, time

FILES = ("stdout.txt", "stderr.txt", "exit.txt")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def git_head(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_bundle(evdir, label, argv=None, shell=None, claim=None, cwd=None, timeout=None, quiet=False):
    cwd = os.path.abspath(cwd or os.getcwd())
    label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "run"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    b = os.path.join(os.path.abspath(evdir), f"{stamp}-{label}")
    os.makedirs(b, exist_ok=True)
    cmd_text = shell if shell else " ".join(shlex.quote(a) for a in argv)
    open(os.path.join(b, "command.txt"), "w", encoding="utf-8").write(f"cd {shlex.quote(cwd)}\n{cmd_text}\n")
    t0 = time.time()
    try:
        r = subprocess.run(shell if shell else argv, shell=bool(shell), cwd=cwd, capture_output=True, timeout=timeout)
        out, err, rc = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = e.stdout or b"", (e.stderr or b"") + b"\n[evidence.py] TIMEOUT\n", 124
    except FileNotFoundError as e:
        out, err, rc = b"", f"[evidence.py] not found: {e}\n".encode(), 127
    t1 = time.time()
    open(os.path.join(b, "stdout.txt"), "wb").write(out)
    open(os.path.join(b, "stderr.txt"), "wb").write(err)
    open(os.path.join(b, "exit.txt"), "w").write(f"{rc}\n")
    meta = {"label": label, "claim": claim, "command": cmd_text, "cwd": cwd, "git_head": git_head(cwd),
            "started": datetime.datetime.fromtimestamp(t0).isoformat(timespec="seconds"),
            "ended": datetime.datetime.fromtimestamp(t1).isoformat(timespec="seconds"), "duration_s": round(t1 - t0, 3),
            "exit": rc, "sha256": {f: sha(os.path.join(b, f)) for f in FILES}}
    json.dump(meta, open(os.path.join(b, "meta.json"), "w"), indent=1)
    if not quiet:
        sys.stdout.write(out.decode("utf-8", "replace")); sys.stderr.write(err.decode("utf-8", "replace"))
        print(f"[evidence] {os.path.relpath(b)}  exit={rc}  {meta['duration_s']}s  stdout sha256 {meta['sha256']['stdout.txt'][:12]}", file=sys.stderr)
    return b, rc


def bundles(evdir):
    if not os.path.isdir(evdir):
        return []
    return sorted(d for d in os.listdir(evdir) if os.path.isfile(os.path.join(evdir, d, "meta.json")))


def verify(evdir):
    rows, bad = [], 0
    for d in bundles(evdir):
        meta = json.load(open(os.path.join(evdir, d, "meta.json")))
        missing = [f for f in FILES if not os.path.isfile(os.path.join(evdir, d, f))]
        if missing:
            rows.append((d, "INCOMPLETE", ", ".join(missing))); bad += 1; continue
        edited = [f for f in FILES if sha(os.path.join(evdir, d, f)) != meta.get("sha256", {}).get(f)]
        if edited:
            rows.append((d, "EDITED", ", ".join(edited))); bad += 1
        else:
            rows.append((d, "intact", ""))
    return rows, bad


def index(evdir):
    rows = []
    for d in bundles(evdir):
        m = json.load(open(os.path.join(evdir, d, "meta.json")))
        rows.append((d, str(m.get("exit")), (m.get("claim") or "-")[:60], m["sha256"]["stdout.txt"][:12], m.get("command", "")[:60]))
    return rows


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")

    with tempfile.TemporaryDirectory() as tmp:
        ev = os.path.join(tmp, "ev")
        b, rc = run_bundle(ev, "exit three", argv=[sys.executable, "-c", "import sys; print('hello'); print('warn', file=sys.stderr); sys.exit(3)"], claim="prints hello", cwd=tmp, quiet=True)
        chk(rc == 3 and open(os.path.join(b, "exit.txt")).read().strip() == "3", "exit code recorded and returned (3)")
        chk(open(os.path.join(b, "stdout.txt")).read() == "hello\n" and "warn" in open(os.path.join(b, "stderr.txt")).read(), "stdout and stderr captured raw")
        meta = json.load(open(os.path.join(b, "meta.json")))
        chk(meta["claim"] == "prints hello" and meta["sha256"]["stdout.txt"] == sha(os.path.join(b, "stdout.txt")), "meta carries the claim and matching hashes")
        chk(open(os.path.join(b, "command.txt")).read().startswith("cd "), "command.txt starts with the cwd (re-runnable)")
        rows, bad = verify(ev)
        chk(bad == 0 and rows[0][1] == "intact", "verify: untouched bundle is intact (control)")
        with open(os.path.join(b, "stdout.txt"), "a") as fh:
            fh.write("all tests passed\n")
        rows, bad = verify(ev)
        chk(bad == 1 and rows[0][1] == "EDITED" and "stdout.txt" in rows[0][2], "verify: an appended line is reported as EDITED stdout.txt")
        os.remove(os.path.join(b, "stderr.txt"))
        rows, bad = verify(ev)
        chk(rows[0][1] == "INCOMPLETE", "verify: a deleted file is reported as INCOMPLETE")
        b2, rc2 = run_bundle(ev, "missing", argv=["definitely-not-a-command-xyz"], cwd=tmp, quiet=True)
        chk(rc2 == 127 and "not found" in open(os.path.join(b2, "stderr.txt")).read(), "a missing command is exit 127 with the reason in stderr, bundle still written")
        b3, rc3 = run_bundle(ev, "slow", argv=[sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp, timeout=1, quiet=True)
        chk(rc3 == 124, "a timeout is exit 124 (not silently green)")
        chk(len(index(ev)) == 3, f"index lists all 3 bundles ({len(index(ev))})")
    return ok, lines


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("cmd", nargs="?", choices=["run", "index", "verify"]); ap.add_argument("--dir"); ap.add_argument("--label")
    ap.add_argument("--claim"); ap.add_argument("--shell"); ap.add_argument("--cwd"); ap.add_argument("--timeout", type=float)
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("-h", "--help", action="store_true")
    a, rest = ap.parse_known_args()
    if a.help or (not a.cmd and not a.selftest):
        print(__doc__); return 2
    ok, lines = selftest()
    if a.selftest or not ok:
        print(f"evidence.py selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    if not a.dir:
        print("--dir is required"); return 2
    if a.cmd == "run":
        argv = rest[1:] if rest and rest[0] == "--" else rest
        if not a.label or not (argv or a.shell):
            print("run needs --label and a command (after --) or --shell"); return 2
        _, rc = run_bundle(a.dir, a.label, argv=argv or None, shell=a.shell, claim=a.claim, cwd=a.cwd, timeout=a.timeout)
        return rc
    if a.cmd == "index":
        for d, rc, claim, h, cmd in index(a.dir):
            print(f"{d}  exit={rc:<4} {h}  {claim}  | {cmd}")
        return 0
    rows, bad = verify(a.dir)
    for d, state, detail in rows:
        print(f"  {'✔' if state == 'intact' else '✘'} {d}  {state} {detail}")
    print(f"{'✔' if not bad else '✘'} {len(rows)} bundles, {bad} not trustworthy")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

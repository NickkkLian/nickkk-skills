#!/usr/bin/env python3
"""probe_check.py — open a booking page in Chrome with ?probe=1 and read what its guard did.

    python3 probe_check.py page.html [--chrome /path/to/chrome]
    python3 probe_check.py --selftest

page_check.py reads the file; it can see that the guard compares the right things, not that the comparisons
work. The page carries its own battery for that: opened with ?probe=1 it builds a request of its own for each
case, tries to get something past commit() — the same message twice, other words under a real approval, a
reminder the approval never covered, an approval from the customer side, another request's approval, a phone
number changed after approval — and writes a table into the page. This script opens the page headless and reads
the table. A person can do the same by opening page.html?probe=1 in any browser.

Needs Google Chrome or Chromium. Inside an agent's sandbox Chrome's own sandbox often cannot start; it then runs
once more with --no-sandbox and says so. Exit 0 every case behaved as promised · 1 a case did not · 2 no Chrome,
no report, or the selftest failed.
"""
import html, json, os, re, shutil, subprocess, sys, tempfile

CANDIDATES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
NOTES = []


def find_chrome(given=None):
    for c in ([given] if given else []) + CANDIDATES:
        if c and (os.path.isfile(c) or shutil.which(c)):
            return c if os.path.isfile(c) else shutil.which(c)
    return None


def dump(binary, url, no_sandbox=False):
    prof = tempfile.mkdtemp(prefix="probe-check-")
    try:
        extra = ["--no-sandbox"] if no_sandbox else []
        return subprocess.run([binary, "--headless", "--no-first-run", "--disable-gpu", f"--user-data-dir={prof}"] + extra +
                              ["--window-size=1200,900", "--virtual-time-budget=4000", "--dump-dom", url],
                              capture_output=True, text=True, timeout=90)
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def report(binary, page):
    url = "file://" + os.path.abspath(page) + "?probe=1"
    r = dump(binary, url)
    blocks = re.findall(r'<pre id="guard-probe">(\{.*?)</pre>', r.stdout or "", re.S)
    if not blocks and "Failed to initialize sandbox" in (r.stderr or "") + (r.stdout or ""):
        r = dump(binary, url, no_sandbox=True)
        blocks = re.findall(r'<pre id="guard-probe">(\{.*?)</pre>', r.stdout or "", re.S)
        if blocks:
            NOTES.append("Chrome's own sandbox would not start here, so it ran again with --no-sandbox (the page is your own file)")
    # the last match is the element; the first can be the page's own comment that mentions it
    return json.loads(html.unescape(blocks[-1])) if blocks else None


def show(rep):
    lines = [f"{rep['passed']}/{rep['cases']} cases behaved as the guard promises"]
    for x in rep["rows"]:
        lines.append(f"  {'✔' if x['pass'] else '✘'} {x['case']:<42} {x['got']:<8} {x['refusal'].replace('Refused: ', '')[:78]}")
    return lines


def selftest():
    binary = find_chrome()
    if not binary:
        print("probe_check selftest: no Chrome here, nothing to test against"); return 2
    here = os.path.dirname(os.path.abspath(__file__))
    starter = os.path.join(here, "..", "assets", "starter.html")
    tokens = os.path.join(here, "..", "assets", "design-tokens.css")
    ok = []
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(tokens, os.path.join(t, "design-tokens.css"))
        good = os.path.join(t, "good.html"); shutil.copy(starter, good)
        rep = report(binary, good)
        # every check in commit() has a case of its own (only_check), so a battery that lost one is caught — a bare
        # count of nine or more (the first version) would not notice the issued-approval cases going missing
        need = {"reuse", "words", "kind", "actor", "issued", "request", "revision"}
        have = {r.get("only_check") for r in (rep or {}).get("rows", [])}
        cond = rep and rep["passed"] == rep["cases"] and need <= have
        ok.append(bool(cond)); print(f"  {'PASS' if cond else 'FAIL'}  the starter's guard passes its own battery ({rep and rep['passed']}/{rep and rep['cases']})")
        # the bug an audit found: compare the approval with the request's draft, not with what goes out
        src = open(starter, encoding="utf-8").read()
        old = 'if (action.text !== approvedWords)'
        bad = os.path.join(t, "bad.html")
        open(bad, "w", encoding="utf-8").write(src.replace(old, "if (approval.message !== draftFor(r))", 1))
        rep = report(binary, bad)
        red = [x["case"] for x in (rep or {"rows": []})["rows"] if not x["pass"]]
        cond = src.count(old) == 1 and "other words under a real approval" in red
        ok.append(bool(cond)); print(f"  {'PASS' if cond else 'FAIL'}  a guard that checks the draft instead of the words going out is caught ({'; '.join(red) or 'nothing red'})")
        # a page with no battery at all gives no report, and that is exit 2, not a pass
        nob = os.path.join(t, "nobattery.html")
        open(nob, "w", encoding="utf-8").write(re.sub(r"  if \(/\[\?&\]probe=1.*?\n  \}\n", "", src, count=1, flags=re.S))
        cond = report(binary, nob) is None
        ok.append(bool(cond)); print(f"  {'PASS' if cond else 'FAIL'}  a page without the battery gives no report rather than a pass")
    print(f"probe_check selftest: {sum(ok)}/{len(ok)} passed")
    return 0 if all(ok) else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    given = argv[argv.index("--chrome") + 1] if "--chrome" in argv else None
    if given in args:
        args.remove(given)
    if len(args) != 1:
        print(__doc__.strip().split("\n\n")[1]); return 2
    binary = find_chrome(given)
    if not binary:
        print("no Chrome or Chromium found; open the page with ?probe=1 in any browser instead, or pass --chrome"); return 2
    rep = report(binary, args[0])
    if not rep:
        print("the page wrote no probe report — is it from this skill's template?"); return 2
    for n in NOTES:
        print("note: " + n)
    print("\n".join(show(rep)))
    return 0 if rep["passed"] == rep["cases"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

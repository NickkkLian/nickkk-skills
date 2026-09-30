#!/usr/bin/env python3
"""print_check.py — print a deck the way a person would, and check the printout is the deck.

    python3 print_check.py deck.html [--pdf out.pdf] [--chrome /path/to/chrome]
    python3 print_check.py --selftest

Two questions, both answered by Chrome rather than by reading the file:
  1. Does the PDF have exactly one page per slide? A printed slide that is allowed to grow pushes everything
     after it onto extra pages — the file looks fine and the printout has eleven pages. (A phone layout that
     reaches the print does not change the count in this template: it shrinks the type and the margins, and
     deck_check D06 is what catches it.)
  2. Is any slide too full? A slide hides its overflow so the printout never spills, which also means nothing on
     screen shows a cut-off last line. The deck measures itself when opened with ?check=1 — the 1280×720 slide,
     at any window width — and this reads that report. It is the printed slide as long as no print rule changes
     what is on a slide, which deck_check D06 checks; a print-only size or spacing is not measured here.

Needs Google Chrome or Chromium (found in the usual places, or pass --chrome). Standard library otherwise: the page
count is read from the PDF's page tree, and if the two ways of counting disagree it says so instead of guessing.
Exit 0 clean · 1 the printout is not the deck · 2 usage, no Chrome, or the selftest failed.
"""
import json, os, re, shutil, subprocess, sys, tempfile

CANDIDATES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]


def find_chrome(given=None):
    for c in ([given] if given else []) + CANDIDATES:
        if c and (os.path.isfile(c) or shutil.which(c)):
            return c if os.path.isfile(c) else shutil.which(c)
    return None


NOTES = []   # things the reader of the output should know about how it was printed


def chrome(binary, args, timeout=90, no_sandbox=False):
    prof = tempfile.mkdtemp(prefix="print-check-")
    try:
        extra = ["--no-sandbox"] if no_sandbox else []
        return subprocess.run([binary, "--headless", "--no-first-run", "--disable-gpu", f"--user-data-dir={prof}"] + extra + args,
                              capture_output=True, text=True, timeout=timeout)
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def chrome_twice(binary, args, done):
    """Run Chrome; if done() says it produced nothing and Chrome reports that its own sandbox would not start,
    run it once more with --no-sandbox. Inside an agent's sandbox (Claude Code's test harness, Codex's
    workspace-write) Chrome cannot start its sandbox and exits before printing — measured on 2026-09-22 with both.
    The file being printed is the person's own, on their own disk; the retry is said out loud, never silent."""
    r = chrome(binary, args)
    if done(r):
        return r
    if "Failed to initialize sandbox" in (r.stderr or "") + (r.stdout or ""):
        r = chrome(binary, args, no_sandbox=True)
        if done(r) and "--no-sandbox" not in " ".join(NOTES):
            NOTES.append("Chrome's own sandbox would not start in this environment, so it printed again with --no-sandbox"
                         " (the file is a local one you made; run it outside the sandbox if that matters to you)")
    return r


def pdf_pages(path):
    """(page objects, root /Count). Chrome writes an uncompressed page tree, so both can be read without a PDF
    library; when they disagree the answer is 'cannot tell', not the bigger or the smaller one."""
    b = open(path, "rb").read()
    objects = len(re.findall(rb"/Type\s*/Page(?![s\w])", b))
    counts = [int(x) for x in re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", b)]
    return objects, (max(counts) if counts else None)


def slide_count(html):
    m = re.search(r'<script type="application/json" id="deck">(.*?)</script>', html, re.S)
    return len(json.loads(m.group(1)).get("slides", [])) if m else None


def check(deck_path, binary, pdf_out=None):
    findings = []
    url = "file://" + os.path.abspath(deck_path)
    n = slide_count(open(deck_path, encoding="utf-8").read())
    if n is None:
        return ["no deck data block, so there is no slide count to compare the printout with"], None
    pdf = pdf_out or os.path.join(tempfile.mkdtemp(prefix="print-check-pdf-"), "deck.pdf")
    chrome_twice(binary, ["--no-pdf-header-footer", "--virtual-time-budget=4000", f"--print-to-pdf={pdf}", url],
                 lambda r: os.path.isfile(pdf))
    if not os.path.isfile(pdf):
        return ["Chrome did not write a PDF"], None
    objects, count = pdf_pages(pdf)
    if count is not None and objects != count:
        findings.append(f"cannot tell how many pages the PDF has ({objects} page objects, page tree says {count})")
    elif objects != n:
        findings.append(f"the printout has {objects} pages for {n} slides")
    # a wide window: below 900 px the deck switches to its phone layout, which is not what prints
    dom = chrome_twice(binary, ["--window-size=1440,900", "--virtual-time-budget=4000", "--dump-dom", url + "?check=1"],
                       lambda r: 'id="deck-check"' in (r.stdout or "")).stdout
    m = re.search(r'<pre id="deck-check">(.*?)</pre>', dom, re.S)
    if not m:
        findings.append("the deck did not report on itself with ?check=1 (template older than this script?)")
        full = None
    else:
        rep = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
        full = rep["tooFull"]
        for r in full:
            findings.append(f"slide {r['slide']} is too full: its text ends at {r['used']} px with room for {r['room']}")
    return findings, {"slides": n, "pdf_pages": objects, "pdf": pdf, "too_full": full}


def selftest():
    binary = find_chrome()
    if not binary:
        print("print_check selftest: no Chrome here, nothing to test against"); return 2
    here = os.path.dirname(os.path.abspath(__file__))
    starter = os.path.join(here, "..", "assets", "starter.html")
    tokens = os.path.join(here, "..", "assets", "design-tokens.css")
    ok = []

    def chk(name, cond, detail=""):
        ok.append(bool(cond))
        print(f"  {'PASS' if cond else 'FAIL'}  {name.ljust(56)}  {'' if cond else detail}".rstrip())

    with tempfile.TemporaryDirectory() as t:
        shutil.copy(tokens, os.path.join(t, "design-tokens.css"))
        good = os.path.join(t, "good.html"); shutil.copy(starter, good)
        f, info = check(good, binary)
        chk("the starter prints one page per slide, none too full", not f, str(f))
        # a printed slide allowed to grow, with one slide too long for its page: the printout gains a page.
        # (An unscoped phone media query does not add a page here — the print block keeps each slide 720px high —
        # it shrinks the type and the margins instead, measured 2026-09-22; deck_check D06 catches that one.)
        grow = open(starter, encoding="utf-8").read()
        grow = grow.replace("display: flex !important; height: 720px; overflow: hidden;", "display: flex !important; min-height: 720px;", 1)
        grow = grow.replace('"sub": "If we both agree, the notice goes up on 1 November. If either of us does not, we talk again on Friday."',
                            '"sub": "' + "If we both agree, the notice goes up. " * 40 + '"', 1)
        p = os.path.join(t, "grow.html"); open(p, "w", encoding="utf-8").write(grow)
        f, info = check(p, binary)
        chk("a slide that grows onto a second printed page is caught", any("pages for" in x for x in f), str(f))
        # a slide with far too much on it
        s = open(starter, encoding="utf-8").read()
        s = s.replace('"sub": "A fixed menu for the month keeps most of the cake income and gives the oven back to the bread."',
                      '"sub": "' + "A fixed menu keeps most of the income. " * 30 + '"', 1)
        p = os.path.join(t, "full.html"); open(p, "w", encoding="utf-8").write(s)
        f, info = check(p, binary)
        chk("a slide with too much on it is caught", any("too full" in x for x in f), str(f))
    print(f"print_check selftest: {sum(ok)}/{len(ok)} passed")
    return 0 if all(ok) else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    opts = {argv[i][2:]: argv[i + 1] for i in range(len(argv) - 1) if argv[i].startswith("--") and not argv[i + 1].startswith("--")}
    args = [a for a in args if a not in opts.values()]
    if len(args) != 1:
        print(__doc__.strip().split("\n\n")[1]); return 2
    binary = find_chrome(opts.get("chrome"))
    if not binary:
        print("no Chrome or Chromium found; pass --chrome /path/to/it"); return 2
    findings, info = check(args[0], binary, opts.get("pdf"))
    if info:
        print(f"{info['slides']} slides · {info['pdf_pages']} printed pages · PDF: {info['pdf']}")
    for n in NOTES:
        print("  note: " + n)
    for f in findings:
        print("  " + f)
    print("✔ the printout is the deck" if not findings else f"✘ {len(findings)} problem(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

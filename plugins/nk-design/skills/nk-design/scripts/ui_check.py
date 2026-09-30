#!/usr/bin/env python3
"""ui_check.py — mechanical acceptance checks for a single-file "evidence UI" page (a data tool / workbench that shows
where every number came from). The checks that can be decided by reading the file; the visual ones stay with a human.

    python3 ui_check.py <index.html> [--json OUT]
    python3 ui_check.py --selftest

Checks (what reading the file can decide; not a subset of the 15 acceptance criteria — see references/acceptance.md):
  C01 exactly one primary action button (class btn-primary) in the document
  C02 no hard-coded colours outside the token block (a <style> whose first line contains 'design-tokens' or a
      <link> to design-tokens.css is exempt); hex/rgb/hsl literals elsewhere must carry a 'why:' comment
  C03 every <table> has sortable headers (a <th> with aria-sort or a <button> inside <th>)
  C04 no 'transition: all'; a prefers-reduced-motion block exists
  C05 no 'outline: none' / 'outline:0' without a nearby focus alternative comment 'focus:'
  C06 honesty: no 'trusted by', 'testimonial', 'customers love', star glyphs; footer has About / Not verified / Source
  C07 a Demo marker exists (text 'Demo ·') when the page loads synthetic data (data-demo attribute or 'synthetic')
  C08 signature elements present: a provenance chip (class chip) and a sum strip (class sum-strip)
  C09 external requests only to fonts.googleapis.com / fonts.gstatic.com / github.com
  C10 meta: <title>, <meta name="description">, a theme-color meta, lang attribute, viewport without maximum-scale
  C11 grid columns use minmax(0,1fr) rather than bare 1fr (long content otherwise widens the page)
  C12 no real-looking phone numbers outside the fictional ranges; no e-mail addresses that are not example.com
  C13 appearance contract (design tokens v3.1): a <script> in <head>, before the first stylesheet, that reads
      nl-theme / nl-scheme and sets data-theme and data-scheme; the <html> tag as served carries neither attribute
      (Plaster and System are the defaults and write nothing); no script still writes the legacy data-theme
      "dark" / "light" values
  C14 icons are drawn, not typed: no emoji or symbol characters used as icons (check marks, crosses, stop signs,
      stars, dots, half circles, warning signs…) and no CSS content that draws an arrow or a symbol; a mark is a
      line SVG (inline, or a CSS mask). Arrows in running text are punctuation and stay.
  C15 clickable number sources: the page carries the shared number-sources layer unchanged (numsrc.js and
      numsrc.css, byte for byte), a manifest whose every entry says where the number came from, how it was worked
      out and what was not checked (numsrc.py check: N01 N03 N07 N08), and marks at least one number with
      data-nk-src
Exit: 0 all pass · 1 findings · 2 selftest failed / usage.
"""
import json, os, re, sys, tempfile
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numsrc  # noqa: E402  — the clickable number sources layer shared with the other nk-* page skills

PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# characters that are icons when they stand alone: circled operators, misc technical, geometric shapes, misc symbols,
# dingbats, misc symbols and arrows, emoji, and the emoji variation selector (no emoji on a public page; icons are
# line SVG)
ICON_CHARS = re.compile("[\u2295-\u22a1\u2300-\u23ff\u25a0-\u25ff\u2600-\u27bf\u2b00-\u2bff\U0001f000-\U0001faff\ufe0f]")
def _drawing_removed(html):
    """The page with every data: URI decoded, so that the tags inside an SVG drawn in CSS are tags again: their
    attributes (the path data of a line icon) go with the markup, while any text the SVG carries is still read.
    A real number in an SVG's text must still be caught; the first version, which skipped whole data: URIs, missed it."""
    return re.sub(r"""url\(\s*["']?(data:[^)]*)\)""", lambda m: " " + unquote(m.group(1)) + " ", html)


def _test_number(digits):
    return bool(re.fullmatch(r"1?\d{3}55501\d{2}", digits) or re.fullmatch(r"(?:44|0)7700900\d{3}", digits) or re.fullmatch(r"(?:44|0)2079460\d{3}", digits))


def checks(html):
    out = []
    low = html.lower()
    n_primary = len(re.findall(r'class="[^"]*\bbtn-primary\b', html))
    if n_primary != 1:
        out.append(("C01", f"{n_primary} primary buttons (want exactly 1)"))
    styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)
    for block in styles:
        first = block.strip().split("\n")[0] if block.strip() else ""
        if "design-tokens" in first:
            continue
        for m in re.finditer(r"(#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\()", block):
            line = block[:m.start()].count("\n") + 1
            ctx = block[max(0, m.start() - 120):m.end() + 120]
            if "why:" not in ctx:
                out.append(("C02", f"hard-coded colour outside the token block at style line {line}: {m.group(0)}")); break
    tables = re.findall(r"<table.*?</table>", html, re.S | re.I)
    for i, t in enumerate(tables, 1):
        if "aria-sort" not in t and not re.search(r"<th[^>]*>\s*<button", t, re.I):
            out.append(("C03", f"table {i} has no sortable header (aria-sort or <th><button>)"))
    if re.search(r"transition\s*:\s*all\b", low):
        out.append(("C04", "'transition: all' found"))
    if "prefers-reduced-motion" not in low:
        out.append(("C04", "no prefers-reduced-motion block"))
    for m in re.finditer(r"outline\s*:\s*(none|0)\b", low):
        if "focus:" not in low[max(0, m.start() - 200):m.end() + 200]:
            out.append(("C05", "outline removed without a 'focus:' alternative comment nearby")); break
    for w in ("trusted by", "testimonial", "customers love", "★", "⭐"):
        if w in low:
            out.append(("C06", f"honesty: {w!r} present"))
    foot = re.search(r"<footer.*?</footer>", html, re.S | re.I)
    if not foot or not all(k in foot.group(0).lower() for k in ("about", "not verified", "source")):
        out.append(("C06", "footer lacks the About / Not verified / Source block"))
    if ("synthetic" in low or "data-demo" in low) and not re.search(r"demo\s*(?:<[^>]+>\s*)*·", low):
        out.append(("C07", "synthetic data without a visible 'Demo ·' marker"))
    if not re.search(r'class="[^"]*\bchip\b', html):
        out.append(("C08", "no provenance chip (class chip)"))
    if not re.search(r'class="[^"]*\bsum-strip\b', html):
        out.append(("C08", "no sum strip (class sum-strip)"))
    # an XML namespace (xmlns='http://www.w3.org/2000/svg' inside an SVG drawn in CSS) names a vocabulary and is
    # never fetched; line SVG icons replaced symbol characters in 0.1.2, and their namespace is not a request
    no_ns = re.sub(r"""xmlns(?::\w+)?\s*=\s*['"]https?://www\.w3\.org/[^'"]*['"]""", " ", html)
    for u in sorted(set(re.findall(r"https?://([^/\"'\s)]+)", no_ns))):
        if u not in ("fonts.googleapis.com", "fonts.gstatic.com", "github.com", "www.github.com"):
            out.append(("C09", f"external host {u}"))
    if not re.search(r"<title>[^<]+</title>", html, re.I):
        out.append(("C10", "no <title>"))
    if not re.search(r'<meta\s+name="description"', html, re.I):
        out.append(("C10", "no meta description"))
    if not re.search(r'name="theme-color"', html):
        out.append(("C10", "no theme-color meta (one is enough: the appearance script keeps it in sync)"))
    if not re.search(r"<html[^>]*\slang=", html, re.I):
        out.append(("C10", "no lang attribute on <html>"))
    if re.search(r"maximum-scale|user-scalable\s*=\s*no", low):
        out.append(("C10", "viewport blocks zoom"))
    if re.search(r"grid-template-columns\s*:[^;]*\b1fr\b", low) and "minmax(0,1fr)" not in low.replace(" ", ""):
        out.append(("C11", "grid uses bare 1fr; use minmax(0,1fr) so long content cannot widen the page"))
    text = re.sub(r"<[^>]+>", " ", _drawing_removed(html))
    for m in PHONE.finditer(text):
        d = re.sub(r"\D", "", m.group(0))
        if 10 <= len(d) <= 12 and not _test_number(d) and not m.group(0).strip().isdigit():
            out.append(("C12", f"phone number outside the fictional ranges: {m.group(0).strip()}")); break
    for m in EMAIL.finditer(text):
        if not re.search(r"@(?:[\w.-]*example\.(?:com|org|net)|[\w.-]+\.(?:test|invalid))$", m.group(0)):
            out.append(("C12", f"non-example e-mail: {m.group(0)}")); break
    bare = re.sub(r"<!--.*?-->|/\*.*?\*/", " ", html, flags=re.S)
    typed = sorted(set(ICON_CHARS.findall(bare)))
    drawn = [c for c in re.findall(r"""content\s*:\s*["']([^"']+)["']""", bare) if re.search("[\u2190-\u21ff]", c) or ICON_CHARS.search(c)]
    # a multiplication sign that is the whole content of an element is a close icon, not arithmetic
    drawn += re.findall(r">\s*(\u00d7)\s*<", bare)
    if typed or drawn:
        out.append(("C14", f"icons typed as characters, not drawn: {''.join(typed + drawn)[:20]}"))
    head = html.split("</head>")[0] if "</head>" in html else html
    first_css = min([i for i in (head.find('rel="stylesheet"'), head.find("<style")) if i >= 0] or [len(head)])
    boot = "".join(re.findall(r"<script>(.*?)</script>", head[:first_css], re.S))
    if not ("nl-theme" in boot and "nl-scheme" in boot and "setAttribute('data-theme'" in boot and "setAttribute('data-scheme'" in boot):
        out.append(("C13", "no appearance script in <head> before the styles (read nl-theme/nl-scheme, set data-theme and data-scheme)"))
    tag = re.search(r"<html\b[^>]*>", html, re.I)
    if tag and re.search(r"\bdata-(theme|scheme)=", tag.group(0)):
        out.append(("C13", "the <html> tag ships a theme attribute; defaults must write none"))
    if re.search(r"""dataset\.theme\s*=|setAttribute\(\s*['"]data-theme['"]\s*,\s*['"](dark|light)['"]""", html):
        out.append(("C13", "a script writes the legacy data-theme dark/light value; use data-scheme"))
    broken = [f for f in numsrc.check(html) if f[1] == "error" and f[0] in ("N01", "N03", "N07", "N08")]
    if broken:
        out.append(("C15", f"number sources cannot open ({broken[0][0]}: {broken[0][2][:90]})"))
    if "data-nk-src=" not in html.replace(numsrc.runtime_js(), ""):
        out.append(("C15", "no number is marked with data-nk-src, so none can be clicked for its source"))
    return out


GOOD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Demo Bench</title>
<meta name="description" content="x"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#faece9">
<script>(function(){var d=document.documentElement,t,s;try{t=localStorage.getItem('nl-theme');s=localStorage.getItem('nl-scheme')}catch(e){}
if(t==='paper'||t==='ink')d.setAttribute('data-theme',t);if(s==='dark'||s==='light')d.setAttribute('data-scheme',s)})();</script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
<style>/* design-tokens */ :root{--accent:#b5674a}</style>
<style>.x{color:var(--accent);transition:color .15s}.grid{grid-template-columns:200px minmax(0,1fr)} @media (prefers-reduced-motion: reduce){*{transition-duration:1ms}}</style>
</head><body><header>Demo Bench <span class="pill">Demo · synthetic data</span><button class="btn-primary">Export</button></header>
<div class="sum-strip">3 + 2 = 5 <span class="ok">reconciles</span></div><table><thead><tr><th aria-sort="none"><button>Name</button></th></tr></thead><tbody><tr><td><span class="chip">src A:6</span></td></tr></tbody></table>
<footer><h2>About this demo</h2><h2>Not verified here</h2><h2>Source</h2> a@example.com +1 202 555 0101</footer></body></html>"""
_SRC = numsrc.Sources("sample", not_checked=["The sample is invented."])
_SRC.add("rows", "Input rows", [{"text": "the sample's rows"}], "computation", "count of every row", ["Nothing was checked."], value="5")
GOOD = numsrc.inject(GOOD.replace("3 + 2 = 5", '3 + 2 = <b data-nk-src="rows">5</b>'), _SRC)


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")
    chk(checks(GOOD) == [], f"control page → 0 findings ({checks(GOOD)})")
    cases = [("C01", GOOD.replace('<button class="btn-primary">Export</button>', '<button class="btn-primary">A</button><button class="btn-primary">B</button>')),
             ("C02", GOOD.replace(".x{color:var(--accent);", ".x{color:#ff0000;")),
             ("C03", GOOD.replace('<th aria-sort="none"><button>Name</button></th>', "<th>Name</th>")),
             ("C04", GOOD.replace("transition:color .15s", "transition:all .15s")),
             ("C05", GOOD.replace(".x{color:var(--accent);", ".x{outline:none;color:var(--accent);")),
             ("C06", GOOD.replace("<h2>Source</h2>", "<h2>Source</h2><p>Trusted by 500 teams</p>")),
             ("C07", GOOD.replace("Demo · synthetic data", "synthetic data")),
             ("C14", GOOD.replace("<h2>Source</h2>", "<h2>Source</h2><p><span>\u2713</span> reconciles</p>")),
             ("C14", GOOD.replace(".x{color:var(--accent);", ".x::after{content:'\u2191'}.x{color:var(--accent);")),
             ("C14", GOOD.replace("<h2>Source</h2>", '<h2>Source</h2><button type="button" aria-label="Close">\u00d7</button>')),
             ("C08", GOOD.replace('class="chip"', 'class="tag"')),
             ("C09", GOOD.replace("https://fonts.googleapis.com/css2?family=Inter", "https://cdn.example.net/x.css")),
             ("C10", GOOD.replace('content="width=device-width, initial-scale=1"', 'content="width=device-width, initial-scale=1, maximum-scale=1"')),
             ("C10", GOOD.replace("<title>Demo Bench</title>", "")),
             ("C10", GOOD.replace('<meta name="description" content="x">', "")),
             ("C10", GOOD.replace('<meta name="theme-color" content="#faece9">', "")),
             ("C10", GOOD.replace('<html lang="en">', "<html>")),
             ("C13", GOOD.replace("if(s==='dark'||s==='light')d.setAttribute('data-scheme',s)", "")),
             ("C13", GOOD.replace('<html lang="en">', '<html lang="en" data-theme="ink">')),
             ("C13", GOOD.replace("</body></html>", "<script>document.documentElement.dataset.theme='dark'</script></body></html>")),
             ("C11", GOOD.replace("grid-template-columns:200px minmax(0,1fr)", "grid-template-columns:200px 1fr")),
             ("C12", GOOD.replace("+1 202 555 0101", "+1 604 000 0000")),   # 000 is not an assignable NANP exchange
             ("C04", GOOD.replace("@media (prefers-reduced-motion: reduce){*{transition-duration:1ms}}", "")),
             ("C06", GOOD.replace("<h2>Not verified here</h2>", "")),
             ("C08", GOOD.replace('class="sum-strip"', 'class="strip"')),
             ("C12", GOOD.replace("a@example.com", "a@demo.example")),      # .example is reserved: no real mailbox
             ("C15", GOOD.replace('<b data-nk-src="rows">5</b>', "<b>5</b>")),
             ("C15", GOOD.replace('"not_checked": [\n        "Nothing was checked."\n      ]', '"not_checked": []')),
             ("C15", GOOD.replace("'use strict';", "'use strict'; var edited = 1;")),
             ("C15", re.sub(r'<script type="application/json" id="nk-sources">.*?</script>', "", GOOD, flags=re.S))]
    for code, html in cases:
        got = {c for c, _ in checks(html)}
        chk(got == {code}, f"{code} sample → exactly {{{code}}} (got {sorted(got)})")
    # a line icon drawn as an SVG mask in CSS: its namespace is not a request (C09) and its path is not a phone (C12)
    svg = GOOD.replace(".x{color:var(--accent);", ".x{-webkit-mask:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
                       "viewBox='0 0 10 10'%3E%3Cpath d='M1.6 5.3 4 7.6 8.4 2.4'/%3E%3C/svg%3E\");color:var(--accent);")
    chk(svg != GOOD and checks(svg) == [], f"a line SVG icon in CSS → 0 findings ({checks(svg)})")
    # but an SVG in a data: URI still has its text read: a real-looking number hidden in it is caught
    hidden = GOOD.replace(".x{color:var(--accent);", ".x{-webkit-mask:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
                          "viewBox='0 0 10 10'%3E%3Ctext%3E+1 604 000 0000%3C/text%3E%3C/svg%3E\");color:var(--accent);")
    chk({c for c, _ in checks(hidden)} == {"C12"}, f"a number written as text inside a data: URI SVG → C12 ({checks(hidden)})")
    # in-process, with the self-test switched off: main() runs this self-test on every start, so calling the command
    # line from here would recurse without end (it did once, 2026-09-16, and filled the machine's process table)
    import contextlib, io
    with tempfile.TemporaryDirectory() as d:
        good_p, bad_p = os.path.join(d, "good.html"), os.path.join(d, "bad.html")
        open(good_p, "w", encoding="utf-8").write(GOOD); open(bad_p, "w", encoding="utf-8").write(GOOD.replace('class="chip"', 'class="tag"'))
        with contextlib.redirect_stdout(io.StringIO()):
            rc_good = main([good_p], run_selftest=False)
            rc_bad = main([bad_p], run_selftest=False)
        chk(rc_good == 0 and rc_bad == 1, f"command line: a clean page exits 0, a page with a finding exits 1 ({rc_good}, {rc_bad})")
    return ok, lines


def main(argv, run_selftest=True):
    ok, lines = selftest() if run_selftest else (True, [])
    if "--selftest" in argv or not ok:
        print(f"ui_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    files = [a for a in argv if not a.startswith("--") and a != argv[argv.index("--json") + 1] if "--json" in argv] if "--json" in argv else [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 2
    findings = checks(open(files[0], encoding="utf-8").read())
    print(f"{'✘' if findings else '✔'} {files[0]}: {len(findings)} findings")
    for c, m in findings:
        print(f"    {c}  {m}")
    if "--json" in argv:
        json.dump(findings, open(argv[argv.index("--json") + 1], "w"), indent=1)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

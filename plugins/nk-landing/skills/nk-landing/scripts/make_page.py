#!/usr/bin/env python3
"""make_page.py — a written description of a small business, in one JSON file, becomes one HTML file you can
open, e-mail or put on any static host. No build step, no packages, nothing fetched when it loads.

    python3 make_page.py --init business.json          # a filled-in example to edit
    python3 make_page.py business.json --out page.html [--template assets/starter.html] [--tokens assets/design-tokens.css]
    python3 make_page.py --selftest

What it does, and nothing else: it reads the template, replaces the business data block with yours, and inlines
the token file and the three faces it names (assets/fonts: Fraunces, Inter, Space Mono, Latin subsets, SIL OFL
1.1 — about 135 KB as base64) so the result is a single file that draws its own type. The booking flow, the
staff desk and the approval guard come from the template unchanged — this script never writes behaviour, so a
page it produces behaves exactly like the starter you can read.

It refuses to write a page when the description is missing something a visitor would look for (name, services,
slots), and — while `demo` is true — when it carries a phone number outside the reserved 555-01xx range or an
e-mail at a domain that is not an example domain. A demo of a business that does not exist should not be able
to ring a real telephone.
"""
import base64, json, os, re, sys

sys.dont_write_bytecode = True   # the selftest imports page_check; a __pycache__ beside a shipped script is litter

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "starter.html")
TOKENS = os.path.join(HERE, "..", "assets", "design-tokens.css")
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
FONTS = [("Fraunces", "fraunces-latin-wght.woff2", "100 900"), ("Inter", "inter-latin-wght.woff2", "100 900"),
         ("Space Mono", "space-mono-latin-400.woff2", "400")]
FONT_NOTICE = ("/* Fraunces (c) 2020 The Fraunces Project Authors; Inter (c) 2016 The Inter Project Authors; Space Mono (c) 2016\n"
               "   The Space Mono Project Authors. Latin subsets under the SIL Open Font License 1.1 (openfontlicense.org);\n"
               "   the licence texts ship with the skill in assets/fonts/. Inlined so the file fetches nothing. */")
REQUIRED = ("name", "tagline", "facts", "services", "faq", "slots")
PHONE_OK = re.compile(r"\b555-01\d{2}\b")
PHONE_ANY = re.compile(r"(?<![\d.\-/])(?:\+\d{1,3}[ -]?)?(?:\(\d{3}\)[ -]?|\d{3}[ -])?\d{3}[ -]\d{4}(?![\d.\-/])")
MAIL_ANY = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
MAIL_OK = re.compile(r"@(?:example\.(?:com|org|net)|[\w-]+\.example)\b")

EXAMPLE = {
    "name": "Marley Street Bakery",
    "tagline": "Bread from a two-day starter, and one cake a week that the baker feels like making.",
    "facts": ["Marley Street, opposite the laundrette", "Wed–Sun, 7:00–14:00", "555-0173", "Cash or card"],
    "services": [
        {"name": "Standing bread order", "price": "$6–$11 a loaf", "note": "Tell us which days. We put it aside under your name until noon."},
        {"name": "Celebration cake", "price": "$60–$140", "note": "One flavour a week. Ten days' notice, and we talk it through first."},
        {"name": "Saturday baking table", "price": "$35", "note": "Two hours, six people, one dough. You take home what you shaped."}
    ],
    "faq": [
        {"q": "Do you do gluten-free?", "a": "No. One oven and one bench, so we cannot keep it apart honestly."},
        {"q": "Can I change a standing order?", "a": "Any time before the evening of the day before. After that the dough is already shaped."},
        {"q": "Do you deliver?", "a": "No, but an order under your name keeps until we close."}
    ],
    "slots": ["Wed 08:00", "Thu 08:00", "Sat 09:30", "Sat 11:30", "Sun 09:00"],
    "demo": True
}


def problems(biz):
    out = []
    for f in REQUIRED:
        if not biz.get(f):
            out.append(f"the description has no `{f}`")
    for s in biz.get("services", []):
        for f in ("name", "price", "note"):
            if not s.get(f):
                out.append(f"a service has no `{f}`: {json.dumps(s, ensure_ascii=False)[:60]}")
    for q in biz.get("faq", []):
        if not q.get("q") or not q.get("a"):
            out.append(f"a question is half written: {json.dumps(q, ensure_ascii=False)[:60]}")
    if biz.get("demo", True):
        blob = json.dumps(biz, ensure_ascii=False)
        for m in PHONE_ANY.finditer(blob):
            if not PHONE_OK.search(m.group(0)):
                out.append(f"a demo page cannot carry a real phone number ({m.group(0)}); use the reserved 555-01xx range")
        for m in MAIL_ANY.finditer(blob):
            if not MAIL_OK.search(m.group(0)):
                out.append(f"a demo page cannot carry a real e-mail ({m.group(0)}); use an example domain")
    return out


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def font_faces(font_dir=FONT_DIR):
    """@font-face rules for the three faces the token file names, each file inlined whole as a data: URI."""
    rules = [FONT_NOTICE]
    for family, name, weight in FONTS:
        data = base64.b64encode(open(os.path.join(font_dir, name), "rb").read()).decode("ascii")
        rules.append(f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{data}) format("woff2");'
                     f"font-weight:{weight};font-style:normal;font-display:block}}")
    return "\n".join(rules)


def build(biz, template, tokens):
    """The template with the data block replaced and the token file inlined. Nothing else is touched, so the
    page's behaviour is the template's behaviour — that is the point of doing it this way."""
    block = re.search(r'(<script type="application/json" id="business">)(.*?)(</script>)', template, re.S)
    if not block:
        raise SystemExit("the template has no business data block")
    page = template[:block.start(2)] + "\n" + json.dumps(biz, ensure_ascii=False, indent=2) + "\n" + template[block.end(2):]
    # the template's markup carries the example business as a fallback for readers with no JavaScript (and for
    # anything that reads the file without running it). Those four places are filled in too, or the file would
    # say one thing and the page another.
    page = re.sub(r"<title>.*?</title>", "<title>" + esc(biz["name"]) + " \u2014 booking</title>", page, count=1, flags=re.S)
    page = re.sub(r'<meta name="description" content=".*?">',
                  '<meta name="description" content="' + esc(biz["tagline"]) + '">', page, count=1, flags=re.S)
    page = re.sub(r'(<h1 id="biz-name">).*?(</h1>)', lambda m: m.group(1) + esc(biz["name"]) + m.group(2), page, count=1, flags=re.S)
    page = re.sub(r'(<p class="tagline" id="biz-tagline">).*?(</p>)',
                  lambda m: m.group(1) + esc(biz["tagline"]) + m.group(2), page, count=1, flags=re.S)
    link = re.search(r'\s*<link[^>]+href="[^"]*design-tokens\.css"[^>]*>', page)
    if link:
        page = (page[:link.start()] + '\n<style id="brand-fonts">\n' + font_faces() + '\n</style>'
                + '\n<style id="design-tokens">\n' + tokens.strip() + '\n</style>' + page[link.end():])
    return page


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--init" in argv:
        i = argv.index("--init")
        path = argv[i + 1] if len(argv) > i + 1 else "business.json"
        if os.path.exists(path):
            print(f"refusing: {path} already exists"); return 2
        open(path, "w", encoding="utf-8").write(json.dumps(EXAMPLE, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {path} — edit it, then run this script again with it")
        return 0
    args, opts, it = [], {}, iter(range(len(argv)))
    skip = set()
    for i, a in enumerate(argv):          # a flag eats the word after it, so its value is not a positional
        if i in skip:
            continue
        if a.startswith("--"):
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                opts[a[2:]] = argv[i + 1]; skip.add(i + 1)
            else:
                opts[a[2:]] = True
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__.strip().split("\n\n")[1]); return 2
    biz = json.load(open(args[0], encoding="utf-8"))
    bad = problems(biz)
    if bad:
        print("refusing to write a page:")
        for b in bad:
            print("  " + b)
        return 1
    template = open(opts.get("template", TEMPLATE), encoding="utf-8").read()
    tokens = open(opts.get("tokens", TOKENS), encoding="utf-8").read()
    out = opts.get("out", "page.html")
    page = build(biz, template, tokens)
    open(out, "w", encoding="utf-8").write(page)
    print(f"wrote {out} · {len(page.encode('utf-8')):,} bytes · one file, nothing fetched when it opens")
    print(f"check it: python3 {os.path.normpath(os.path.join(HERE, 'page_check.py'))} {out} --single")
    return 0


def selftest():
    import tempfile
    ok = []

    def check(name, cond, detail=""):
        ok.append((name, bool(cond), detail))
        print(f"  {'PASS' if cond else 'FAIL'}  {name.ljust(56)}  {'' if cond else detail}".rstrip())

    template = open(TEMPLATE, encoding="utf-8").read()
    tokens = open(TOKENS, encoding="utf-8").read()
    check("the example description has nothing missing", not problems(EXAMPLE), str(problems(EXAMPLE)))
    for field in REQUIRED:
        bad = dict(EXAMPLE); bad.pop(field)
        check(f"a description with no {field} is refused", any(field in p for p in problems(bad)), str(problems(bad)))
    # 020 7946 0123 is in the UK range reserved for fiction and .test is a reserved top-level domain (RFC 2606):
    # neither reaches anybody, and both are outside what a demo page is allowed here, which is what these test.
    real = dict(EXAMPLE, facts=["Marley Street", "020 7946 0123"])
    check("a number outside the reserved range is refused in a demo", any("phone" in p for p in problems(real)), str(problems(real)))
    mail = dict(EXAMPLE, facts=["Marley Street", "hi@parcel.test"])
    check("an e-mail outside the example domains is refused in a demo", any("e-mail" in p for p in problems(mail)), str(problems(mail)))
    live = dict(EXAMPLE, demo=False, facts=["Marley Street", "020 7946 0123"])
    check("a page that says it is not a demo may carry its own number", not problems(live), str(problems(live)))

    page = build(EXAMPLE, template, tokens)
    tmpl_biz = json.loads(re.search(r'<script type="application/json" id="business">(.*?)</script>', template, re.S).group(1))
    # whole phrases, not words: "check" is ordinary English, "Safety check and tune-up" is the example's
    phrases = [tmpl_biz["name"], tmpl_biz["tagline"]] + list(tmpl_biz["facts"]) + list(tmpl_biz["slots"]) + \
              [s[k] for s in tmpl_biz["services"] for k in ("name", "note")] + \
              [f[k] for f in tmpl_biz["faq"] for k in ("q", "a")]
    body = re.sub(r'(?s)<style id="design-tokens">.*?</style>', "", page)
    leaked = sorted({p for p in phrases if p and p in body})
    check("the business in the page is the one given", EXAMPLE["name"] in page and not leaked,
          "words from the template's own business survived: " + ", ".join(leaked[:6]))
    check("the token file is inlined", '<style id="design-tokens">' in page and "--bg:" in page, "")
    faces = re.findall(r'@font-face\{font-family:"([^"]+)";src:url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)', page)
    # the answer comes from the token file, not from FONTS: a check that reads the list it checks agrees with any
    # face left out of that list
    named = [re.search(r'--font-%s:\s*"([^"]+)"' % k, tokens).group(1) for k in ("display", "sans", "mono")]
    check("the three faces the tokens name travel inside the file",
          sorted(f for f, _ in faces) == sorted(named), f"{[f for f, _ in faces]} inlined, the tokens name {named}")
    check("each inlined face is its whole font file",
          len(faces) == len(FONTS) and all(base64.b64decode(d) == open(os.path.join(FONT_DIR, n), "rb").read()
                                           for (_, d), (_, n, _) in zip(faces, FONTS)), "")
    check("the fonts' licence notice travels with them", "SIL Open Font License" in page, "")
    fetches = [u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', page)]
    check("nothing is left to fetch", 'href="design-tokens.css"' not in page and not fetches, str(fetches))
    check("the behaviour is the template's, byte for byte",
          re.sub(r'(?s)<script type="application/json" id="business">.*?</script>', "", page).count("function commit(") == 1
          and "state.outbox.push(" in page, "")
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "page.html")
        open(p, "w", encoding="utf-8").write(page)
        sys.path.insert(0, HERE)
        import page_check
        sys.argv.append("--single")
        found = page_check.check(p, public=True)
        sys.argv.remove("--single")
        check("the page it writes passes every rule of page_check", not found, str(found))
    bad = sum(1 for _, g, _ in ok if not g)
    print(f"make_page selftest: {len(ok) - bad}/{len(ok)} passed")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

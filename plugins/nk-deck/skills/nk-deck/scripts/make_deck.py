#!/usr/bin/env python3
"""make_deck.py — a deck written down as JSON becomes one HTML file: arrow keys to move, P to print, one slide
per printed page, nothing fetched when it opens.

    python3 make_deck.py --init deck.json               # the example deck, to overwrite with yours
    python3 make_deck.py deck.json --out deck.html [--template assets/starter.html] [--tokens assets/design-tokens.css]
    python3 make_deck.py --selftest

The script fills in content and never writes behaviour: it replaces the deck data block in the template, fills
the title the file shows before any script runs, and inlines the token file and the three faces it names
(assets/fonts: Fraunces, Inter, Space Mono, Latin subsets, SIL OFL 1.1 — about 135 KB as base64), so the deck
draws its own type and still fetches nothing. Navigation, printing and layout are the template's, unchanged.
It refuses a deck that breaks the rules deck_check.py would report — a label for a title, a sixth point, a
number with no source in a deck that does not say it is illustrative, a made-up number with a source that reads
as real — because a deck that fails those is not finished, and writing the file anyway only moves the problem
to the meeting.
"""
import base64, json, os, re, sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "starter.html")
TOKENS = os.path.join(HERE, "..", "assets", "design-tokens.css")
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
FONTS = [("Fraunces", "fraunces-latin-wght.woff2", "100 900"), ("Inter", "inter-latin-wght.woff2", "100 900"),
         ("Space Mono", "space-mono-latin-400.woff2", "400")]
FONT_NOTICE = ("/* Fraunces (c) 2020 The Fraunces Project Authors; Inter (c) 2016 The Inter Project Authors; Space Mono (c) 2016\n"
               "   The Space Mono Project Authors. Latin subsets under the SIL Open Font License 1.1 (openfontlicense.org);\n"
               "   the licence texts ship with the skill in assets/fonts/. Inlined so the file fetches nothing. */")
sys.path.insert(0, HERE)
import deck_check  # noqa: E402  — one definition of the rules, shared with the checker
import numsrc  # noqa: E402  — the clickable number sources layer shared with the other nk-* page skills (D12)


def font_faces(font_dir=FONT_DIR):
    """@font-face rules for the three faces the token file names, each file inlined whole as a data: URI."""
    rules = [FONT_NOTICE]
    for family, name, weight in FONTS:
        data = base64.b64encode(open(os.path.join(font_dir, name), "rb").read()).decode("ascii")
        rules.append(f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{data}) format("woff2");'
                     f"font-weight:{weight};font-style:normal;font-display:block}}")
    return "\n".join(rules)


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def problems(deck):
    """The rules from deck_check that can be judged on the JSON alone, run on a throwaway page."""
    import tempfile
    page = build(deck, open(TEMPLATE, encoding="utf-8").read(), open(TOKENS, encoding="utf-8").read())
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "d.html")
        open(p, "w", encoding="utf-8").write(page)
        return [f"{c} {m}" for c, m in deck_check.check(p) if c in ("D01", "D02", "D03", "D04", "D05", "D11")]


def build(deck, template, tokens):
    block = re.search(r'(<script type="application/json" id="deck">)(.*?)(</script>)', template, re.S)
    if not block:
        raise SystemExit("the template has no deck data block")
    page = template[:block.start(2)] + "\n" + json.dumps(deck, ensure_ascii=False, indent=2) + "\n" + template[block.end(2):]
    page = re.sub(r"<title>.*?</title>", "<title>" + esc(deck.get("title", "")) + "</title>", page, count=1, flags=re.S)
    first = (deck.get("slides") or [{}])[0]
    page = re.sub(r'<meta name="description" content=".*?">',
                  '<meta name="description" content="' + esc(first.get("sub") or deck.get("title", "")) + '">', page, count=1, flags=re.S)
    link = re.search(r'\s*<link[^>]+href="[^"]*design-tokens\.css"[^>]*>', page)
    if link:
        page = (page[:link.start()] + '\n<style id="brand-fonts">\n' + font_faces() + '\n</style>'
                + '\n<style id="design-tokens">\n' + tokens.strip() + '\n</style>' + page[link.end():])
    src = deck_check.sources(deck)
    return numsrc.inject(page, src) if src else page


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--init" in argv:
        i = argv.index("--init")
        path = argv[i + 1] if len(argv) > i + 1 else "deck.json"
        if os.path.exists(path):
            print(f"refusing: {path} already exists"); return 2
        template = open(TEMPLATE, encoding="utf-8").read()
        example = json.loads(re.search(r'<script type="application/json" id="deck">(.*?)</script>', template, re.S).group(1))
        open(path, "w", encoding="utf-8").write(json.dumps(example, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {path} — the example deck; replace every slide with yours, then run this again with it")
        return 0
    args, opts, skip = [], {}, set()
    for i, a in enumerate(argv):
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
    deck = json.load(open(args[0], encoding="utf-8"))
    bad = problems(deck)
    if bad:
        print("refusing to write the deck:")
        for b in bad:
            print("  " + b)
        return 1
    page = build(deck, open(opts.get("template", TEMPLATE), encoding="utf-8").read(),
                 open(opts.get("tokens", TOKENS), encoding="utf-8").read())
    out = opts.get("out", "deck.html")
    open(out, "w", encoding="utf-8").write(page)
    n = len(deck.get("slides", []))
    print(f"wrote {out} · {n} slides · one file, nothing fetched when it opens")
    print(f"print it: python3 {os.path.normpath(os.path.join(HERE, 'print_check.py'))} {out}   (needs Chrome; checks {n} pages)")
    return 0


def selftest():
    import tempfile
    ok = []

    def check(name, cond, detail=""):
        ok.append((name, bool(cond), detail))
        print(f"  {'PASS' if cond else 'FAIL'}  {name.ljust(58)}  {'' if cond else detail}".rstrip())

    template = open(TEMPLATE, encoding="utf-8").read()
    tokens = open(TOKENS, encoding="utf-8").read()
    example = json.loads(re.search(r'<script type="application/json" id="deck">(.*?)</script>', template, re.S).group(1))
    mine = {"title": "Move the Thursday stand-up to Wednesday afternoon", "for": "The five of us on the rota",
            "slides": [{"title": "Move the Thursday stand-up to Wednesday afternoon"},
                       {"title": "Thursday mornings are when deliveries arrive",
                        "points": [{"text": "Four of the last six Thursdays had a delivery before ten", "source": "the delivery log, July–August"}]},
                       {"title": "Decision: Wednesdays at three, starting next week", "sub": "Tried for a month, then kept or dropped."}]}
    check("the example deck has nothing to refuse", not problems(example), str(problems(example)))
    check("a deck of one's own has nothing to refuse", not problems(mine), str(problems(mine)))
    label = json.loads(json.dumps(mine)); label["slides"][1]["title"] = "Background"
    check("a label for a title is refused", any(p.startswith("D03") for p in problems(label)), str(problems(label)))
    six = json.loads(json.dumps(mine)); six["slides"][1]["points"] = ["a", "b", "c", "d", "e", "f"]
    check("a sixth point is refused", any(p.startswith("D04") for p in problems(six)), str(problems(six)))
    nosrc = json.loads(json.dumps(mine)); nosrc["slides"][1]["points"] = ["Four of the last six Thursdays"]
    check("a number with no source is refused", any(p.startswith("D05") for p in problems(nosrc)), str(problems(nosrc)))
    illus = json.loads(json.dumps(nosrc)); illus["illustrative"] = True
    check("an illustrative deck may carry a number without a source", not problems(illus), str(problems(illus)))
    real = json.loads(json.dumps(mine)); real["illustrative"] = True
    check("an illustrative deck may not give a number a real-looking source",
          any(p.startswith("D05") and "reads as real" in p for p in problems(real)), str(problems(real)))
    dates = json.loads(json.dumps(mine)); dates["slides"][1]["points"] = ["Deliveries come on 6 January and on the 15th, at 7am"]
    check("a date is not a number that needs a source", not problems(dates), str(problems(dates)))

    page = build(mine, template, tokens)
    phrases = [example["title"], example["for"]] + [s["title"] for s in example["slides"]] + \
              [p["text"] if isinstance(p, dict) else p for s in example["slides"] for p in s.get("points", [])]
    body = re.sub(r'(?s)<style id="design-tokens">.*?</style>', "", page)
    leaked = sorted({p for p in phrases if p and p in body})
    check("no sentence of the example deck survives into the output", not leaked, ", ".join(leaked[:3]))
    check("the token file is inlined and nothing is fetched",
          '<style id="design-tokens">' in page and not re.findall(r'(?:src|href)="(https?://[^"]+)"', page), "")
    check("the file's own title is the deck's", "<title>" + esc(mine["title"]) + "</title>" in page, "")
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
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "deck.html")
        open(p, "w", encoding="utf-8").write(page)
        sys.argv.append("--single")
        found = deck_check.check(p)
        sys.argv.remove("--single")
        check("the file it writes passes every rule of deck_check", not found, str(found))
    bad = sum(1 for _, g, _ in ok if not g)
    print(f"make_deck selftest: {len(ok) - bad}/{len(ok)} passed")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

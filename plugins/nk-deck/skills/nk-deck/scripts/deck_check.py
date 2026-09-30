#!/usr/bin/env python3
"""deck_check.py — the rules a deck from this skill has to keep, checked on the file itself.

    python3 deck_check.py <deck.html> [<deck.html> ...] [--single]
    python3 deck_check.py --selftest

  D01  the deck data block is there, parses, and the page reads its slides from it
  D02  3 to 20 slides, and the first one is the cover
  D03  every title states something: not a label ("Results", "Summary of key findings"), at least three words,
       no trailing colon — a reader who reads only the titles should get the argument         (invariant 1)
       A title in Chinese or Japanese is measured in characters (four at least); the label words are English.
  D04  five points at most on any slide, each under 140 characters                               (invariant 2)
  D05  a point that measures something carries a source — digits, or English number words used as a ratio, a
       rate, a change, a fraction or a size ("four of the last six", "twice as", "doubled", "two thirds",
       "dozens of"); a date, a time or a year is not a measurement, where it cannot also be a count. A deck
       marked illustrative says so in words on the page — markup text or a string the script shows, not a
       comment, attribute or name — and a source it gives a made-up number says "illustrative" too  (invariant 3)
  D06  printing is the deck: an @page of 1280×720 with no margin, every slide one page high with overflow
       hidden and a page break after it, every width media query scoped to screen (a phone layout that reaches
       the print shrinks the type and the margins and keeps the page count, so no page count shows it), and
       print rules that set only page breaks, what shows, colours, and the template's slide frame — nothing
       that moves or resizes what is on a slide — so what ?check=1 measures on screen is what prints
                                                                                                  (invariant 4)
  D07  it works from the keyboard: arrows, space, PageUp/PageDown, Home/End, P to print, and #n opens slide n
                                                                                                  (invariant 5)
  D08  nothing is fetched when it opens, except the fonts the token file names — src/href in either quote, CSS
       url() and @import                                                                          (invariant 5)
  D09  colours come from the token file, not from raw hex in the deck's own styles
  D10  a deck built for delivery is one file: no external stylesheet or script
  D11  no "thank you" slide: the last slide is the decision or the ask
  D12  a point that names a source opens it: clicking the point's numbers (or its source note, when the point has
       no digits) shows the source, how the number got there and what was not checked. The page carries the shared
       number-sources layer unchanged (numsrc.js and numsrc.css), a manifest entry for every such point with its
       source word for word, and the template marks the numbers (data-nk-src)

What it cannot see: whether a title is true, whether the argument holds, whether a slide's text actually fits —
`print_check.py` prints the file in Chrome and counts pages for that. D03 and D05 are heuristics that read
English; references/invariants.md lists what they get wrong. Exit 0 clean · 1 findings · 2 selftest failed.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numsrc  # noqa: E402  — the clickable number sources layer shared with the other nk-* page skills

VERSION = "0.1.3"   # written into the sources manifest as the generator


def sources(deck):
    """the manifest behind the page's numbers: one entry per point that names a source (the template marks that
    point's digits, or its source note, with the same id s<slide>p<point>). None when no point names a source."""
    page_wide = ["deck_check.py checks that a source is written under every measurement, not that the source says what the point says."]
    if deck.get("illustrative"):
        page_wide.insert(0, "The numbers in this deck are illustrative, not measured.")
    src = numsrc.Sources(f"nk-deck {VERSION}", not_checked=page_wide)
    for i, s in enumerate(deck.get("slides") or []):
        for j, pt in enumerate(s.get("points") or []):
            if isinstance(pt, dict) and str(pt.get("source") or "").strip():
                src.add(f"s{i + 1}p{j + 1}", str(pt.get("text", "")) or f"slide {i + 1}, point {j + 1}", [{"text": str(pt["source"])}], "stated",
                        "The source the author wrote for this point in the deck's outline; make_deck.py copied it word for word.",
                        ["Nobody opened the source or compared the number with it."], live=True)
    return src if src.to_dict()["sources"] else None

# A title made only of these words is a label however long it is: "Results", but also "Results and next steps"
# and "Summary of our key findings". Length alone cannot tell: a short sentence can argue ("Tuesdays lose money")
# and a long label still says nothing.
LABEL_WORDS = set("""agenda overview introduction intro background context result results finding findings summary
    conclusion conclusions next step steps q a questions question thank you thanks appendix team timeline problem
    problems solution solutions market markets roadmap about us key takeaway takeaways recap update updates status
    discussion analysis review plan plans goal goals objective objectives approach method methods data metric metrics
    and of the for our & to on in a an""".split())
# the business nouns a label is usually built from ("Q3 revenue summary", "The competitive landscape in 2026");
# a title that also says what happened to them ("Revenue fell in the third quarter") is not made only of these
LABEL_WORDS |= set("""revenue sales cost costs quarter quarterly annual year yearly monthly weekly performance
    highlights landscape competitive competition strategy vision mission priorities priority risks risk
    opportunities opportunity from with by at this last""".split())
def is_label(title):
    if CJK.search(title):        # the label words are English: a Chinese title that starts "Q3" is not the label "Q3"
        return False
    words = re.findall(r"[a-z&]+", title.lower())
    return bool(words) and all(w in LABEL_WORDS for w in words)
# scripts written without spaces between words: a title in them is one "word" to split(), so it is counted in
# characters instead — four is about the shortest sentence that can claim something
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]")
def too_short(title):
    if CJK.search(title):
        return len(CJK.findall(title)) + len(re.findall(r"[A-Za-z0-9]+", title)) < 4
    return len(title.split()) < 3
THANKS = re.compile(r"(?i)^\s*(thank you|thanks|questions\??|q\s*&\s*a)\b")
# a measurement, not any number: digits, or number words used as a ratio or a rate ("four of the last six",
# "three in five", "twice as", "half of"). "Two bakes and a cooling rack" describes; "four of the last six
# Thursdays" measures, and only the second needs a source. A heuristic — it will miss some phrasings, and it
# reads a small count in digits ("2 people") as a measurement: write those in words.
_NW = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand|million|dozen)"
MEASURE = [
    ("a digit", r"\d"),
    ("a ratio in words", r"\b" + _NW + r"\s+(?:of|in|out\s+of)\s+(?:the\s+)?(?:last\s+|past\s+)?(?:" + _NW + r"|\d)"),
    ("a rate in words", r"\b" + _NW + r"\s+(?:percent|per\s+cent|times)\b"),
    ("a comparison in words", r"\b(?:half|a\s+third|a\s+quarter|twice|double|triple)\s+(?:as|of|the)\b"),
    ("a change in words", r"\b(?:doubled|tripled|trebled|quadrupled|halved)\b|\bby\s+(?:a\s+)?(?:half|third|quarter)\b"),
    ("a fraction in words", r"\b(?:two|three|four)\s+(?:thirds|quarters|fifths)\b"),
    ("a size in words", r"\b(?:dozens|hundreds|thousands|millions|billions)\s+of\b"),
]
NUMBER = re.compile("(?i)" + "|".join(p for _, p in MEASURE))
# dates, times and years carry digits but measure nothing: "on 1 November", "the 15th", "since 2019", "7am".
# They are taken out before NUMBER looks. A bare year stays a number ("2019 was our best year" is a claim);
# a year after in/since/from/until/by/of/during, after a month or a quarter, or in a range, is a date.
# Months are matched capitalised (so "12 may leave" stays a sentence), a day only 1–31, and a number is taken for a
# date only where it cannot also be a count: the first version stripped "December 40" out of
# "In December 40% of orders…", "March 12" out of "In March 12 customers cancelled", "Q3 40" and "of 2000 orders".
_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DAY = r"(?:3[01]|[12]\d|0?[1-9])"
_YEAR = r"(?:19|20)\d{2}"
_END = r"(?=\s*(?:$|[,.;:)!?]))"   # nothing after it but punctuation or the end of the point
NOT_A_MEASURE = re.compile(
    # 1 November, 1st November 2025
    r"(?<![$£€¥\d.,])\b" + _DAY + r"(?:st|nd|rd|th)?\s+" + _MONTH + r"\b(?:\s+" + _YEAR + r"\b)?"
    # November 1st, November 1, 2025, "…on November 1." — a month then a day only with an ordinal, a year or nothing after
    r"|\b" + _MONTH + r"\s+" + _DAY + r"(?:(?:st|nd|rd|th)\b|,?\s+" + _YEAR + r"\b|" + _END + r")"
    # November 2025
    r"|\b" + _MONTH + r"\s+" + _YEAR + r"\b"
    # the 15th, the 15th of each month ("the 3rd busiest day" is a ranking and stays)
    r"|\bthe\s+" + _DAY + r"(?:st|nd|rd|th)(?:" + _END + r"|\s+of\b)"
    # since 2019, until 2026: words that do not come before a count
    r"|\b(?i:since|until|till|during|before|after|through|throughout)\s+" + _YEAR + r"\b"
    # "in 2025" only where the year closes the phrase: "in 2000 stores" is a count
    r"|\b(?i:in)\s+" + _YEAR + _END +
    # 2019–2021
    r"|\b" + _YEAR + r"\s*[–-]\s*(?:19|20)?\d{2}\b"
    # Q3, Q3 2025, H1, FY24, FY2024 — the quarter alone, never the number after it ("Q3 40% …")
    r"|\b(?:Q[1-4]|H[12])(?:\s+" + _YEAR + r"\b|\s*'\d{2}\b)?(?!\d)|\bFY\s*'?(?:19|20)?\d{2}\b"
    # 7am, 7 pm, 10:30
    r"|\b\d{1,2}(?::\d{2})?\s*(?i:a\.?m\.?|p\.?m\.?)(?![a-z])|\b\d{1,2}:\d{2}\b")
# the same, written in Chinese: a year, a month and day, a day of the month, a time of day (after a word for morning or
# afternoon, or with minutes or "half"), the Nth quarter, the Nth week — without these, a Chinese outline was refused
# on its dates. A bare hour ("3" + the word for o'clock) stays a number: it reads as often as "three points".
CJK_NOT_A_MEASURE = re.compile(
    r"\d{4}\s*\u5e74(?:\s*\d{1,2}\s*\u6708(?:\s*\d{1,2}\s*[\u65e5\u53f7])?)?"
    r"|\d{1,2}\s*\u6708(?:\s*\d{1,2}\s*[\u65e5\u53f7])?|\d{1,2}\s*\u53f7"
    r"|(?:\u4e0a\u5348|\u4e0b\u5348|\u665a\u4e0a|\u65e9\u4e0a|\u4e2d\u5348|\u51cc\u6668)\s*\d{1,2}\s*[\u70b9\u65f6](?:\s*\d{1,2}\s*\u5206|\u534a)?"
    r"|\d{1,2}\s*[\u70b9\u65f6]\s*(?:\d{1,2}\s*\u5206|\u534a)"
    r"|\u7b2c\s*[1-4]\s*\u5b63\u5ea6|\u7b2c\s*\d{1,2}\s*\u5468")
def measures(text):
    return bool(NUMBER.search(CJK_NOT_A_MEASURE.sub(" ", NOT_A_MEASURE.sub(" ", text))))
# "illustrative", or its Chinese, in a source or on the page
SAYS_MADE_UP = re.compile(r"(?i)illustrative|\u793a\u610f")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
EXT_URL = re.compile(r"""(?:src|href)\s*=\s*["']?(https?://[^"'\s>]+)|url\(\s*["']?(https?://[^"')\s]+)|@import\s+["'](https?://[^"']+)""")
FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
KEYS = ["ArrowRight", "ArrowLeft", "PageDown", "PageUp", "Home", "End", '" "', "print()"]
# What a print rule may set: where pages break, what shows, colours — and, on the template's own frame (html, body,
# .viewport, .stage, .slide, the key hint), the box that makes one slide one page. Nothing that moves or resizes what is
# on a slide. The first version listed forbidden properties and missed margin, gap, font-family, word-spacing, scale
# and transform: a print-only gap pushed the last point under the footer with every check green.
PRINT_ANYWHERE = {"background", "background-color", "color", "visibility", "page-break-after", "page-break-before",
                  "page-break-inside", "break-after", "break-before", "break-inside", "-webkit-print-color-adjust",
                  "print-color-adjust"}
PRINT_FRAME = {"html", "body", "html, body", ".viewport", ".stage", ".slide", ".slide:last-child", ".foot .hint", ".hint"}
PRINT_FRAME_PROPS = {"position": r"static|relative", "display": r"block|flex|none", "overflow": r"hidden|visible",
                     "transform": r"none", "width": r"1280px", "height": r"720px|auto"}


def print_changes(pb):
    """Declarations in the print styles that could make the printout differ from the slide ?check=1 measured."""
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", pb):
        sel = " ".join(sel.split())
        if sel.startswith("@page"):
            continue
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            prop, val = (x.strip() for x in decl.split(":", 1))
            prop, val = prop.lower(), re.sub(r"\s*!important$", "", val)
            if prop in PRINT_ANYWHERE:
                continue
            if sel in PRINT_FRAME and prop in PRINT_FRAME_PROPS and re.fullmatch(PRINT_FRAME_PROPS[prop], val):
                continue
            out.append(f"{sel} {{ {prop}: {val} }}")
    return out


def says_illustrative(html):
    """Whether the page can put the word on the screen: in the text of its markup, or in a string its scripts use —
    not in the data block, a style sheet, a comment, an attribute, a class name, or a variable or property name. The
    template's CSS class alone once satisfied this; so did a comment or a variable."""
    h = re.sub(r'<script type="application/json".*?</script>', "", html, flags=re.S)
    h = re.sub(r"<style[^>]*>.*?</style>", "", h, flags=re.S)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", h, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<script[^>]*>.*?</script>", "", h, flags=re.S))
    strings = []
    for js in scripts:
        js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
        js = re.sub(r"(?m)(^|[^:\\\"'])//.*$", r"\1", js)
        js = re.sub(r"""(?:className\s*=\s*|classList\.\w+\(\s*|querySelector(?:All)?\(\s*)("[^"]*"|'[^']*')""", "", js)
        strings += re.findall(r""""(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'""", js)
    return bool(SAYS_MADE_UP.search(text)) or any(SAYS_MADE_UP.search(x) for x in strings)


def deck_block(html):
    m = re.search(r'<script type="application/json" id="deck">(.*?)</script>', html, re.S)
    if not m:
        return None, "no deck data block"
    try:
        return json.loads(m.group(1)), None
    except Exception as e:
        return None, f"the deck data block does not parse: {e}"


def own_styles(html):
    return "\n".join(body for tag, body in re.findall(r"<style([^>]*)>(.*?)</style>", html, re.S)
                     if 'id="design-tokens"' not in tag)


def media_blocks(css):
    """(query, body) for every @media block, by brace counting — enough to ask which queries are screen-only."""
    out, i = [], 0
    while True:
        m = re.search(r"@media([^{]*)\{", css[i:])
        if not m:
            return out
        start = i + m.end()
        depth, j = 1, start
        while j < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        out.append((m.group(1).strip(), css[start:j - 1]))
        i = j


def check(path):
    html = open(path, encoding="utf-8").read()
    out = []
    add = lambda code, msg: out.append((code, msg))

    deck, err = deck_block(html)
    if err:
        add("D01", err)
        deck = {"slides": []}
    elif 'getElementById("deck")' not in html:
        add("D01", "the data block is never read: editing it would change nothing on screen")
    slides = deck.get("slides", [])

    # with no readable block there are no slides to judge: one root cause, one finding
    if not err and not 3 <= len(slides) <= 20:
        add("D02", f"{len(slides)} slides; a deck here is 3 to 20")
    for n, s in enumerate(slides, 1):
        t = (s.get("title") or "").strip()
        if not t:
            add("D03", f"slide {n} has no title")
            continue
        if is_label(t):
            add("D03", f"slide {n}'s title is a label, not a conclusion: {t!r}")
        elif too_short(t):
            add("D03", f"slide {n}'s title is too short to state anything: {t!r}")
        if t.endswith(":"):
            add("D03", f"slide {n}'s title ends in a colon — it introduces a point instead of making one")
        pts = s.get("points") or []
        if len(pts) > 5:
            add("D04", f"slide {n} has {len(pts)} points; the sixth is a second slide")
        for p in pts:
            text = p if isinstance(p, str) else p.get("text", "")
            if len(text) > 140:
                add("D04", f"slide {n} has a point of {len(text)} characters (over 140): {text[:40]}…")
            source = None if isinstance(p, str) else p.get("source")
            if measures(text) and not source and not deck.get("illustrative"):
                add("D05", f"slide {n}: a number with no source: {text[:60]}")
            # in a deck whose numbers are made up, a source that reads as real under a number is the thing the flag
            # exists to stop; a source under a point that measures nothing ("proposal — to be agreed") is not a claim
            if deck.get("illustrative") and source and measures(text) and not SAYS_MADE_UP.search(source):
                add("D05", f"slide {n}: a made-up number with a source that reads as real — start it with "
                           f"'illustrative': {source[:40]}")
    if deck.get("illustrative") and not says_illustrative(html):
        add("D05", "the deck is marked illustrative but the page never says so in words")
    sourced = [(n, j, str(p["source"])) for n, s in enumerate(slides, 1) for j, p in enumerate(s.get("points") or [], 1)
               if isinstance(p, dict) and str(p.get("source") or "").strip()]
    if sourced:
        broken = [f for f in numsrc.check(html) if f[1] == "error" and f[0] in ("N01", "N03", "N07", "N08")]
        if broken:
            add("D12", f"the numbers' sources cannot open ({broken[0][0]}: {broken[0][2][:90]}); build the deck again with make_deck.py")
        else:
            man = json.loads(re.search(r'<script type="application/json" id="nk-sources">(.*?)</script>', html, re.S).group(1))["sources"]
            for n, j, src in sourced:
                e = man.get(f"s{n}p{j}") or {}
                if [x.get("text") for x in e.get("from") or []] != [src]:
                    add("D12", f"slide {n}, point {j}: its source is not in the page's sources manifest word for word, so clicking its number does not show it")
        if not re.search(r'setAttribute\(\s*"data-nk-src"', "\n".join(re.findall(r"<script(?![^>]*application/json)(?![^>]*nk-sources-runtime)[^>]*>(.*?)</script>", html, re.S))):
            add("D12", "the page never marks a point's numbers as clickable (data-nk-src): its sources can never be opened")
    if slides and THANKS.match(slides[-1].get("title", "")):
        add("D11", "the last slide thanks the reader instead of stating the decision or the ask")

    css = own_styles(html)
    blocks = media_blocks(css)
    prints = [b for q, b in blocks if re.search(r"\bprint\b", q)]
    pb = "\n".join(prints)
    if not re.search(r"@page\s*\{[^}]*size\s*:\s*1280px\s+720px[^}]*margin\s*:\s*0", pb):
        add("D06", "no @page of 1280px 720px with margin 0 in the print styles")
    if not re.search(r"\.slide\s*\{[^}]*overflow\s*:\s*hidden", pb):
        add("D06", "a printed slide does not hide its overflow, so a long one spills onto a second page")
    if not re.search(r"\.slide\s*\{[^}]*(break-after\s*:\s*page|page-break-after\s*:\s*always)", pb):
        add("D06", "no page break after each printed slide")
    for q, _ in blocks:
        # (max-width: 900px) and the range form (width <= 900px) are the same query
        if re.search(r"(max|min)-width|\bwidth\s*[<>]=?|[<>]=?\s*width\b", q) and not re.search(r"\bscreen\b", q):
            add("D06", f"a width media query that is not screen-only ({q}): the print will pick it up")
    changed = print_changes(pb)
    if changed:
        add("D06", f"{len(changed)} print rule(s) change what is on a slide ({changed[0]}): the slides measured on "
                   "screen are no longer the slides that print")

    js = "\n".join(re.findall(r"<script(?![^>]*application/json)[^>]*>(.*?)</script>", html, re.S))
    for k in KEYS:
        if k not in js:
            add("D07", f"the keyboard handler does not answer {k.strip(chr(34)) or 'space'}")
    if "location.hash" not in js:
        add("D07", "a link to slide n does not open slide n (#n is never read)")

    for m in EXT_URL.finditer(html):
        url = next(g for g in m.groups() if g)
        if not any(h in url for h in FONT_HOSTS):
            add("D08", f"the deck fetches something when it opens: {url[:70]}")
    hexes = HEX.findall(css)
    if hexes:
        add("D09", f"{len(hexes)} raw colour(s) in the deck's own styles instead of tokens: {', '.join(hexes[:4])}")
    if "--single" in sys.argv:
        for m in re.finditer(r'<link[^>]+rel="stylesheet"[^>]*>|<script[^>]+src="[^"]+"', html):
            add("D10", f"a delivered deck must be one file: {m.group(0)[:70]}")
    return out


# ---------------------------------------------------------------- selftest

def minimal(**over):
    deck = {"title": "Close the Tuesday shift", "for": "The two of us",
            "slides": [{"title": "Close the Tuesday shift from October onwards"},
                       {"title": "Tuesdays cost more to open than they take in",
                        "points": [{"text": "Takings averaged $210 on Tuesdays in August", "source": "till exports, August"}]},
                       {"title": "Decision: closed on Tuesdays from 1 October", "sub": "Reviewed in December."}]}
    deck.update(over.pop("deck", {}))
    page = """<!doctype html><html><head><meta charset="utf-8"><title>t</title>
<link rel="stylesheet" href="design-tokens.css">
<style>
.slide { color: var(--text); }
@media screen and (max-width: 900px) { .slide { position: relative; } }
@media print {
  @page { size: 1280px 720px; margin: 0; }
  .slide { display: flex !important; height: 720px; overflow: hidden; page-break-after: always; break-after: page; }
}
</style></head><body><div id="stage"></div>
<script type="application/json" id="deck">__DECK__</script>
<script>
var DECK = JSON.parse(document.getElementById("deck").textContent);
function fromHash() { return parseInt(location.hash.slice(1), 10) - 1; }
addEventListener("keydown", function (e) {
  if (["ArrowRight", " ", "PageDown"].indexOf(e.key) >= 0) next();
  else if (["ArrowLeft", "PageUp"].indexOf(e.key) >= 0) prev();
  else if (e.key === "Home") first(); else if (e.key === "End") last();
  else if (e.key === "p") print();
});
function mark(li, id) { li.setAttribute("data-nk-src", id); }
</script></body></html>"""
    page = page.replace("__DECK__", json.dumps(deck))
    for old, new in over.pop("sub", []):
        assert page.count(old) == 1, old
        page = page.replace(old, new, 1)
    src = sources(deck)
    page = numsrc.inject(page, src) if src else page
    for old, new in over.pop("post", []):            # changes made to the page after its sources were written in
        assert page.count(old) == 1, old
        page = page.replace(old, new, 1)
    return page


def selftest():
    import tempfile
    S = lambda **k: k
    T = lambda title, points=None: {"slides": [{"title": "Close the Tuesday shift from October"},
                                               dict({"title": title}, **({"points": points} if points else {})),
                                               {"title": "Decision: closed on Tuesdays from October"}]}
    # an illustrative deck whose one source says so, so that only the rule a sample is about stands in its way
    ILL = {"illustrative": True, "slides": [{"title": "Close the Tuesday shift from October onwards"},
                                            {"title": "Tuesdays cost more to open than they take in",
                                             "points": [{"text": "Takings averaged $210 on Tuesdays in August",
                                                         "source": "illustrative — till exports, August"}]},
                                            {"title": "Decision: closed on Tuesdays from 1 October"}]}
    NOTICE = ('<div id="stage"></div>', '<div id="stage"></div><p class="illustrative">The numbers in this deck are illustrative, not measured.</p>')
    cases = [
        ("clean", {}, set()),
        ("D01 no data block", S(sub=[('id="deck"', 'id="other"')]), {"D01"}),
        ("D01 the block is never read", S(sub=[('JSON.parse(document.getElementById("deck").textContent)', "{}")]), {"D01"}),
        ("D02 two slides", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D02"}),
        ("D03 a label title", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Results"}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D03"}),
        ("D03 a long label is still a label", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Summary of our key findings"}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D03"}),
        ("D03 a short sentence that argues is not a label", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Tuesdays lose money"}, {"title": "Decision: closed on Tuesdays from October"}]}), set()),
        ("D03 a title too short to say anything", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Tuesday costs"}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D03"}),
        ("D03 a label with a business noun is still a label", S(deck=T("Q3 revenue summary")), {"D03"}),
        # "Tuesdays keep losing money" and "Summary", in Chinese: counted in characters, not in words
        ("D03 a Chinese title that argues is measured in characters", S(deck=T("\u5468\u4e8c\u4e00\u76f4\u5728\u4e8f\u94b1")), set()),
        ("D03 a Chinese title too short to say anything", S(deck=T("\u603b\u7ed3")), {"D03"}),
        # "is" and "are" in the label words once made every "X is at risk" a label; a Chinese title with
        # one English word ("Q3 revenue fell by a fifth", in Chinese) was judged on that word alone
        ("D03 a sentence with 'is' in it is not a label", S(deck=T("The roadmap is at risk")), set()),
        ("D03 a Chinese title with an English word is not a label", S(deck=T("Q3 \u8425\u6536\u540c\u6bd4\u4e0b\u964d\u4e24\u6210")), set()),
        ("D03 a title ending in a colon", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Here is what the numbers show:"}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D03"}),
        ("D04 six points", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Six reasons to close on a Tuesday", "points": ["a", "b", "c", "d", "e", "f"]}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D04"}),
        ("D04 a point that is a paragraph", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Tuesdays are quiet in a way that matters", "points": ["word " * 30]}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D04"}),
        ("D05 a number with no source", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Tuesdays cost more to open than they take in", "points": ["Takings averaged $210 on Tuesdays"]}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D05"}),
        ("D05 a measurement in words with no source", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Tuesdays cost more to open than they take in", "points": ["Four of the last six Tuesdays ran at a loss"]}, {"title": "Decision: closed on Tuesdays from October"}]}), {"D05"}),
        ("D05 a count that only describes is not a measurement", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Opening on a Tuesday takes the whole team", "points": ["Two people, one oven and the till"]}, {"title": "Decision: closed on Tuesdays from October"}]}), set()),
        ("D05 illustrative in the data but not on the page", S(deck=ILL), {"D05"}),
        ("D05 a notice that is only a class name is not a notice",
         S(deck=ILL, sub=[('<div id="stage"></div>', '<div id="stage"></div><p class="illustrative"></p>'),
                          (".slide { color: var(--text); }", ".slide { color: var(--text); } .illustrative { color: var(--text-2); }")]), {"D05"}),
        ("D05 an illustrative deck that says so in words", S(deck=ILL, sub=[NOTICE]), set()),
        ("D05 a made-up number with a source that reads as real", S(deck={"illustrative": True}, sub=[NOTICE]), {"D05"}),
        ("D05 a point that measures nothing may name any source", S(deck=dict(ILL, slides=ILL["slides"][:1] + [
            {"title": "Try it for six Mondays before deciding", "points": [{"text": "Run the closure for six consecutive Mondays",
                                                                           "source": "proposal — to be agreed by both owners"}]}] + ILL["slides"][2:]),
                                                                         sub=[NOTICE]), set()),
        # "from 1 October, the meeting is at half past three", in Chinese
        ("D05 a Chinese date or time is not a measurement", S(deck=T("Tuesdays cost more to open than they take in", ["10 \u6708 1 \u65e5\u8d77\uff0c\u4e0b\u5348 3 \u70b9\u534a\u5f00\u4f1a"])), set()),
        # a source that says "illustrative" in Chinese ("illustrative — till exports")
        ("D05 a source that says illustrative in Chinese", S(deck=dict(ILL, slides=ILL["slides"][:1] + [
            {"title": "Tuesdays cost more to open than they take in", "points": [{"text": "Takings averaged $210 on Tuesdays in August",
                                                                                  "source": "\u793a\u610f \u2014 \u6536\u94f6\u8bb0\u5f55"}]}] + ILL["slides"][2:]),
                                                               sub=[NOTICE]), set()),
        # the cover notice written in Chinese ("the numbers in this deck are illustrative")
        ("D05 a notice written in Chinese is a notice", S(deck=ILL, sub=[('<div id="stage"></div>', '<div id="stage"></div><p>\u672c\u6f14\u793a\u4e2d\u7684\u6570\u5b57\u5747\u4e3a\u793a\u610f</p>')]), set()),
        # the first date rule stripped these numbers and let them through with no source
        ("D05 a number after a month is still a number", S(deck=T("Custom cakes crowd out the bread", ["In December 40% of orders were custom cakes"])), {"D05"}),
        ("D05 a count after 'of' is still a number", S(deck=T("The order book is overflowing", ["A backlog of 2000 orders"])), {"D05"}),
        ("D05 a number after a quarter is still a number", S(deck=T("Late orders are a third-quarter problem", ["In Q3 40% of orders were late"])), {"D05"}),
        # a ">" inside the comment, so that taking tags out of the markup is not enough to hide it
        ("D05 a notice only in a comment is not a notice", S(deck=ILL, sub=[('<div id="stage"></div>', '<div id="stage"></div><!-- slide 3 > slide 2, and the numbers are illustrative -->')]), {"D05"}),
        ("D05 a variable named illustrative is not a notice", S(deck=ILL, sub=[("var DECK = JSON.parse", "var illustrative = true;\nvar DECK = JSON.parse")]), {"D05"}),
        ("D05 a date is not a measurement", S(deck=T("Tuesdays cost more to open than they take in", ["We reopen on 6 January at 7am", "Open every day since 2019, orders by the 15th"])), set()),
        ("D05 a comparison in words with no source", S(deck=T("Saturdays carry the whole week", ["Twice as many orders on Saturdays"])), {"D05"}),
        ("D05 a rate in words with no source", S(deck=T("Refunds are eating the margin", ["Refunds ran at five percent of orders"])), {"D05"}),
        ("D05 a change in words with no source", S(deck=T("December complaints are about bread", ["Complaints doubled in December"])), {"D05"}),
        ("D05 a fraction in words with no source", S(deck=T("Custom cakes are most of December", ["Two thirds of the cake income"])), {"D05"}),
        ("D05 a size in words with no source", S(deck=T("December complaints are about bread", ["Dozens of complaints every December"])), {"D05"}),
        ("D06 no @page", S(sub=[("@page { size: 1280px 720px; margin: 0; }", "")]), {"D06"}),
        ("D06 a printed slide spills over", S(sub=[("height: 720px; overflow: hidden;", "height: 720px;")]), {"D06"}),
        ("D06 no page break after a slide", S(sub=[("page-break-after: always; break-after: page;", "")]), {"D06"}),
        ("D06 the phone layout leaks into print", S(sub=[("@media screen and (max-width: 900px)", "@media (max-width: 900px)")]), {"D06"}),
        ("D06 the phone layout leaks into print, written as a range", S(sub=[("@media screen and (max-width: 900px)", "@media (width <= 900px)")]), {"D06"}),
        ("D06 a print rule that changes the spacing", S(sub=[("  @page { size: 1280px 720px; margin: 0; }", "  @page { size: 1280px 720px; margin: 0; }\n  ul.points { gap: 120px; }")]), {"D06"}),
        ("D06 a print rule that restyles what is on a slide", S(sub=[("  @page { size: 1280px 720px; margin: 0; }", "  @page { size: 1280px 720px; margin: 0; }\n  ul.points { display: block; }")]), {"D06"}),
        ("D06 a print rule that changes the type", S(sub=[("  @page { size: 1280px 720px; margin: 0; }", "  @page { size: 1280px 720px; margin: 0; }\n  h2 { font-size: 30px; }")]), {"D06"}),
        ("D07 no Home key", S(sub=[('else if (e.key === "Home") first(); ', "")]), {"D07"}),
        ("D07 P does not print", S(sub=[('else if (e.key === "p") print();', "")]), {"D07"}),
        ("D07 #n is never read", S(sub=[("location.hash.slice(1)", "'1'")]), {"D07"}),
        ("D08 an outside request", S(sub=[('<div id="stage">', '<img src="https://cdn.example.net/logo.png"><div id="stage">')]), {"D08"}),
        ("D08 an outside request in single quotes", S(sub=[('<div id="stage">', "<img src='https://cdn.example.net/logo.png'><div id=\"stage\">")]), {"D08"}),
        ("D08 an outside request from the style sheet", S(sub=[(".slide { color: var(--text); }", ".slide { color: var(--text); background: url(https://cdn.example.net/paper.png); }")]), {"D08"}),
        ("D09 a raw colour", S(sub=[(".slide { color: var(--text); }", ".slide { color: #1a1a2e; }")]), {"D09"}),
        ("D12 a sourced point with no entry in the sources manifest", S(post=[('"s2p1"', '"s9p9"')]), {"D12"}),
        ("D12 a source changed after the manifest was written", S(post=[('"text": "till exports, August"', '"text": "till exports, July"')]), {"D12"}),
        ("D12 the shared runtime edited", S(post=[("'use strict';", "'use strict'; var edited = 1;")]), {"D12"}),
        ("D12 no entry says what was not checked", S(post=[('"Nobody opened the source or compared the number with it."', '""')]), {"D12"}),
        ("D12 the numbers are never marked", S(sub=[('li.setAttribute("data-nk-src", id)', 'li.id = id')]), {"D12"}),
        ("D11 a thank-you slide", S(deck={"slides": [{"title": "Close the Tuesday shift from October"}, {"title": "Tuesdays cost more to open than they take in"}, {"title": "Thank you for reading this far today"}]}), {"D11"}),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "d.html")
        for name, over, want in cases:
            open(p, "w", encoding="utf-8").write(minimal(**dict(over)))
            got = {c for c, _ in check(p)}
            good = got == want
            ok = ok and good
            print(f"  {'✔' if good else '✘'} {name} → want {sorted(want) or ['clean']}, got {sorted(got) or ['clean']}")
        open(p, "w", encoding="utf-8").write(minimal())
        sys.argv.append("--single")
        got = {c for c, _ in check(p)}
        sys.argv.remove("--single")
        good = got == {"D10"}
        ok = ok and good
        print(f"  {'✔' if good else '✘'} D10 an external stylesheet with --single → want ['D10'], got {sorted(got) or ['clean']}")
    print(f"deck_check selftest · {'all' if ok else 'NOT all'} samples behaved as written ({len(cases) + 1} cases)")
    return 0 if ok else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    decks = [a for a in argv if not a.startswith("--")]
    if not decks:
        print(__doc__.strip()); return 2
    bad = 0
    for d in decks:
        found = check(d)
        bad += bool(found)
        print(("✘ " if found else "✔ ") + f"{os.path.basename(d)}: {len(found)} findings")
        for code, msg in found:
            print(f"    {code} {msg}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

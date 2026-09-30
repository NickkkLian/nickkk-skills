#!/usr/bin/env python3
"""explorer_check.py — check a built nk-explorer page without opening it.

    python3 explorer_check.py page.html [page.html ...]
    python3 explorer_check.py --selftest

First the page's concept block, read back out of the page, against the concept rules (E01-E07, in concept.py —
the same rules make_explorer.py applies before it builds). Then the page itself:
  E08  the formula language in the page is this skill's, unchanged (the text between its markers is formula.js's)
  E09  one file that fetches nothing. The page opens with its own Content-Security-Policy (right after <meta
       charset>), and the browser holds it to that: nothing loaded from any file or address (only data: images), no
       script but the page's own three, named by their SHA-256, and no string run as code. This refuses a page whose
       policy is missing, not first, or not the one make_explorer.py writes, and one whose scripts no longer match
       the hashes. It also names, so they can be taken out, the usual ways a page asks for something from outside —
       any <link>, a script from a file, an outside address in an attribute (src, srcset, href, …) or in the styles,
       an @import, a <meta http-equiv> refresh (a policy cannot stop one), fetch, XMLHttpRequest, sockets, beacons,
       workers and dynamic import. An attribute naming a file next to the page (src="px.png") is not named here;
       the policy stops the browser loading it
  E10  the page writes text, not markup or code, by the ways listed here: no innerHTML/outerHTML/insertAdjacentHTML/createContextualFragment,
       DOMParser, eval (called in any way), new Function, document.write, string timers, script elements made from
       the script, and no on...= handlers or javascript: addresses in the markup (read as tags, so a question that
       happens to contain "only =" is not a handler). "eval" means the name anywhere in the page's script — eval(…),
       (0, eval)(…), window.eval(…); a name put together while the page runs is not something a reading can see, and
       the policy, which allows no string to run as code, stops it in the browser
  E11  colours come from the design tokens: no hex, rgb() or hsl() in the page's own styles, inline styles, SVG
       colour attributes or scripts, and no named colours in its styles
  E12  no icon characters in the page or its concept: emoji, dingbats, geometric shapes and the other pictograph
       blocks, the emoji punctuation marks and the info sign (‼ ⁉ ℹ), a keycap, and anything followed by the emoji
       selector (U+FE0F). Arrows (→ ↔), and © ® ™, are text and allowed. Icons are line SVG
  E13  the footer says what the formula leaves out, where it comes from, and that the page is not advice
  E14  the page reads its concept block, carries its ?probe=1 battery, and its <title> is the concept's title

What this does not check: that the controls are wired to the formula, that the numbers on the page are right, and
that the practice questions grade as they promise. That needs the page running — probe_check.py.
Exit 0 no findings · 1 findings · 2 usage or the selftest failed.
"""
import html as H, io, json, os, re, sys, urllib.parse
from html.parser import HTMLParser

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import concept as K
import make_explorer as M

FORMULA_JS = os.path.join(HERE, "..", "assets", "formula.js")
MARKS = ("/* formula:start */", "/* formula:end */")
ICONS = re.compile("[\u203c\u2049\u20e3\u2139\u2295-\u22a1\u2300-\u23ff\u25a0-\u25ff\u2600-\u27bf\u2b00-\u2bff\U0001f000-\U0001faff\ufe0f]")
HEAD = re.compile(r'\A\s*<!doctype html>\s*<html\b[^>]*>\s*<head>\s*<meta charset="utf-8">\s*<meta http-equiv="Content-Security-Policy" content="([^"]*)">', re.I)
OUTSIDE_ATTRS = r"(?:src|srcset|href|xlink:href|action|data|poster|formaction|ping|background|manifest|codebase|archive|longdesc|cite)"
TOKENS_BLOCK = re.compile(r'<style id="design-tokens">.*?</style>', re.S)
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
COLOUR_FN = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(\s*[\d.]", re.I)
NAMED = re.compile(r"(?:^|[;{\s])(?:color|background(?:-color)?|fill|stroke|border(?:-[a-z]+)?(?:-color)?|outline(?:-color)?)\s*:[^;}]*?"
                   r"\b(red|blue|green|black|white|gray|grey|orange|yellow|purple|pink|brown|navy|teal|maroon|olive|lime|aqua|fuchsia|silver)\b", re.I)
NETWORK = [(re.compile(p), what) for p, what in (
    (r"\bfetch\s*\(", "fetch()"), (r"\bXMLHttpRequest\b", "XMLHttpRequest"), (r"\bWebSocket\b", "a WebSocket"),
    (r"\bEventSource\b", "an EventSource"), (r"\bsendBeacon\b", "sendBeacon()"), (r"\bimport\s*\(", "a dynamic import()"),
    (r"\bnew\s+Worker\b", "a Worker"), (r"\bserviceWorker\b", "a service worker"))]
CODE = [(re.compile(p), what) for p, what in (
    (r"\.innerHTML\b", "innerHTML"), (r"\.outerHTML\b", "outerHTML"), (r"\binsertAdjacentHTML\b", "insertAdjacentHTML"),
    (r"\bcreateContextualFragment\b", "createContextualFragment"), (r"\bDOMParser\b", "DOMParser"),
    (r"(?<![\w$])eval\b", "eval"), (r"\bnew\s+Function\b", "new Function"), (r"(?<![\w.])Function\s*\(", "Function()"),
    (r"\bdocument\.write", "document.write"), (r"\bset(?:Timeout|Interval)\s*\(\s*[\"'`]", "a timer given a string"),
    (r"\bcreateElement\s*\(\s*[\"'`]script", "a script element made from the script"), (r"javascript:", "a javascript: address"))]


class Tags(HTMLParser):
    """every start tag of the markup with its attributes, as a browser reads them (script and style bodies are text)"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

    handle_startendtag = handle_starttag


def tags_of(text):
    t = Tags()
    t.feed(text)
    t.close()
    return t.tags


def language(text):
    if text.count(MARKS[0]) != 1 or text.count(MARKS[1]) != 1:
        return None
    a, b = text.index(MARKS[0]), text.index(MARKS[1]) + len(MARKS[1])
    return text[a:b] if a < b else None


def scripts(page):
    """the page's own JavaScript: every <script> except the concept block"""
    return "\n".join(m.group(2) for m in re.finditer(r"<script([^>]*)>(.*?)</script>", page, re.S)
                     if 'type="application/json"' not in m.group(1))


def strings_of(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings_of(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings_of(v)


def check_text(page):
    """[(code, message)] for a page's text"""
    found = []
    concept, why = K.read(page)
    if why:
        found.append(("E01", why))
    else:
        found += K.problems(concept)
    bare = TOKENS_BLOCK.sub("", page)
    js = scripts(bare)
    # E08 the formula language
    lang, canon = language(bare), language(io.open(FORMULA_JS, encoding="utf-8").read())
    if lang is None:
        found.append(("E08", "the page does not carry the formula language between its markers exactly once"))
    elif lang != canon:
        found.append(("E08", "the formula language in the page differs from the skill's formula.js; the page may compute something the checkers do not"))
    # E09 one file, nothing fetched — first the page's own policy, which the browser enforces
    head = HEAD.match(page)
    want_policy = M.policy(M.script_hashes(page))
    named = re.search(r"script-src ([^;]*)", head.group(1)) if head else None
    only_hashes = bool(named) and all(re.fullmatch(r"'sha256-[A-Za-z0-9+/=]+'", x) for x in named.group(1).split())
    if not head:
        found.append(("E09", "the page does not open with its Content-Security-Policy (the line after <meta charset>, ahead of anything that could load or run); without it the browser loads and runs whatever the page asks"))
    elif head.group(1) != want_policy and (not only_hashes or re.sub(r"script-src [^;]*", "", head.group(1)) != re.sub(r"script-src [^;]*", "", want_policy)):
        found.append(("E09", f"the page's Content-Security-Policy is not the one make_explorer.py writes: {head.group(1)[:160]}"))
    elif head.group(1) != want_policy:
        found.append(("E09", "the page's scripts are not the ones its policy names by hash: a script was added or changed after the page was built, and the browser runs only the ones the policy names — build the page again with make_explorer.py"))
    for m in re.finditer(r"<link\b[^>]*>", bare, re.I):
        found.append(("E09", f"the page links a file ({m.group(0)[:80]}); a page from this skill is one file — make_explorer.py writes the tokens into it"))
    for m in re.finditer(r"<meta\b[^>]*\bhttp-equiv\s*=\s*[\"']?([^\"'\s>]+)", bare, re.I):
        if m.group(1).lower() != "content-security-policy":
            found.append(("E09", f"a <meta http-equiv=\"{m.group(1)}\"> in the page: a refresh sends the reader to another address, and no policy can stop it"))
    for m in re.finditer(r"<script\b[^>]*\bsrc\s*=", bare, re.I):
        found.append(("E09", "the page loads a script from a file or an address; everything it runs is written into it"))
    for m in re.finditer(r"\b" + OUTSIDE_ATTRS + r"\s*=\s*[\"']?\s*((?:https?:)?//[^\"'\s>]+)", bare, re.I):
        found.append(("E09", f"an outside address in the page: {m.group(1)[:80]}"))
    for m in re.finditer(r"url\(\s*[\"']?((?:https?:)?//[^\"')\s]+)", bare, re.I):
        found.append(("E09", f"an outside address in the page's styles: {m.group(1)[:80]}"))
    for m in re.finditer(r"@import\b[^;]*", "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", bare, re.S))):
        found.append(("E09", f"an @import in the page's styles ({m.group(0)[:80]}): it loads another file"))
    for rx, what in NETWORK:
        if rx.search(js):
            found.append(("E09", f"the page's script uses {what}; the page talks to nothing outside itself"))
    # E10 text, not markup or code, by the listed ways
    for rx, what in CODE:
        if rx.search(js):
            found.append(("E10", f"the page's script uses {what}; it writes text with textContent and runs only its own code"))
    markup = tags_of(bare)
    for tag, attrs in markup:
        for k, v in attrs:
            if k.startswith("on"):
                found.append(("E10", f"an on...= handler in the markup: <{tag} {k}=…>"))
            elif v and re.match(r"\s*javascript:", v, re.I):
                found.append(("E10", f"a javascript: address in the markup: <{tag} {k}=\"{v[:40]}\">"))
    # E11 colours from the tokens
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", bare, re.S))
    inline = " ".join(re.findall(r'\sstyle\s*=\s*"([^"]*)"', bare)) + " " + " ".join(re.findall(r"\sstyle\s*=\s*'([^']*)'", bare))
    attrs = " ".join(v for _, v in re.findall(r'\s(fill|stroke|color|stop-color|flood-color|lighting-color)\s*=\s*"([^"]*)"', bare))
    data = " ".join(urllib.parse.unquote(u) for u in re.findall(r'url\(\s*"(data:[^"]*)"', css) + re.findall(r"url\(\s*'(data:[^']*)'", css))
    for where, text in (("the page's styles", css), ("an inline style", inline), ("an SVG colour attribute", attrs), ("an image written into the styles", data)):
        for rx in (HEX, COLOUR_FN):
            for m in rx.finditer(text):
                found.append(("E11", f"a raw colour in {where}: {m.group(0)}; take it from the design tokens (var(--…))"))
    for m in NAMED.finditer(css + ";" + inline):
        found.append(("E11", f"a named colour in the page's styles: {m.group(1)}; take it from the design tokens"))
    for m in re.finditer(r"[\"'](#[0-9a-fA-F]{3,8}|(?:rgba?|hsla?)\([^\"']*)[\"']", js):
        found.append(("E11", f"a raw colour in the page's script: {m.group(1)[:40]}"))
    # E12 no icon characters
    hits = {ch for ch in ICONS.findall(bare)} | {ch for s in (strings_of(concept) if concept else ()) for ch in ICONS.findall(s)}
    for ch in sorted(hits):
        found.append(("E12", f"an icon character in the page: {ch} (U+{ord(ch):04X}); draw icons as line SVG"))
    # E13 the footer
    foot = re.search(r"<footer\b[^>]*>(.*?)</footer>", bare, re.S)
    if not foot:
        found.append(("E13", "the page has no footer saying what the formula leaves out, where it comes from, and that it is not advice"))
    else:
        f = foot.group(1)
        for words, what in (("What this leaves out", "what the formula leaves out"), ('id="notes"', "the concept's notes"),
                            ("Where the formula comes from", "where the formula comes from"), ('id="source"', "the concept's source"),
                            ("not advice", "that the page is not advice")):
            if words not in f:
                found.append(("E13", f"the footer does not say {what}"))
        for target in ("notes", "source"):
            if not re.search(r'\$\("' + target + r'"\)\.textContent\s*=\s*C\.' + target, js):
                found.append(("E13", f"the page never writes the concept's {target} into its footer"))
    # E14 the page is wired to its concept and carries its probe
    if not re.search(r'getElementById\("concept"\)', js):
        found.append(("E14", "the page's script never reads its concept block"))
    if not (re.search(r"if \(/\[\?&\]probe=1\\b/\.test\(location\.search\)\)", js) and "explorer-probe" in js):
        found.append(("E14", "the page does not carry its ?probe=1 battery, so probe_check.py cannot test it"))
    titles = re.findall(r"<title>(.*?)</title>", bare, re.S)
    if len(titles) != 1:
        found.append(("E14", f"the page has {len(titles)} <title> elements"))
    elif concept and not why and isinstance(concept.get("title"), str) and H.unescape(titles[0]).strip() != concept["title"].strip():
        found.append(("E14", f"the page's <title> is \"{H.unescape(titles[0]).strip()[:60]}\", not the concept's title"))
    if not re.search(r"<html\b[^>]*\blang=", bare):
        found.append(("E14", "the <html> element does not say the page's language"))
    return found


def check(path):
    return check_text(io.open(path, encoding="utf-8").read())


# ---- selftest: one clean page, and for every rule a page broken in the way that rule is there to catch -------------
def _concept(fn):
    def make(base, M):
        c = json.loads(json.dumps(base))
        fn(c)
        return M.render(c)
    return make


def _page(*subs, reseal=True):
    """the starter's page with text replaced. The page is sealed again afterwards, as an editor who knew the page's
    policy would do, so a sample shows the rule it was written for and not also the changed script hashes;
    reseal=False leaves the policy as it was"""
    def make(base, M):
        page = M.render(base)
        for old, new in subs:
            assert page.count(old) == 1, f"the sample's anchor appears {page.count(old)} times: {old[:60]}"
            page = page.replace(old, new, 1)
        return M.seal(page) if reseal else page
    return make


def _whole(concept):
    """a sample built from a whole concept of its own rather than the starter's"""
    def use(c):
        c.clear()
        c.update(json.loads(json.dumps(concept)))
    return use


def _example(name, fn=None):
    """a sample built from one of the worked examples, changed by fn"""
    def use(c):
        c.clear()
        c.update(K.loads(io.open(os.path.join(HERE, "..", "assets", "concepts", name + ".json"), encoding="utf-8").read())[0])
        if fn:
            fn(c)
    return use


BALL = {"title": "How high a ball thrown straight up goes", "question": "A ball thrown straight up slows down, stops and falls back. How high is it at a given moment?",
        "result": {"name": "h", "label": "Height above the hand", "unit": "m"}, "formula": "v * t - 4.9 * t^2",
        "controls": [{"name": "v", "label": "Speed it leaves the hand at", "unit": "m/s", "min": 10, "max": 30, "step": 1, "value": 20},
                     {"name": "t", "label": "Time since it was thrown", "unit": "s", "min": 0, "max": 4, "step": 0.1, "value": 2}],
        "chart": {"x": "t", "title": "Height, moment by moment"}, "notes": ["Air resistance is left out."],
        "source": "the equation of motion under constant acceleration, h = v t - g t² / 2.",
        # at 1.5 s the ball is at 18.975 m; at 2.6 s, coming down, it is at 18.876 m — 0.099 away, inside 0.2
        "practice": [{"type": "compute", "prompt": "Thrown up at 20 m/s: how high is it after 1.5 s?", "set": {"v": 20, "t": 1.5}, "tolerance": 0.2}]}

BOXES = {"title": "How many boxes a delivery needs", "question": "Items are packed into boxes that each hold the same number. How many boxes does a delivery need?",
         "result": {"name": "B", "label": "Boxes needed", "unit": "boxes", "unit_one": "box"}, "formula": "ceil(N / k)",
         "controls": [{"name": "N", "label": "Items to send", "unit": "items", "unit_one": "item", "min": 1, "max": 100, "step": 1, "value": 12},
                      {"name": "k", "label": "Items one box holds", "unit": "items", "unit_one": "item", "min": 1, "max": 20, "step": 1, "value": 6}],
         "chart": {"x": "N", "title": "Boxes for each number of items"}, "notes": ["Every item fits in any box.", "A part-filled box still counts as a box."],
         "source": "rounding up a division: boxes = ceil(items / items per box).",
         "practice": [{"type": "compute", "prompt": "25 items, 10 to a box. How many boxes?", "set": {"N": 25, "k": 10}, "tolerance": 0.4}]}


def _ctl(name, lo=0, hi=10, step=1, value=1, label="Extra"):
    return {"name": name, "label": label, "unit": "", "min": lo, "max": hi, "step": step, "value": value}


def _extra_used(c, name, formula):
    c["formula"] = formula
    c["controls"].append(_ctl(name))
    c["practice"][0]["set"][name] = 1
    c["practice"][0]["prompt"] += f" (Take {name} as 1.)"


def _seven(c):
    c["formula"] = "P * (1 + r/100)^n + a + b + c + d"
    for n in "abcd":
        c["controls"].append(_ctl(n))
        c["practice"][0]["set"][n] = 1
    c["practice"][0]["prompt"] += " (Take a, b, c and d as 1.)"


def _no_curve(c):
    # the formula has a value only at r = 5, which none of the chart's 201 points along r lands on
    c["formula"] = "P * (1 + r/100)^n + sqrt(-(r - 5)^2)"
    c["chart"]["x"] = "r"
    c["practice"][0].update({"prompt": "£2,000 at 5% a year for 5 years. What is the amount?", "set": {"P": 2000, "r": 5, "n": 5}})
    c["practice"][1].update({"prompt": "£1,000 at 5% a year: after how many whole years is there £2,000 or more for the first time?", "fixed": {"P": 1000, "r": 5}})


def _wide(c):
    c["controls"][1].update({"step": 0.01})
    c["controls"][2].update({"max": 400})
    c["practice"][1].update({"fixed": {"P": 1000}, "prompt": "From £1,000, what rate and how many whole years first give £2,000 or more?"})


PROBE_IF = "if (/[?&]probe=1\\b/.test(location.search)) {"
SAMPLES = [
    ("clean", _page(), set()),
    ("E01 no concept block", _page(), {"E01"}, "concept blocks"),     # the block is cut out below, in selftest()
    ("E01 a concept that is a list, not an object", _page(), {"E01"}),     # the block's text is swapped below
    ("E01 a control that is not an object", _concept(lambda c: c["controls"].append(5)), {"E01"}),
    ("E01 a label left empty", _concept(lambda c: c["controls"][0].update({"label": " "})), {"E01"}),
    ("E01 notes written as an object, not a list", _concept(lambda c: c.update({"notes": {"leaves out": "Interest is added once a year."}})), {"E01"}),
    ("E01 a question of a type the page does not know", _concept(lambda c: c["practice"][0].update({"type": "guess"})), {"E01"}),
    ("E01 a question value written as text", _concept(lambda c: c["practice"][0]["set"].update({"P": "2000"})), {"E01"}),
    ("E01 a question value that is true", _concept(lambda c: (c["practice"][0]["set"].update({"n": True}),
                                                             c["practice"][0].update({"prompt": "£2,000 at 3% a year for 1 year. What is the amount?"}))), {"E01"}),
    ("E04 a step below zero, on a control the formula does not use", _concept(lambda c: c["controls"].append(
        {"name": "q", "label": "Unused", "unit": "", "min": 0, "max": 10, "step": -1, "value": 0})), {"E04"}),
    ("E01 a misspelt field", _concept(lambda c: c["practice"][0].update({"tolerence": c["practice"][0].pop("tolerance")})), {"E01"}),
    ("E01 a field the skill does not know", _concept(lambda c: c["practice"][0].update({"hint": "Use the formula."})), {"E01"}),
    ("E01 a required field left out", _concept(lambda c: c.pop("source")), {"E01"}),
    ("E01 a number written as text", _concept(lambda c: c["controls"][0].update({"value": "1000"})), {"E01"}),
    ("E01 true where a number goes", _concept(lambda c: c["controls"][0].update({"value": True})), {"E01"}),
    ("E01 a key written twice", _page(('"title": "How compound interest grows",', '"title": "A", "title": "How compound interest grows",')), {"E01"}, "appears twice"),
    ("E01 a title longer than 90 characters", _concept(lambda c: c.update({"title": "How compound interest grows, " * 4})), {"E01"}),
    ("E01 no notes", _concept(lambda c: c.update({"notes": []})), {"E01"}),
    ("E01 no practice questions", _concept(lambda c: c.update({"practice": []})), {"E01"}),
    ("E01 seven controls", _concept(_seven), {"E01"}),
    ("E02 a name that is not a control", _concept(lambda c: c.update({"formula": "p * (1 + r/100)^n"})), {"E02"}),
    ("E02 a formula that does not parse", _concept(lambda c: c.update({"formula": "P * (1 + r/100"})), {"E02"}),
    ("E02 the result named like a control", _concept(lambda c: c["result"].update({"name": "P"})), {"E02"}),
    ("E02 the result named like a function", _concept(lambda c: c["result"].update({"name": "max"})), {"E02"}),
    ("E04 a starting value between positions", _concept(lambda c: c["controls"][1].update({"value": 5.25})), {"E04"}),
    ("E04 a step that does not divide the range", _concept(lambda c: c["controls"][2].update({"step": 3, "value": 9})), {"E04"}),
    ("E04 positions that need more than six digits", _concept(lambda c: c["controls"][0].update({"min": 1000000, "max": 1000100, "step": 0.1, "value": 1000000})), {"E04"}),
    ("E04 a control named __proto__", _concept(lambda c: (c["controls"][2].update({"name": "__proto__"}), c.update({"formula": "P * (1 + r/100)^__proto__"}),
                                                          c["chart"].update({"x": "__proto__"}), c["practice"][0]["set"].update({"__proto__": c["practice"][0]["set"].pop("n")}),
                                                          c["practice"][1].update({"lowest": "__proto__"}))), {"E04"}),
    ("E04 two controls with one name", _concept(lambda c: c["controls"].append(dict(c["controls"][2], label="Years again"))), {"E04"}),
    ("E04 a control named like a function", _concept(lambda c: c["controls"].append(_ctl("sqrt"))), {"E04"}),
    ("E04 a slider with more than 2000 steps", _concept(lambda c: c["controls"][0].update({"step": 1})), {"E04"}),
    ("E04 a slider with no range", _concept(lambda c: c["controls"][0].update({"min": 1000, "max": 1000})), {"E04"}),
    ("E03 a control the formula never uses", _concept(lambda c: _extra_used(c, "t", c["formula"])), {"E03"}),
    ("E03 a control that never changes the result", _concept(lambda c: _extra_used(c, "q", "P * (1 + r/100)^n + 0 * q")), {"E03"}),
    ("E05 no value at the starting values", _concept(lambda c: c.update({"formula": "P * (1 + r/100)^n / (n - 10)"})), {"E05"}),
    ("E05 the chart runs along something that is not a control", _concept(lambda c: c["chart"].update({"x": "t"})), {"E05"}),
    ("E05 a chart with no curve to draw", _concept(_no_curve), {"E05"}),
    ("E06 a question that leaves a control out", _concept(lambda c: c["practice"][0]["set"].pop("n")), {"E06"}),
    ("E06 a question value between positions", _concept(lambda c: (c["practice"][0]["set"].update({"r": 3.25}), c["practice"][0].update({"prompt": "£2,000 at 3.25% a year for 5 years. What is the amount?"}))), {"E06"}),
    ("E06 a question that never says a value it uses", _concept(lambda c: c["practice"][0].update({"prompt": "£2,000 at 3% a year. What is the amount?"})), {"E06"}),
    ("E06 a value the prompt gives to another control", _concept(lambda c: c["practice"][0]["set"].update({"r": 5})), {"E06"}),
    ("E06 a number that only says how to round, standing in for a value", _concept(lambda c: c["practice"][0].update(
        {"prompt": "£2,000 at 3% a year for 5 years. What is the amount? Give 2 decimal places.", "set": {"P": 2000, "r": 2, "n": 5}})), {"E06"}),
    ("E06 a question label's number standing in for a value", _concept(lambda c: c["practice"][0].update(
        {"prompt": "Task 2: £2,000 at 3% a year for 5 years. What is the amount?", "set": {"P": 2000, "r": 2, "n": 5}})), {"E06"}),
    ("E06 the M of a question label's N of M standing in for a value", _concept(lambda c: c["practice"][0].update(
        {"prompt": "Question 3 of 4: £2,000 at 3% a year for 5 years. What is the amount?", "set": {"P": 2000, "r": 3, "n": 4}})), {"E06"}),
    ("E06 a precision's number standing in for a value", _concept(lambda c: c["practice"][0].update(
        {"prompt": "£2,000 at 3% a year for 5 years. What is the amount? Answer in 2 lines.", "set": {"P": 2000, "r": 2, "n": 5}})), {"E06"}),
    ("E06 a bracketed count standing in for a value", _concept(lambda c: c["practice"][0].update(
        {"prompt": "£2,000 at 3% a year for 5 years. What is the amount (2 marks)?", "set": {"P": 2000, "r": 2, "n": 5}})), {"E06"}),
    ("clean: a negative value stated as x = -2", _concept(lambda c: (c["controls"][1].update({"min": -5}), c["practice"][0].update({"prompt": "£2,000 at r = -2 (a yearly loss of 2%) for 5 years. What is the amount?", "set": {"P": 2000, "r": -2, "n": 5}}))), set()),
    ("E06 a question the formula has no answer for", _concept(lambda c: c.update({"formula": "P * (1 + r/100)^n / (n - 5) * (n - 5)"})), {"E06"}),
    ("E06 a tolerance of zero", _concept(lambda c: c["practice"][0].update({"tolerance": 0})), {"E06"}),
    ("E06 a tolerance that also passes a neighbour", _concept(lambda c: c["practice"][0].update({"tolerance": 60})), {"E06"}),
    ("clean: a step function with a tight tolerance", _concept(_whole(BOXES)), set()),
    ("E06 a tolerance a step function hides", _concept(lambda c: (_whole(BOXES)(c), c["practice"][0].update({"tolerance": 1}))), {"E06"}),
    ("E06 a tolerance a far position passes, on a curve that turns back", _concept(_whole(BALL)), {"E06"}),
    ("E07 fixes something that is not a control", _concept(lambda c: c["practice"][1]["fixed"].update({"q": 1})), {"E07"}),
    ("E07 a fixed value between positions", _concept(lambda c: c["practice"][1].update({"fixed": {"P": 1000, "r": 7.25}, "prompt": "£1,000 at 7.25% a year: after how many whole years is there £2,000 or more for the first time?"})), {"E07"}),
    ("E07 three controls left free", _concept(lambda c: c["practice"][1].update({"fixed": {}})), {"E07"}),
    ("E07 a goal the page does not know", _concept(lambda c: c["practice"][1].update({"goal": "more than"})), {"E07"}),
    ("E07 a within goal with no tolerance", _concept(lambda c: c["practice"][1].update({"goal": "within"})), {"E07"}),
    ("E07 a tolerance on an at-least goal", _concept(lambda c: c["practice"][1].update({"tolerance": 5})), {"E07"}),
    ("E07 lowest and highest together", _concept(lambda c: c["practice"][1].update({"highest": "n"})), {"E07"}),
    ("E07 lowest names a fixed control", _concept(lambda c: c["practice"][1].update({"lowest": "r"})), {"E07"}),
    ("E07 more settings than the checker walks", _concept(_wide), {"E07"}),
    ("E07 a question that never says its target", _concept(lambda c: c["practice"][1].update({"prompt": "£1,000 at 7% a year: after how many whole years has it doubled?"})), {"E07"}),
    ("E07 a within goal whose prompt gives another tolerance", _concept(_example("at-least-one-success", lambda c: c["practice"][1].update({"tolerance": 0.03}))), {"E07"}),
    ("E07 a goal the starting values already pass", _concept(lambda c: (c["practice"][1].pop("lowest"), c["practice"][1].update({"target": 1500, "prompt": "£1,000 at 7% a year: reach £1,500 or more."}))), {"E07"}),
    ("E07 a goal no setting reaches", _concept(lambda c: c["practice"][1].update({"target": 100000, "prompt": "£1,000 at 7% a year: after how many years is there £100,000?"})), {"E07"}),
    ("E08 a changed formula language", _page(('if (b === 0) fail("division by zero"); ', "")), {"E08"}),
    ("E08 the language's markers removed", _page(("/* formula:start */", "")), {"E08"}),
    ("E09 the tokens linked, not written in", None, {"E09"}),     # built below: the inlined block swapped for the link
    ("E09 no Content-Security-Policy", _page(('<meta http-equiv="Content-Security-Policy"', '<meta name="csp-was-here"'), reseal=False), {"E09"}),
    ("E09 a policy that lets images in from anywhere", _page(("img-src data:;", "img-src data: https:;"), reseal=False), {"E09"}),
    ("E09 a script changed after the page was sealed", _page(("/* ---- practice: graded on the result ---- */", "/* ---- practice ---- */"), reseal=False), {"E09"}),
    ("E09 a meta refresh", _page(('<meta name="theme-color"', '<meta http-equiv="refresh" content="30;url=https://example.com/">\n<meta name="theme-color"')), {"E09"}),
    ("E09 an @import in the styles", _page(("<style>\n  *, *::before", '<style>\n  @import "https://example.com/extra.css";\n  *, *::before')), {"E09"}),
    ("E09 an image list from an outside address", _page(("<main>", '<main><img srcset="https://example.com/pixel.png 1x" alt="">')), {"E09"}),
    ("E09 a Google Fonts stylesheet", _page(("</head>", '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">\n</head>')), {"E09"}),
    ("E09 a script from a file", _page(("</head>", '<script src="extra.js"></script>\n</head>')), {"E09"}),
    ("E09 an image from an outside address", _page(("<main>", '<main><img src="https://example.com/pixel.png" alt="">')), {"E09"}),
    ("E09 an outside address in the styles", _page(("  .task p {", '  .task { background-image: url("https://example.com/bg.png"); }\n  .task p {')), {"E09"}),
    ("E09 a fetch", _page(('  var C = JSON.parse(', '  fetch("/log?page=1");\n  var C = JSON.parse(')), {"E09"}),
    ("E10 markup written into the page", _page(('$("title").textContent = C.title;', '$("title").innerHTML = C.title;')), {"E10"}),
    ("E10 eval", _page(('  var C = JSON.parse(', '  eval("1");\n  var C = JSON.parse(')), {"E10"}),
    ("E10 eval called indirectly", _page(('  var C = JSON.parse(', '  (0, eval)("1");\n  var C = JSON.parse(')), {"E10"}),
    ("E10 eval reached through a dot", _page(('  var C = JSON.parse(', '  window.eval("1");\n  var C = JSON.parse(')), {"E10"}),
    ("E10 a javascript: link", _page(("<main>", '<main><a href="javascript:void(0)">start</a>')), {"E10"}),
    ("clean: a question that says 'only ='", _concept(lambda c: c.update({"question": "Money grows at a fixed yearly rate. If only = £1,000 is put in, how much is there after a number of years?"})), set()),
    ("E10 an inline event handler", _page(('id="scheme" aria-pressed', 'id="scheme" onclick="go()" aria-pressed')), {"E10"}),
    ("E11 a raw colour in the page's styles", _page(("  .task p {", "  .task { color: #b00020; }\n  .task p {")), {"E11"}),
    ("E11 a colour in an inline style", _page(("<main>", '<main style="background: rgb(255, 240, 240)">')), {"E11"}),
    ("E11 a colour in an SVG attribute", _page(('stroke="currentColor" stroke-width="1.6"', 'stroke="#ca6980" stroke-width="1.6"')), {"E11"}),
    ("E11 a named colour in the page's styles", _page(("  .task p {", "  .task { border-color: red; }\n  .task p {")), {"E11"}),
    ("E11 a colour set from the script", _page(('  var C = JSON.parse(', '  document.body.style.color = "#ff0000";\n  var C = JSON.parse(')), {"E11"}),
    ("E11 a colour inside an image written into the styles", _page(("stroke='black' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'", "stroke='%23d00000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'")), {"E11"}),
    ("E12 an icon character in the page", _page(("concept explorer</span>", "concept explorer \u2728</span>")), {"E12"}),
    ("E12 an icon written as an escape in the concept", _page(('"The rate never changes."', '"The rate never changes \\u2705"')), {"E12"}),
    ("E12 an emoji punctuation mark", _page(("concept explorer</span>", "concept explorer \u203c</span>")), {"E12"}),
    ("clean: arrows and a copyright sign in a note", _concept(lambda c: c["notes"].append("Rates \u2192 amounts; \u00a9 the formula is public.")), set()),
    ("E13 no footer", None, {"E13"}),       # built below: the footer cut out
    ("E13 the not-advice line removed", _page((" It explains a concept; it is not advice.", "")), {"E13"}),
    ("E13 the notes never written", _page(('  $("notes").textContent = C.notes.join(" ");\n', "")), {"E13"}),
    ("E14 a page that does not read its concept block", _page(('var C = JSON.parse(document.getElementById("concept").textContent);', "var C = window.CONCEPT || {};")), {"E14"}),
    ("E14 no probe battery", _page((PROBE_IF, "if (false) {")), {"E14"}),
    ("E14 a title that is not the concept's", _page(("<title>How compound interest grows</title>", "<title>Explainer</title>")), {"E14"}),
    ("E14 two titles", _page(("</title>", "</title>\n<title>How compound interest grows</title>")), {"E14"}),
    ("E14 no language on the page", _page(('<html lang="en">', "<html>")), {"E14"}),
]


def selftest():
    import make_explorer as M
    starter, _ = K.read(io.open(M.TEMPLATE, encoding="utf-8").read())
    ok = []
    for name, make, want, *words in SAMPLES:
        try:
            if name == "E01 no concept block":
                page = K.BLOCK.sub("", M.render(starter), count=1)
            elif name == "E09 the tokens linked, not written in":
                page = TOKENS_BLOCK.sub(lambda _: M.LINK, M.render(starter), count=1)
            elif name == "E13 no footer":
                page = re.sub(r"<footer>.*?</footer>", "", M.render(starter), count=1, flags=re.S)
            elif name == "E01 a concept that is a list, not an object":
                page = K.BLOCK.sub(lambda _: '<script type="application/json" id="concept">[]</script>', M.render(starter), count=1)
            else:
                page = make(starter, M)
            got = {code for code, _ in check_text(page)}
            detail = [f"{c} {m}" for c, m in check_text(page)]
            if words and not any(words[0] in d for d in detail):
                got = got | {"(not: " + words[0] + ")"}
        except Exception as e:      # a sample that cannot even be built proves nothing either way
            got, detail = {"CRASH"}, [f"{type(e).__name__}: {e}"]
        good = got == want
        ok.append(good)
        print(f"  {'✔' if good else '✘'} {name} → want {sorted(want) or ['clean']}, got {sorted(got) or ['clean']}")
        if not good:
            for d in detail[:4]:
                print(f"        {d[:150]}")
    print(f"explorer_check selftest: {sum(ok)}/{len(ok)} passed")
    return 0 if all(ok) else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__.strip().split("\n\n")[1]); return 2
    total = 0
    for p in paths:
        try:
            found = check(p)
        except OSError as e:
            print(f"cannot read {p}: {e}"); return 2
        total += len(found)
        print(("✘ " if found else "✔ ") + f"{os.path.basename(p)}: {len(found)} findings")
        for code, m in found:
            print(f"  {code} {m}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

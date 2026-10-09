#!/usr/bin/env python3
"""ui_check.py — mechanical acceptance checks for a one-page "evidence UI" page (a data tool / workbench that shows
where every number came from). The checks that can be decided by reading the file; the visual ones stay with a human.

    python3 ui_check.py <index.html> [--json OUT]
    python3 ui_check.py --selftest
    python3 ui_check.py --wire-form <index.html>

Checks (what reading the file can decide; not a subset of the 16 acceptance criteria — see references/acceptance.md):
  C01 exactly one primary action button (class btn-primary) in the document
  C02 no hard-coded colours outside the token block (a <style> whose first line contains 'design-tokens' or a
      <link> to design-tokens.css is exempt); hex/rgb/hsl literals elsewhere must carry a 'why:' comment
  C03 every <table> has sortable headers, at most eight authored header columns, and a bounded,
      keyboard-focusable .tablewrap with horizontal scrolling; runtime columns/geometry need a browser
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
  C16 plate data-form, recorded choice, SHAPE keys, fixed sources, verdict and fallback note agree;
      caption text and caption-function literals contain no untraced digits; early independent build guard,
      static cross and completion after drawing are present (cannot prove execution)
The page command also runs ALL shared numsrc checks, printing both results with one exit code.
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


FORM_NAMES = ("split", "gaps", "waiting", "steps")
FORM_KEYS = {
    "split": ("unit", "amount", "parts", "unknownLabel"),
    "gaps": ("unit", "a", "b", "kind", "words", "point", "show"),
    "waiting": ("unit", "since", "today", "waitingStatuses", "bands", "limitDays", "outcomes"),
    "steps": ("unit", "step", "steps", "exits"),
}


def recorded_form_errors(form, declared):
    """C16b: read the design form choice from the manifest."""
    if not isinstance(form, dict):
        return ["manifest form must be an object"]
    errors = []
    if form.get("name") not in FORM_NAMES or form.get("name") != declared:
        errors.append("manifest form.name must equal plate data-form")
    for key in ("row_is", "why"):
        if not numsrc._string(form.get(key)):
            errors.append("manifest form." + key + " must be non-empty")
    if type(form.get("fallback")) is not bool:
        errors.append("manifest form.fallback must be boolean")
    if not isinstance(form.get("also_fits"), list) or any(x not in FORM_NAMES for x in form.get("also_fits", [])):
        errors.append("manifest form.also_fits must be a list of form names")
    return errors


def shape_block(html):
    """SHAPE is intentionally JSON-compatible: no JavaScript evaluation in a file check."""
    blocks = re.findall(r"/\* SHAPE:start.*?\*/(.*?)/\* SHAPE:end \*/", html, re.S)
    if len(blocks) != 1:
        return None
    match = re.fullmatch(r"\s*var SHAPE\s*=\s*(\{.*\})\s*;\s*", blocks[0], re.S)
    try:
        return json.loads(match.group(1)) if match else None
    except (ValueError, TypeError):
        return None


def fixed_form_ids(shape):
    ids = ["rec.rows"]
    form = shape.get("form")
    if form == "split":
        ids += ["rec.unknown", "rec.cents"]
        for i in range(len(shape.get("parts", []))):
            ids += ["rec.part" + str(i), "rec.part" + str(i) + ".cents"]
        ids += ["rec.count" + str(i) for i in range(len(shape.get("countParts", [])))]
    elif form == "gaps":
        ids += ["rec.a", "rec.b", "rec.lower", "rec.higher", "rec.match.rows", "rec.lower.rows", "rec.higher.rows", "rec.compared", "rec.unknown"]
    elif form == "waiting":
        ids += ["rec.waiting", "rec.oldest", "rec.unknown"]
        ids += ["rec.band" + str(i) for i in range(len(shape.get("bands", [])))]
        ids += ["rec.outcome" + str(i) for i in range(len(shape.get("outcomes", [])))]
    elif form == "steps":
        ids += ["rec.inprogress"]
        ids += ["rec.step" + str(i) for i in range(len(shape.get("steps", [])))]
        ids += ["rec.exit" + str(i) for i in range(len(shape.get("exits", [])))]
    return ids


def wire_form(html):
    """Fill fixed live ids from SHAPE; preserve the deliberately recorded choice and shared runtime."""
    shape = shape_block(html)
    if not isinstance(shape, dict) or shape.get("form") not in FORM_NAMES:
        raise ValueError("SHAPE:start must contain a JSON-compatible var SHAPE with a known form")
    if any(key not in shape for key in FORM_KEYS[shape["form"]]):
        raise ValueError("SHAPE is missing required keys for " + shape["form"])
    page = numsrc._Page(html)
    blocks = [node for node in page.nodes if node.attrs.get("id") == "nk-sources"]
    if len(blocks) != 1:
        raise ValueError("Expected exactly one nk-sources manifest")
    data = json.loads(blocks[0].text())
    plates = [node for node in page.nodes if "plate" in (node.attrs.get("class") or "").split()]
    declared = plates[0].attrs.get("data-form") if len(plates) == 1 else None
    errors = recorded_form_errors(data.get("form"), declared)
    if errors or declared != shape["form"]:
        raise ValueError("; ".join(errors or ["SHAPE.form must equal data-form"]))
    sources = data.get("sources", {})
    # rec.* belongs to the form engine. Other authored page numbers survive switching forms.
    data["sources"] = {key: value for key, value in sources.items() if not key.startswith("rec.")}
    for ident in fixed_form_ids(shape):
        data["sources"][ident] = {
            "label": ident, "from": [{"input": "rows", "text": "Loaded row array; trace() supplies exact matching rows on load."}],
            "how": {"kind": "computation", "text": "Computed by " + shape["form"] + " reconcile(); trace() supplies the exact separate-pass integer formula on load."},
            "not_checked": ["Source accuracy and recorded row status are not verified by an adds-up identity."], "live": True}
    # Require the input used by the engine; never silently claim an absent source.
    if not any(item.get("id") == "rows" for item in data.get("inputs", []) if isinstance(item, dict)):
        raise ValueError("Manifest inputs must include the form engine's rows input")
    start = blocks[0].start
    end = html.find(">", blocks[0].end) + 1
    return html[:start] + '<script type="application/json" id="nk-sources">' + json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c") + '</script>' + html[end:]



_JS_TOKENS = re.compile(r'''//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|[A-Za-z_$][\w$]*|[{}()]''', re.S)


def caption_digit_errors(html):
    """Read caption text and literal HTML fragments; do not evaluate JavaScript or dynamic values."""
    errors = []
    page = numsrc._Page(html)

    def bare_runs(fragment):
        return [text for node, text in fragment.runs if re.search(r"\d", text)
                and not any("data-nk-src" in a.attrs or a.tag in numsrc.IGNORED
                            for a in numsrc._ancestors(node))]

    def excerpt(text):
        index = re.search(r"\d", text).start()
        return text[max(0, index - 35):index + 60].strip()

    for node, text in page.runs:
        parents = list(numsrc._ancestors(node))
        if (re.search(r"\d", text) and any(a.attrs.get("id") == "form-caption" for a in parents)
                and not any("data-nk-src" in a.attrs or a.tag in numsrc.IGNORED for a in parents)):
            errors.append("form-caption has untraced text: " + excerpt(text))

    def unescape(token):
        def decode(match):
            code = match.group(1)
            if code.startswith(("u", "x")) and len(code) > 1:
                return chr(int(code[1:], 16))
            return {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}.get(code, code)
        return re.sub(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", decode, token[1:-1], flags=re.S)

    for script in (n for n in page.nodes if n.tag == "script" and n.attrs.get("type") != "application/json"):
        code = script.text()
        for start in re.finditer(r"\bcaption\s*:\s*function\s*\([^)]*\)\s*\{", code):
            depth, traced_call, fragments = 1, 0, []
            previous = ""
            for match in _JS_TOKENS.finditer(code, start.end()):
                token = match.group()
                if token.startswith(("//", "/*")): continue
                if token == "{": depth += 1
                if token == "}":
                    depth -= 1
                    if not depth: break
                # The shared helpers wrap their output in a sourced number. Ignore their arguments,
                # including numeric source ids and values; the browser still checks their actual source.
                if token == "(" and (traced_call or previous in ("number", "configText")):
                    traced_call += 1
                elif token == ")" and traced_call:
                    traced_call -= 1
                elif token[0] in ('"', "'", "`") and not traced_call:
                    fragments.append(unescape(token))
                previous = token
            for text in bare_runs(numsrc._Page("".join(fragments))):
                errors.append("caption function has untraced literal text: " + excerpt(text))
    return errors


def form_checks(html):
    out = []
    page = numsrc._Page(html)
    plates = [n for n in page.nodes if "plate" in (n.attrs.get("class") or "").split()]
    declared = plates[0].attrs.get("data-form") if len(plates) == 1 else None
    def bad(letter, message):
        out.append(("C16", "[" + letter + "] " + message))
    if len(plates) != 1 or declared not in FORM_NAMES:
        bad("a", "plate data-form: require exactly one plate with split, gaps, waiting or steps")
        return out
    blocks = [n for n in page.nodes if n.attrs.get("id") == "nk-sources"]
    try:
        data = json.loads(blocks[0].text()) if len(blocks) == 1 else {}
        if not isinstance(data, dict): data = {}
    except (ValueError, TypeError):
        data = {}
    for error in recorded_form_errors(data.get("form"), declared):
        bad("b", "nk-sources " + error)
    shape = shape_block(html)
    if not isinstance(shape, dict) or shape.get("form") != declared or declared not in FORM_NAMES:
        bad("c", "SHAPE:start: use one JSON-compatible var SHAPE with form equal to data-form")
    else:
        missing = [k for k in FORM_KEYS[declared] if k not in shape]
        for key in ("parts", "countParts", "bands", "outcomes", "steps", "exits"):
            if key in shape and not isinstance(shape[key], list): missing.append(key + " (array)")
        if declared == "split" and isinstance(shape.get("parts"), list) and not 2 <= len(shape["parts"]) <= 5: missing.append("parts (2 to 5)")
        if declared == "steps" and isinstance(shape.get("steps"), list) and not 3 <= len(shape["steps"]) <= 7: missing.append("steps (3 to 7)")
        if missing: bad("c", "SHAPE keys: require " + ", ".join(missing))
        if not missing:
            sources = data.get("sources", {})
            if not isinstance(sources, dict): sources = {}
            for ident in fixed_form_ids(shape):
                if ident not in sources: bad("d", "nk-sources.sources: add fixed id " + ident)
    eq = [n for n in page.nodes if "sum-eq" in (n.attrs.get("class") or "").split()
          and any(a in plates for a in numsrc._ancestors(n))]
    scripts = "\n".join(n.text() for n in page.nodes if n.tag == "script" and n.attrs.get("type") != "application/json" and n.attrs.get("id") != "nk-build-guard")
    if not eq or 'class="ok"' not in scripts or 'class="bad"' not in scripts:
        bad("e", 'plate .sum-eq and shared verdict(): require script output class="ok" and class="bad"')
    notes = [n for n in page.nodes if "data-form-note" in n.attrs]
    form = data.get("form")
    fallback = isinstance(form, dict) and form.get("fallback") is True
    if (fallback and (len(notes) != 1 or not any(a.tag == "footer" for a in numsrc._ancestors(notes[0])) or not re.fullmatch(r"The first screen shows parts of a whole because .+\.", notes[0].text().strip()))) or (not fallback and notes):
        bad("f", "footer data-form-note: include the fallback sentence exactly when manifest form.fallback is true")
    for error in caption_digit_errors(html):
        bad("g", error)
    for error in build_guard_errors(html):
        bad("h", error)
    return out


def shipped_build_guard():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "starter.html")
    try:
        match = re.search(r'<script id="nk-build-guard">(.*?)</script>', open(path, encoding="utf-8").read(), re.S)
        return match.group(1) if match else ""
    except OSError:
        return ""


def build_guard_errors(html):
    """Require the independent shipped guard, static fallback, and draw-before-complete order.

    A file check cannot evaluate the editable data code, syntax, or the resulting DOM.
    """
    page = numsrc._Page(html)
    scripts = [n for n in page.nodes if n.tag == "script" and n.attrs.get("type") != "application/json"]
    guard = [n for n in scripts if n.attrs.get("id") == "nk-build-guard"]
    eq = next((n for n in page.nodes if n.attrs.get("id") == "sum-eq"), None)
    out = []
    if (len(guard) != 1 or not scripts or scripts[0] is not guard[0]
            or not any(a.tag == "head" for a in numsrc._ancestors(guard[0]))
            or not shipped_build_guard() or guard[0].text() != shipped_build_guard()):
        out.append("keep the shipped nk-build-guard unchanged, first in head before editable scripts")
    fallback = [n for n in page.nodes if eq and eq in numsrc._ancestors(n)
                and "bad" in (n.attrs.get("class") or "").split()]
    if not fallback or not any("Page did not build:" in n.text() for n in fallback):
        out.append("sum-eq must start with the static cross and Page did not build sentence")
    drawing = "\n".join(n.text() for n in scripts if n not in guard)
    if not re.search(r'renderStrip\(\);\s*renderTable\(\);\s*renderInspector\(\);\s*window\.nkBuild\.complete\(\);', drawing):
        out.append("complete the build only after renderStrip, renderTable and renderInspector")
    return out


MAX_TABLE_COLUMNS = 8


def table_checks(html):
    """Count authored headers and check the starter's scroll-box contract, without laying out CSS."""
    page = numsrc._Page(html)
    tables = [n for n in page.nodes if n.tag == "table"]
    css = "\n".join(n.text() for n in page.nodes if n.tag == "style")
    properties = {}
    for rule in re.findall(r"\.tablewrap\s*\{([^{}]*)\}", css):
        for declaration in rule.split(";"):
            if ":" in declaration:
                key, value = declaration.split(":", 1)
                properties[key.strip().lower()] = re.sub(r"\s+", "", value).lower()
    bounded = properties.get("min-width") in ("0", "0px") and properties.get("max-width") == "100%"
    scrolling = properties.get("overflow-x", properties.get("overflow")) in ("auto", "scroll")
    out = []
    for i, table in enumerate(tables, 1):
        wrappers = [a for a in numsrc._ancestors(table.parent) if "tablewrap" in (a.attrs.get("class") or "").split()]
        if not wrappers or not bounded or not scrolling:
            out.append(("C03", f"table {i}: use .tablewrap with min-width:0, max-width:100% and overflow-x:auto; do not clip columns"))
        if wrappers:
            wrapper = wrappers[0]
            if (not re.fullmatch(r"\d+", wrapper.attrs.get("tabindex") or "")
                    or wrapper.attrs.get("role") != "region"
                    or not (wrapper.attrs.get("aria-label") or wrapper.attrs.get("aria-labelledby"))):
                out.append(("C03", f"table {i}: give .tablewrap tabindex=0, role=region and an accessible label for keyboard scrolling"))
        for row in (n for n in page.nodes if n.tag == "tr" and next((a for a in numsrc._ancestors(n) if a.tag == "table"), None) is table):
            cells = [n for n in row.parts if isinstance(n, numsrc._Node) and n.tag in ("th", "td")]
            if not any(n.tag == "th" for n in cells): continue
            try:
                spans = [int(n.attrs.get("colspan", "1")) for n in cells]
                if any(n < 1 for n in spans): raise ValueError()
            except (ValueError, TypeError):
                out.append(("C03", f"table {i}: header colspan must be a positive integer")); continue
            columns = sum(spans)
            if columns > MAX_TABLE_COLUMNS:
                out.append(("C03", f"table {i}: {columns} authored header columns; maximum {MAX_TABLE_COLUMNS}, including Source and Actions; move extra attributes to details"))
    return out


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
    out.extend(table_checks(html))
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
    out.extend(form_checks(html))
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
GOOD = GOOD.replace('<div class="sum-strip">', '<section class="plate" data-form="split"><div class="sum-strip"><p class="sum-eq"></p>').replace('</div><table>', '</div></section><table>')
GOOD = GOOD.replace('<table>', '<div class="tablewrap" tabindex="0" role="region" aria-label="Sample rows"><table>').replace('</table>', '</table></div>')
GOOD = GOOD.replace('.x{color:var(--accent);', '.tablewrap{min-width:0;max-width:100%;overflow-x:auto;overflow-y:auto}.x{color:var(--accent);')
GOOD = GOOD.replace('</body>', """<script>/* SHAPE:start */var SHAPE = {"form":"split","unit":{"one":"row","many":"rows"},"amount":null,"parts":[{},{}],"unknownLabel":"unknown"};/* SHAPE:end */function verdict(ok){return ok ? '<span class="ok">yes</span>' : '<span class="bad">no</span>';}</script></body>""")
_SRC = numsrc.Sources("sample", not_checked=["The sample is invented."])
_SRC.add("rows", "Input rows", [{"text": "the sample's rows"}], "computation", "count of every row", ["Nothing was checked."], value="5")
_DATA = _SRC.to_dict()
_DATA["form"] = {"name": "split", "row_is": "one sample row", "why": "question 4: parts of a whole", "also_fits": [], "fallback": False}
for ident in fixed_form_ids(shape_block(GOOD)):
    _DATA["sources"][ident] = dict(_DATA["sources"]["rows"], live=True)
GOOD = numsrc.inject(GOOD.replace("3 + 2 = 5", '3 + 2 = <b data-nk-src="rows">5</b>'), _DATA)
GOOD = GOOD.replace('<head>', '<head><script id="nk-build-guard">' + shipped_build_guard() + '</script>', 1)
GOOD = GOOD.replace('<p class="sum-eq"></p>', '<p class="sum-eq" id="sum-eq"><span class="bad">Page did not build: drawing has not completed.</span></p>')
GOOD = GOOD.replace('</body>', '<script>renderStrip(); renderTable(); renderInspector(); window.nkBuild.complete();</script></body>')


def starter_label(skill_md, starter_html):
    """(the version the starter's generator label states, the version SKILL.md states); None for one that is not there.
    The label is hand-typed in assets/starter.html, and 0.1.9 shipped with one that still said 0.1.8."""
    label = re.search(r'"generator":\s*"nk-design (\d+\.\d+\.\d+) starter"', starter_html)
    version = re.search(r"^\s*version:\s*(\d+\.\d+\.\d+)\s*$", skill_md, re.M)
    return (label.group(1) if label else None, version.group(1) if version else None)


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")
    chk(checks(GOOD) == [], f"control page → 0 findings ({checks(GOOD)})")
    unguarded = re.sub(r'<script id="nk-build-guard">.*?</script>', '', GOOD, flags=re.S)
    chk(bool(build_guard_errors(unguarded)), "C16h: a page without an early build guard is refused")
    for label, broken in [
        ("static cross", GOOD.replace('class="bad">Page did not build:', 'class="pending">Page did not build:')),
        ("changed guard", GOOD.replace('window.addEventListener("error",', 'window.addEventListener("other",')),
        ("early tick", GOOD.replace('renderInspector(); window.nkBuild.complete();', 'window.nkBuild.complete(); renderInspector();')),
    ]:
        chk(bool(build_guard_errors(broken)), "C16h: " + label + " mutation refused")
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
        want = {code, "C16"} if code == "C15" and 'id="nk-sources"' not in html else {code}
        chk(got == want, f"{code} sample → exactly {sorted(want)} (got {sorted(got)})")
    crowded = GOOD.replace('<th aria-sort="none"><button>Name</button></th>', '<th aria-sort="none"><button>Name</button></th>' + '<th><button>Extra</button></th>' * 8)
    chk(any(c == "C03" for c, _ in checks(crowded)), "C03 nine authored columns must go red")
    eight = GOOD.replace('<th aria-sort="none"><button>Name</button></th>', '<th aria-sort="none"><button>Name</button></th>' + '<th><button>Extra</button></th>' * 7)
    chk(not checks(eight), "C03 eight authored columns stay green")
    for label, html in [
        ("colspan counts toward the limit", GOOD.replace('<th aria-sort="none">', '<th aria-sort="none" colspan="9">')),
        ("missing scroll box", GOOD.replace('class="tablewrap"', 'class="plain"')),
        ("unbounded scroll box", GOOD.replace('max-width:100%;', '')),
        ("clipped scroll box", GOOD.replace('overflow-x:auto;', 'overflow-x:hidden;')),
        ("scroll box cannot receive keyboard focus", GOOD.replace('tabindex="0" role="region"', 'role="region"')),
    ]:
        chk(any(c == "C03" for c, _ in checks(html)), "C03 " + label + " goes red")
    form_cases = [
        ("a", GOOD.replace('data-form="split"', 'data-form="other"')),
        ("b", GOOD.replace('"row_is": "one sample row"', '"row_is": ""')),
        ("c", GOOD.replace('"unknownLabel":"unknown"', '"missingLabel":"unknown"')),
        ("d", GOOD.replace('"rec.cents": {', '"rec.missing": {')),
        ("e", GOOD.replace('class="bad">no', 'class="wrong">no')),
        ("f", GOOD.replace('"fallback": false', '"fallback": true')),
        ("g", GOOD.replace('function verdict(ok)', 'var FORMS = {waiting:{caption:function(){return "Above 120 waiting rows.";}}};function verdict(ok)')),
    ]
    for letter, html in form_cases:
        results = form_checks(html)
        chk(any(message.startswith("[" + letter + "]") for _, message in results),
            "C16" + letter + " broken condition goes red: " + str(results))
    caption_cases = [
        ("static bare caption digit", '<p id="form-caption">Above 120 rows.</p>', True),
        ("static sourced caption digit", '<p id="form-caption">Above <b data-nk-src="rec.rows">120</b> rows.</p>', False),
        ("generated sourced value and numeric source id", '<script>var FORMS={waiting:{caption:function(){return "Above " + number("rec.limit120", "120");}}};</script>', False),
        ("caption threshold condition is code, not rendered text", '<script>var FORMS={waiting:{caption:function(r){return r.waiting > 120 ? "Blocks share a scale." : "";}}};</script>', False),
        ("generated sourced markup and numeric attribute", '<script>var FORMS={waiting:{caption:function(){return \'<b data-nk-src="rec.limit120">120</b>\';}}};</script>', False),
        ("escaped generated digit remains untraced", r'<script>var FORMS={waiting:{caption:function(){return "Above \x31\u0032\x30 rows.";}}};</script>', True),
    ]
    for label, html, bad in caption_cases:
        chk(bool(caption_digit_errors(html)) == bad, "C16g " + label)
    fallback = GOOD.replace('"fallback": false', '"fallback": true').replace('<footer>', '<footer><p data-form-note>The first screen shows parts of a whole because no whole was named.</p>')
    chk(not form_checks(fallback), "C16 fallback true plus footer sentence stays green")
    chk(any(m.startswith("[f]") for _, m in form_checks(fallback.replace('"fallback": true', '"fallback": false'))), "C16f stray footer sentence goes red")
    displaced = fallback.replace('<p data-form-note>The first screen shows parts of a whole because no whole was named.</p>', '').replace('<footer>', '<p data-form-note>The first screen shows parts of a whole because no whole was named.</p><footer>')
    chk(any(m.startswith("[f]") for _, m in form_checks(displaced)), "C16f note outside footer goes red")
    components = GOOD.replace('"parts":[{},{}]', '"parts":[{},{}],"countParts":[{},{}]')
    chk(any(m.startswith("[d]") and "rec.count0" in m for _, m in form_checks(components)), "C16d separate countParts require rec.count ids")
    invalid_components = GOOD.replace('"parts":[{},{}]', '"parts":[{},{}],"countParts":"wrong"')
    chk(any(m.startswith("[c]") for _, m in form_checks(invalid_components)), "C16c countParts must be an array")
    # a line icon drawn as an SVG mask in CSS: its namespace is not a request (C09) and its path is not a phone (C12)
    svg = GOOD.replace(".x{color:var(--accent);", ".x{-webkit-mask:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
                       "viewBox='0 0 10 10'%3E%3Cpath d='M1.6 5.3 4 7.6 8.4 2.4'/%3E%3C/svg%3E\");color:var(--accent);")
    chk(svg != GOOD and checks(svg) == [], f"a line SVG icon in CSS → 0 findings ({checks(svg)})")
    # but an SVG in a data: URI still has its text read: a real-looking number hidden in it is caught
    hidden = GOOD.replace(".x{color:var(--accent);", ".x{-webkit-mask:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
                          "viewBox='0 0 10 10'%3E%3Ctext%3E+1 604 000 0000%3C/text%3E%3C/svg%3E\");color:var(--accent);")
    chk({c for c, _ in checks(hidden)} == {"C12"}, f"a number written as text inside a data: URI SVG → C12 ({checks(hidden)})")
    # the starter's generator label names the version that shipped it. First the comparison on two samples, then the two
    # real files, when this script sits in the skill folder (scripts/ beside SKILL.md and assets/starter.html); copied
    # out without both of them, there is nothing to compare and no line is added.
    stale = starter_label("metadata:\n  version: 0.1.9\n", '{"generator": "nk-design 0.1.8 starter"}')
    same = starter_label("metadata:\n  version: 0.1.9\n", '{"generator": "nk-design 0.1.9 starter"}')
    chk(stale == ("0.1.8", "0.1.9") and stale[0] != stale[1] and same[0] == same[1] == "0.1.9" and starter_label("", "{}") == (None, None),
        f"starter label sample → a stale label differs from the version, a current one equals it ({stale}, {same})")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_p, starter_p = os.path.join(root, "SKILL.md"), os.path.join(root, "assets", "starter.html")
    if os.path.exists(skill_p) and os.path.exists(starter_p):
        label, version = starter_label(open(skill_p, encoding="utf-8").read(), open(starter_p, encoding="utf-8").read())
        chk(label is not None and label == version,
            f"assets/starter.html says the version SKILL.md says (label {label}, SKILL.md {version})")
        chk(not caption_digit_errors(open(starter_p, encoding="utf-8").read()),
            "assets/starter.html captions have no untraced literal digits")
    # Shared numsrc must ignore design form metadata even on a page with a plate.
    legacy = GOOD.replace('"row_is":"one sample row"', '"row_is":""')
    # inject() uses compact JSON; confirm this is a real mutation before checking it.
    if legacy == GOOD:
        legacy = GOOD.replace('"row_is": "one sample row"', '"row_is": ""')
    chk(legacy != GOOD and not any(x[1] == "error" for x in numsrc.check(legacy)),
        "BRIEF-2 shared numsrc ignores form reason; C16 owns it")
    chk(any(m.startswith("[b]") for _, m in form_checks(legacy)),
        "C16b catches the same missing row description")
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
        digits = GOOD.replace('</body>', '<div data-nk-scope><h1>Annual dues · 2026 season</h1><p>30 members</p></div></body>')
        open(bad_p, "w", encoding="utf-8").write(digits)
        report = io.StringIO()
        with contextlib.redirect_stdout(report):
            rc_digits = main([bad_p], run_selftest=False)
        chk(not checks(digits) and rc_digits == 1 and report.getvalue().count('N06 error:') == 2
            and 'ui_check:' in report.getvalue() and 'numsrc:' in report.getvalue(),
            "single command prints both results and refuses untraced heading/sentence digits")
    return ok, lines


def main(argv, run_selftest=True):
    ok, lines = selftest() if run_selftest else (True, [])
    if "--selftest" in argv or not ok:
        print(f"ui_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    if "--wire-form" in argv:
        try:
            path = argv[argv.index("--wire-form") + 1]
            html = open(path, encoding="utf-8").read()
            wired = wire_form(html)
            open(path, "w", encoding="utf-8").write(wired)
            print("C16 wire-form: fixed ids filled; form choice and runtime preserved")
            return 0
        except (IndexError, ValueError, OSError) as exc:
            print("C16 wire-form: " + str(exc)); return 2
    files = [a for a in argv if not a.startswith("--") and a != argv[argv.index("--json") + 1] if "--json" in argv] if "--json" in argv else [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 2
    html = open(files[0], encoding="utf-8").read()
    findings = checks(html)
    sources = numsrc.check(html)
    errors = sum(level == 'error' for _, level, _ in sources)
    print(f"ui_check: {files[0]}: {len(findings)} findings")
    for c, m in findings:
        print(f"    {c}  {m}")
    print(f"numsrc: {errors} errors, {len(sources) - errors} warnings")
    for code, level, message in sources:
        print(f"    {code} {level}: {message}")
    if "--json" in argv:
        json.dump(findings + [(c, level + ': ' + m) for c, level, m in sources], open(argv[argv.index("--json") + 1], "w"), indent=1)
    return 1 if findings or errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

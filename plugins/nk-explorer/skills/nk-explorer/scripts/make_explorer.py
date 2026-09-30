#!/usr/bin/env python3
"""make_explorer.py — build a one-file interactive explainer from a concept.

    python3 make_explorer.py concept.json -o explainer.html
    python3 make_explorer.py --concept-of explainer.html > concept.json     # a built page's concept, to edit and rebuild
    python3 make_explorer.py --selftest

concept.json is the page's only input: a title and the question the page answers, one formula, the controls it reads
(sliders), the control the chart runs along, what the formula leaves out and where it comes from, and one or more
practice questions. references/concept-format.md lists every field; assets/concepts/ has worked examples.

The page is this skill's template (assets/starter.html) with the concept block replaced and the design tokens
written into it, so the result is one file that opens anywhere. Last, the page is sealed: its Content-Security-Policy
(the second line of its head) is written to allow exactly the page's own four scripts (the template's three and the number-sources runtime), by their SHA-256, and nothing
else — no file or address to load anything from (only data: images), and no string run as code. The browser enforces
it, so an outside font, a tracking pixel or an eval() added to the page later does not run, and a script changed
after sealing does not run at all. Before writing anything the concept is checked
against the rules in concept.py (E01-E07); if it breaks one, nothing is written and each problem is printed with
its code. Then run explorer_check.py (the page, read as a file) and probe_check.py (the page, running).

Exit 0 built · 1 the concept breaks a rule, nothing written · 2 usage, an unreadable file, or a template that is not
this skill's.
"""
import base64, hashlib, html as H, io, json, os, re, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import concept as K
import numsrc  # the clickable number sources layer shared with the other nk-* page skills

ASSETS = os.path.join(HERE, "..", "assets")
TEMPLATE = os.path.join(ASSETS, "starter.html")
TOKENS = os.path.join(ASSETS, "design-tokens.css")
FORMULA_JS = os.path.join(ASSETS, "formula.js")
LINK = '<link rel="stylesheet" href="design-tokens.css">'
MARKS = ("/* formula:start */", "/* formula:end */")
CSP_META = re.compile(r'<meta http-equiv="Content-Security-Policy" content="[^"]*">')
SCRIPT = re.compile(r"<script([^>]*)>(.*?)</script>", re.S)


def script_hashes(page):
    """'sha256-…' of every script the page runs (the concept block is data, not a script), in page order — the text
    between <script> and </script> exactly, as the browser hashes it"""
    return ["sha256-" + base64.b64encode(hashlib.sha256(m.group(2).encode("utf-8")).digest()).decode("ascii")
            for m in SCRIPT.finditer(page) if 'type="application/json"' not in m.group(1)]


def policy(hashes):
    """the page's Content-Security-Policy: nothing from anywhere, data: images for the CSS masks, inline styles, and
    only these scripts; no 'unsafe-eval', so no string is ever run as code"""
    return ("default-src 'none'; script-src " + " ".join(f"'{h}'" for h in hashes) +
            "; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'")


def seal(page):
    """the page with its policy written for the scripts it has now"""
    return CSP_META.sub(lambda _: '<meta http-equiv="Content-Security-Policy" content="' + policy(script_hashes(page)) + '">', page, count=1)


class TemplateError(Exception):
    pass


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def language(text):
    """the formula language between its markers, or None when the markers are not there exactly once"""
    if text.count(MARKS[0]) != 1 or text.count(MARKS[1]) != 1:
        return None
    a, b = text.index(MARKS[0]), text.index(MARKS[1]) + len(MARKS[1])
    return text[a:b] if a < b else None


def render(concept, template=None, tokens=None, formula_js=None):
    """the page for a concept — no rules applied here (the CLI applies them first); the template is checked"""
    template = read(TEMPLATE) if template is None else template
    tokens = read(TOKENS) if tokens is None else tokens
    formula_js = read(FORMULA_JS) if formula_js is None else formula_js
    lang = language(template)
    if lang is None or lang != language(formula_js):
        raise TemplateError("the template's formula language is not the one in assets/formula.js — the template was edited; restore it from the skill")
    for what, n in (("concept block", len(K.BLOCK.findall(template))), ("tokens link", template.count(LINK)),
                    ("Content-Security-Policy line", len(CSP_META.findall(template))),
                    ("<title>", len(re.findall(r"<title>.*?</title>", template))),
                    ("description", len(re.findall(r'<meta name="description" content="[^"]*">', template)))):
        if n != 1:
            raise TemplateError(f"the template has {n} of its {what}, not one — restore assets/starter.html from the skill")
    m = K.BLOCK.search(template)
    page = template[:m.start(1)] + "\n" + K.dumps(concept) + "\n" + template[m.end(1):]
    page = re.sub(r"<title>.*?</title>", lambda _: "<title>" + H.escape(concept["title"], quote=False) + "</title>", page, count=1)
    page = re.sub(r'<meta name="description" content="[^"]*">',
                  lambda _: '<meta name="description" content="' + H.escape(concept["question"]) + '">', page, count=1)
    page = numsrc.inject(page.replace(LINK, '<style id="design-tokens">\n' + tokens.strip() + "\n</style>", 1), sources(concept))
    return seal(page)


VERSION = "0.1.2"   # written into the sources manifest as the generator


def sources(concept):
    """the manifest behind the page's clickable numbers: the result and each control's readout. The numbers move
    with the sliders, so the entries are live: the page brings the result's entry up to date after every move."""
    notes = [str(n) for n in concept.get("notes") or [] if str(n).strip()]
    src = numsrc.Sources(f"nk-explorer {VERSION}", not_checked=["Whether this formula fits your own case: the page explains a concept and gives no advice."])
    r = concept["result"] if isinstance(concept.get("result"), dict) else {}
    if not r.get("name"):
        return src.add("result", "the result", [{"text": "the controls as they are set on the page"}], "formula", str(concept.get("formula")),
                       ["The concept could not be read, so nothing about this number was checked."], live=True) or src
    src.add("result", r.get("label") or r["name"], [{"text": "the controls as they are set on the page"}], "formula",
            f"{r['name']} = {concept['formula']}", (["What the formula leaves out: " + n for n in notes] or
            ["What the formula leaves out was not written down."]) + [f"Where the formula comes from: {concept.get('source', '')}".strip()],
            command="python3 scripts/make_explorer.py concept.json -o page.html", live=True)
    for c in [c for c in concept.get("controls") or [] if isinstance(c, dict) and c.get("name")]:
        src.add("control." + c["name"], f"{c.get('label') or c['name']} ({c['name']})",
                [{"text": f"set with its slider, from {c['min']} to {c['max']} in steps of {c['step']}"}], "input",
                "the slider's position: a value you choose, not a measurement",
                ["Whether this range is a sensible one for your case."], live=True)
    return src


def build(src, out):
    try:
        text = read(src)
    except OSError as e:
        print(f"cannot read {src}: {e}"); return 2
    concept, why = K.loads(text)
    if why:
        print("E01 " + why); print("nothing written"); return 1
    found = K.problems(concept)
    if found:
        for code, m in found:
            print(f"{code} {m}")
        print(f"{len(found)} problem(s); nothing written"); return 1
    try:
        page = render(concept)
    except TemplateError as e:
        print(str(e)); return 2
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(page)
    names = ", ".join(c["name"] for c in concept["controls"])
    print(f"built {out}: {concept['result']['name']} = {concept['formula']}  ·  controls {names}  ·  "
          f"{len(concept['practice'])} practice question(s)  ·  {len(page.encode('utf-8'))} bytes")
    print(f"next: python3 {os.path.join(HERE, 'explorer_check.py')} {out}  and  python3 {os.path.join(HERE, 'probe_check.py')} {out}")
    return 0


def selftest():
    import explorer_check as X
    ok = []

    def say(cond, text):
        ok.append(bool(cond)); print(f"  {'PASS' if cond else 'FAIL'}  {text}")

    starter, why = K.read(read(TEMPLATE))
    say(starter and not K.problems(starter), "the starter's own concept meets every concept rule")
    page = render(starter)
    say(not X.check_text(page), "the page built from it has no findings in explorer_check.py" +
        "".join(f"\n        {c} {m}" for c, m in X.check_text(page)))
    say(LINK not in page and page.count('<style id="design-tokens">') == 1, "the tokens are written into the page, not linked")
    hashes = script_hashes(page)
    say(len(hashes) == 4 and CSP_META.search(page).group(0) == '<meta http-equiv="Content-Security-Policy" content="' + policy(hashes) + '">'
        and "'unsafe-eval'" not in page and page.index("Content-Security-Policy") < page.index("<script"),
        "the page is sealed: its policy, ahead of every script, allows exactly its four scripts by hash (the three of the template and the number-sources runtime) and no eval")
    back, _ = K.read(page)
    say(back == starter, "the concept read back out of the built page is the concept that went in")
    examples = sorted(f for f in os.listdir(os.path.join(ASSETS, "concepts")) if f.endswith(".json"))
    for f in examples:
        c, why = K.loads(read(os.path.join(ASSETS, "concepts", f)))
        found = (["E01 " + why] if why else [f"{a} {b}" for a, b in K.problems(c)]) or [f"{a} {b}" for a, b in X.check_text(render(c))]
        say(not found, f"the example {f} builds with no findings" + "".join("\n        " + x for x in found))
    with tempfile.TemporaryDirectory() as t:
        # a note that says </script> cannot close the block early, and comes back out unchanged
        c = json.loads(json.dumps(starter))
        c["notes"] = c["notes"] + ["A page can say </script> in a note and <b>markup</b> in a note; neither is read as HTML."]
        src, out = os.path.join(t, "c.json"), os.path.join(t, "p.html")
        io.open(src, "w", encoding="utf-8").write(json.dumps(c))
        rc = subprocess.run([sys.executable, __file__, src, "-o", out], capture_output=True, text=True).returncode
        back, _ = K.read(read(out)) if rc == 0 else (None, None)
        say(rc == 0 and back == c, "a note containing </script> and markup survives the trip into the page and back")
        # a concept that breaks a rule: exit 1, and no file
        c = json.loads(json.dumps(starter))
        c["controls"].append({"name": "t", "label": "Tax", "unit": "%", "min": 0, "max": 50, "step": 1, "value": 20})
        io.open(src, "w", encoding="utf-8").write(json.dumps(c))
        out2 = os.path.join(t, "no.html")
        r = subprocess.run([sys.executable, __file__, src, "-o", out2], capture_output=True, text=True)
        say(r.returncode == 1 and not os.path.exists(out2) and "E03" in r.stdout, "a concept with a control the formula never uses is refused and nothing is written")
        # a template whose formula language was edited is refused
        bent = read(TEMPLATE).replace('if (b === 0) fail("division by zero"); ', "", 1)
        try:
            render(starter, template=bent); refused = False
        except TemplateError:
            refused = True
        say(refused and bent != read(TEMPLATE), "a template whose formula language was edited is refused")
        # a key written twice is refused rather than silently taking the last one
        io.open(src, "w", encoding="utf-8").write(json.dumps(starter).replace('"title": ', '"title": "x", "title": ', 1))
        r = subprocess.run([sys.executable, __file__, src, "-o", out2], capture_output=True, text=True)
        say(r.returncode == 1 and "appears twice" in r.stdout and not os.path.exists(out2), "a concept with a key written twice is refused")
    print(f"make_explorer selftest: {sum(ok)}/{len(ok)} passed")
    return 0 if all(ok) else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--concept-of" in argv:
        i = argv.index("--concept-of")
        if i + 1 >= len(argv):
            print(__doc__.strip().split("\n\n")[1]); return 2
        c, why = K.read(read(argv[i + 1]))
        if why:
            print(why); return 2
        print(json.dumps(c, indent=2, ensure_ascii=False)); return 0
    if "-o" not in argv or len(argv) != 3:
        print(__doc__.strip().split("\n\n")[1]); return 2
    i = argv.index("-o")
    out = argv[i + 1] if i + 1 < len(argv) else None
    src = [a for j, a in enumerate(argv) if j not in (i, i + 1)]
    if not out or len(src) != 1:
        print(__doc__.strip().split("\n\n")[1]); return 2
    return build(src[0], out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""page_check.py — the rules a booking page from this skill has to keep, checked on the file itself.

    python3 page_check.py <page.html> [<page.html> ...] [--public]
        --public: also refuse anything that would be wrong to put on the open web from a demo — a phone
        number outside the reserved 555-01xx range, a contact e-mail at a real-looking domain.
    python3 page_check.py --selftest

The rules, and the invariant each one serves (references/invariants.md):

  L01  the business data block is there and parses, and the page reads its content from it, not from the markup
  L02  demo mode is stated on the screen, and every row the outbox writes says it was not sent          (5)
  L03  no testimonials, star ratings, review counts or "trusted by" logos anywhere                      (—)
  L04  a page that says it is a demo uses a reserved 555-01xx number and an example.* e-mail            (—)
  L05  every write to the outbox happens inside the guard, the guard takes an approval, and each outbox
       row records the approval it came from                                                             (1)
  L06  the guard compares the actor, that the desk issued this very approval, the request, the revision, the
       words actually going out and the kind of action, refuses reuse — and the page carries its own
       ?probe=1 battery that exercises them                                                              (1–4)
  L07  the customer form has no control that approves; the approve buttons live in the staff view        (4)
  L08  every input has a label, the status regions announce, and focus is never removed silently        (—)
  L09  nothing is fetched from the network except the fonts the token file names                        (—)
  L10  colours come from the token file, not from raw hex in the page's own styles                      (—)
  L11  a page built for delivery is one file: no external stylesheet or script                          (—)
  L12  the footer says what is made up, and does not claim customers the page has not had               (—)

Exit 0 clean · 1 findings · 2 selftest failed or usage.
"""
import os, re, sys, json

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
PHONE_OK = re.compile(r"\b555-01\d{2}\b")
PHONE_ANY = re.compile(r"(?<![\d.\-/])(?:\+\d{1,3}[ -]?)?(?:\(\d{3}\)[ -]?|\d{3}[ -])?\d{3}[ -]\d{4}(?![\d.\-/])")
MAIL_ANY = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
MAIL_OK = re.compile(r"@(?:example\.(?:com|org|net)|[\w-]+\.example)\b")
SOCIAL = re.compile(r"(?i)★|✩|⭐|\b\d(?:\.\d)?\s*/\s*5\b|\btrusted by\b|\btestimonial|\bratings?\b|\breviews?\b|\b\d[\d,]*\+? (?:happy )?(?:customers|clients)\b")
# What the guard compares, read from its code rather than from its messages: a message can say "not the text that
# was approved" while the code compares the approval with the request's draft instead of with what goes out — an
# earlier version's bug. These patterns follow the template's guard; ?probe=1 is the behavioural test.
REFUSALS = [("the actor", r"actor\s*!==\s*.staff."),
            # the same object the desk issued, not merely an id the desk has seen: a copy under a real id with other
            # words passes an id-only check (0.1.1)
            ("that the desk issued this very approval", r"issued\[approval\.id\]\s*!==\s*approval\b"),
            ("the request the approval belongs to", r"approval\.requestId\s*!==\s*r\.id"),
            ("the revision", r"approval\.rev\s*!==\s*r\.rev"),
            ("the words actually going out", r"action\.text\s*!=="),
            ("the kind of action", r"KINDS\.hasOwnProperty\(action\.kind\)"),
            ("reuse", r"state\.spent\[")]
TOKENS_HREF = re.compile(r'<link[^>]+href="([^"]*design-tokens\.css)"')
EXT_URL = re.compile(r'(?:src|href)="(https?://[^"]+)"')
FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def read(path):
    return open(path, encoding="utf-8").read()


def business_block(html):
    m = re.search(r'<script type="application/json" id="business">(.*?)</script>', html, re.S)
    if not m:
        return None, "no business data block"
    try:
        return json.loads(m.group(1)), None
    except Exception as e:
        return None, f"the business data block does not parse: {e}"


def function_span(js, name):
    """The source of `function name(...)`, by counting braces. Good enough for one file written by this skill;
    it is used to answer one question — is this line inside that function — not to understand JavaScript."""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\(", js)
    if not m:
        return None
    i = js.index("{", m.end() - 1)
    depth, j = 0, i
    while j < len(js):
        if js[j] == "{":
            depth += 1
        elif js[j] == "}":
            depth -= 1
            if depth == 0:
                return (i, j)
        j += 1
    return None


def style_blocks(html):
    """The page's own styles. The token file, when it is inlined for delivery, is a <style id="design-tokens">
    block and is not the page's own — it is where the colours are supposed to live."""
    return "\n".join(body for tag, body in re.findall(r"<style([^>]*)>(.*?)</style>", html, re.S)
                     if 'id="design-tokens"' not in tag)


def check(path, public=False):
    html = read(path)
    out = []
    add = lambda code, msg: out.append((code, msg))

    biz, err = business_block(html)
    if err:
        add("L01", err)
    else:
        for field in ("name", "services", "faq", "slots"):
            if field not in biz:
                add("L01", f"the business block has no `{field}`")
        if 'getElementById("business")' not in html and "getElementById('business')" not in html:
            add("L01", "the data block is never read: the page renders from its markup, so editing the block changes nothing")

    demo = bool(biz.get("demo")) if biz else False
    if demo:
        if not re.search(r"(?i)demo mode", html):
            add("L02", "the page says demo in its data but never on the screen")
        if "not sent" not in html:
            add("L02", "nothing in the outbox says it was not sent")
    if SOCIAL.search(re.sub(r"(?i)no reviews[^.]*\.|\breviews?, ratings", "", html)):
        add("L03", "social proof on a page that has not earned any: " + (SOCIAL.search(html).group(0)))

    if demo or public:
        for m in PHONE_ANY.finditer(html):
            if not PHONE_OK.search(m.group(0)):
                add("L04", f"a phone number outside the reserved 555-01xx range: {m.group(0)}")
        for m in MAIL_ANY.finditer(html):
            if not MAIL_OK.search(m.group(0)):
                add("L04", f"a contact e-mail at a real-looking domain: {m.group(0)}")

    js = "\n".join(re.findall(r"<script(?![^>]*application/json)[^>]*>(.*?)</script>", html, re.S))
    span = function_span(js, "commit")
    if not span:
        add("L05", "no guard: the page has no commit() that outbound actions pass through")
    else:
        inside = js[span[0]:span[1]]
        if "approval" not in js[max(0, span[0] - 120):span[0]]:
            add("L05", "the guard does not take an approval")
        pushes = [m.start() for m in re.finditer(r"outbox\.push\(", js)]
        outside = [p for p in pushes if not (span[0] < p < span[1])]
        if not pushes:
            add("L05", "nothing ever writes to the outbox")
        if outside:
            add("L05", f"{len(outside)} write(s) to the outbox happen outside the guard")
        if pushes and not re.search(r"outbox\.push\(\{[^}]*approval:\s*approval\.id", inside):
            add("L05", "an outbox row does not record the approval it came from")
        for name, pattern in REFUSALS:
            if not re.search(pattern, inside):
                add("L06", f"the guard never checks {name}")
        # the record the desk keeps must have no prototype, or "constructor" and "toString" are already in it
        if re.search(r"issued\s*:", js) and not re.search(r"issued\s*:\s*(?:Object\.create\(\s*null\s*\)|new\s+Map\b)", js):
            add("L06", "the desk's record of issued approvals is a plain object: inherited names like 'constructor' read as issued")
        if not (re.search(r"probe=1", js) and "guard-probe" in js):
            add("L06", "no ?probe=1 battery: nothing in the page exercises the guard against the cases it exists for")

    form = re.search(r"<form[^>]*>(.*?)</form>", html, re.S)
    if not form:
        add("L07", "no booking form")
    elif re.search(r"(?i)approve", form.group(1)):
        add("L07", "the customer form carries an approve control")
    if not re.search(r"(?i)>\s*approve", html):
        add("L07", "no approve control anywhere: nothing can reach the outbox")

    for m in re.finditer(r"<(input|select|textarea)\b[^>]*>", html):
        tag = m.group(0)
        ident = re.search(r'id="([^"]+)"', tag)
        labelled = (html.count(f'for="{ident.group(1)}"') if ident else 0) or \
                   re.search(r"aria-label", tag) or \
                   (html.rfind("<label", 0, m.start()) > html.rfind("</label>", 0, m.start()))
        if not labelled:
            add("L08", f"an input with no label: {tag[:60]}")
    if "aria-live" not in html:
        add("L08", "no live region: a status that changes is never announced")
    css = style_blocks(html)
    if re.search(r"outline\s*:\s*(none|0)", css) and ":focus-visible" not in css:
        add("L08", "focus outline removed without putting one back")

    for m in EXT_URL.finditer(html):
        if not any(h in m.group(1) for h in FONT_HOSTS):
            add("L09", f"the page fetches something at load: {m.group(1)[:70]}")
    hexes = [h for h in HEX.findall(css)]
    if hexes:
        add("L10", f"{len(hexes)} raw colour(s) in the page's own styles instead of tokens: {', '.join(hexes[:4])}")

    single = "--single" in sys.argv
    if single or not TOKENS_HREF.search(html):
        for m in re.finditer(r'<link[^>]+rel="stylesheet"[^>]*>|<script[^>]+src="[^"]+"', html):
            add("L11", f"a delivered page must be one file: {m.group(0)[:70]}")

    foot = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.S)
    if not foot:
        add("L12", "no footer: nothing says what is made up")
    text = re.sub(r"<[^>]+>", " ", foot.group(1)) if foot else ""
    if foot and not re.search(r"(?i)made up|fictional|invented|demo", text):
        add("L12", "the footer does not say the business and its numbers are made up")
    return out


# ---------------------------------------------------------------- selftest

def minimal(**over):
    """A tiny page that passes every rule, so each sample can break exactly one thing."""
    biz = {"name": "Ash & Co", "services": [{"name": "Repair", "price": "$20", "note": "n"}],
           "faq": [{"q": "q", "a": "a"}], "slots": ["Tue 09:30"], "demo": True}
    biz.update(over.pop("biz", {}))
    for k in over.pop("biz_del", []):
        biz.pop(k, None)
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title>
<link rel="stylesheet" href="design-tokens.css">
<style>body { color: var(--text); } :focus-visible { outline: 2px solid var(--focus); }</style></head>
<body><p>Demo mode. Nothing is sent.</p>
<form><label for="n">Name</label><input id="n"></form>
<div id="desk"><button type="button">Approve and send</button></div>
<ul id="outbox"></ul><p id="s" aria-live="polite">waiting</p>
<footer><p>The business and its prices are made up. Call 555-0142 or write to hello@ash.example.</p></footer>
<script type="application/json" id="business">__BIZ__</script>
<script>
var BIZ = JSON.parse(document.getElementById("business").textContent);
var state = { outbox: [], spent: {}, issued: Object.create(null) };
var KINDS = { message: 1, calendar: 1 };
function commit(action, approval) {
  var r = state.requests[0];
  if (!approval || approval.actor !== "staff") return refuse("approvals come from the staff desk, not from the form");
  if (state.issued[approval.id] !== approval) return refuse("the staff desk did not issue this approval");
  if (!KINDS.hasOwnProperty(action.kind)) return refuse("an approval covers two kinds of action");
  if (approval.requestId !== r.id) return refuse("another request's approval");
  if (approval.rev !== r.rev) return refuse("the request changed after it was approved");
  if (action.text !== approval.message) return refuse("the text going out is not the text that was approved");
  if (state.spent[approval.id]) return refuse("already used");
  state.spent[approval.id] = true;
  state.outbox.push({ text: action.text, approval: approval.id, note: "not sent" });
  return true;
}
if (/[?&]probe=1/.test(location.search)) { document.body.appendChild(Object.assign(document.createElement("pre"), { id: "guard-probe" })); }
</script></body></html>"""
    page = page.replace("__BIZ__", json.dumps(biz))
    for old, new in over.pop("sub", []):
        assert page.count(old) == 1, old
        page = page.replace(old, new, 1)
    return page


def selftest():
    import tempfile
    cases = [
        ("clean", {}, set()),
        ("L01 no data block", {"sub": [('<script type="application/json" id="business">', '<script type="application/json" id="other">')]}, {"L01"}),
        ("L01 missing field", {"biz_del": ["slots"]}, {"L01"}),
        ("L01 the block is never read", {"sub": [('var BIZ = JSON.parse(document.getElementById("business").textContent);\n', "")]}, {"L01"}),
        ("L02 demo only in the data", {"sub": [("<p>Demo mode. Nothing is sent.</p>", "<p>Welcome.</p>")]}, {"L02"}),
        ("L02 outbox never says not sent", {"sub": [('note: "not sent"', 'note: "sent"')]}, {"L02"}),
        ("L03 star rating", {"sub": [("<footer>", "<p>Rated 5/5 by our customers</p><footer>")]}, {"L03"}),
        # the two values below have to trip this rule and must still be safe to publish inside a checker that
        # anyone can read: 020 7946 0123 is in the UK range reserved for fiction, and .test is a top-level domain
        # reserved for testing; it never resolves in public DNS (RFC 2606). Neither can reach a person; both are
        # outside what this page's rule allows, which is the point — L04 is this page's convention, not a guess at
        # what is real.
        # (An earlier sample used parcel-example.com, which an audit found is simply unregistered — anyone could buy it.)
        ("L04 a number outside the reserved range", {"sub": [("555-0142", "020 7946 0123")]}, {"L04"}),
        ("L04 an e-mail outside the example domains", {"sub": [("hello@ash.example", "hello@parcel.test")]}, {"L04"}),
        ("L05 no guard", {"sub": [("function commit(action, approval) {", "function send(action) {")]}, {"L05"}),
        ("L05 a write outside the guard", {"sub": [("</script></body>", "<script>state.outbox.push({text:'x'});</script></body>")]}, {"L05"}),
        ("L05 a row that does not say which approval sent it", {"sub": [("approval: approval.id, ", "")]}, {"L05"}),
        ("L05 a guard that takes no approval", {"sub": [("function commit(action, approval) {", "function commit(action, grant) {\n  var approval = grant;")]}, {"L05"}),
        ("L05 nothing ever reaches the outbox", {"sub": [('  state.outbox.push({ text: action.text, approval: approval.id, note: "not sent" });', '  // rows would say not sent')]}, {"L05"}),
        ("L06 no actor check", {"sub": [('if (!approval || approval.actor !== "staff") return refuse("approvals come from the staff desk, not from the form");', 'if (!approval) return refuse("no approval");')]}, {"L06"}),
        ("L06 no check that the desk issued the approval", {"sub": [('  if (state.issued[approval.id] !== approval) return refuse("the staff desk did not issue this approval");\n', "")]}, {"L06"}),
        ("L06 the record of issued approvals is a plain object", {"sub": [("issued: Object.create(null)", "issued: {}")]}, {"L06"}),
        ("L06 checks only that the id was issued", {"sub": [("if (state.issued[approval.id] !== approval)", "if (!state.issued[approval.id])")]}, {"L06"}),
        ("L06 no revision check", {"sub": [('  if (approval.rev !== r.rev) return refuse("the request changed after it was approved");\n', "")]}, {"L06"}),
        ("L06 no reuse check", {"sub": [('  if (state.spent[approval.id]) return refuse("already used");\n', ""), ("state.spent[approval.id] = true;", "")]}, {"L06"}),
        ("L06 compares the draft, not what goes out (an earlier version's bug)", {"sub": [("if (action.text !== approval.message)", "if (approval.message !== draftFor(r))")]}, {"L06"}),
        ("L06 any kind of action goes", {"sub": [('  if (!KINDS.hasOwnProperty(action.kind)) return refuse("an approval covers two kinds of action");\n', "")]}, {"L06"}),
        ("L06 another request's approval goes", {"sub": [('  if (approval.requestId !== r.id) return refuse("another request\'s approval");\n', "")]}, {"L06"}),
        ("L06 no probe battery", {"sub": [('if (/[?&]probe=1/.test(location.search)) { document.body.appendChild(Object.assign(document.createElement("pre"), { id: "guard-probe" })); }\n', "")]}, {"L06"}),
        ("L07 approve on the form", {"sub": [("<form><label", '<form><button type="button">Approve</button><label')]}, {"L07"}),
        ("L07 no approve control anywhere", {"sub": [('<button type="button">Approve and send</button>', '<button type="button">Send</button>')]}, {"L07"}),
        ("L08 unlabelled input", {"sub": [('<label for="n">Name</label><input id="n">', '<input id="n">')]}, {"L08"}),
        ("L08 no live region", {"sub": [('aria-live="polite"', 'class="x"')]}, {"L08"}),
        ("L08 focus removed", {"sub": [(":focus-visible { outline: 2px solid var(--focus); }", "button { outline: none; }")]}, {"L08"}),
        ("L09 an outside request", {"sub": [("<body>", '<body><img src="https://cdn.example.net/tracker.gif">')]}, {"L09"}),
        ("L10 a raw colour", {"sub": [("body { color: var(--text); }", "body { color: #3a7bd5; }")]}, {"L10"}),
        ("L10 the inlined token block is not the page's own styles",
         {"sub": [('<link rel="stylesheet" href="design-tokens.css">', '<style id="design-tokens">:root { --text: #1d1b24; --focus: #ca6980; }</style>')]}, set()),

        ("L12 no footer", {"sub": [("<footer><p>The business and its prices are made up. Call 555-0142 or write to hello@ash.example.</p></footer>", "")]}, {"L12"}),
        ("L12 footer says nothing", {"sub": [("The business and its prices are made up.", "Come and see us.")]}, {"L12"}),
    ]
    ok = True
    with tempfile.TemporaryDirectory() as t:
        for name, over, want in cases:
            p = os.path.join(t, "p.html")
            open(p, "w", encoding="utf-8").write(minimal(**over))
            got = {c for c, _ in check(p)}
            good = got == want
            ok = ok and good
            print(f"  {'✔' if good else '✘'} {name} → want {sorted(want) or ['clean']}, got {sorted(got) or ['clean']}")
        # a page that is not a demo is judged on its contacts only when it is going public
        p = os.path.join(t, "p.html")
        open(p, "w", encoding="utf-8").write(minimal(biz={"demo": False}, sub=[("555-0142", "020 7946 0123"), ("<p>Demo mode. Nothing is sent.</p>", "<p>Book below.</p>")]))
        quiet = {c for c, _ in check(p)}
        loud = {c for c, _ in check(p, public=True)}
        good = quiet == set() and loud == {"L04"}
        ok = ok and good
        print(f"  {'✔' if good else '✘'} L04 a live page with a non-reserved number, under --public → want ['L04'] only with the flag, got {sorted(quiet) or ['clean']} / {sorted(loud) or ['clean']}")
        # the single-file rule needs the flag, so it gets its own run
        p = os.path.join(t, "p.html")
        open(p, "w", encoding="utf-8").write(minimal())
        sys.argv.append("--single")
        got = {c for c, _ in check(p)}
        sys.argv.remove("--single")
        good = got == {"L11"}
        ok = ok and good
        print(f"  {'✔' if good else '✘'} L11 an external stylesheet with --single → want ['L11'], got {sorted(got) or ['clean']}")
    print(f"page_check selftest · {'all' if ok else 'NOT all'} samples behaved as written ({len(cases) + 2} cases)")
    return 0 if ok else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    pages = [a for a in argv if not a.startswith("--")]
    if not pages:
        print(__doc__.strip()); return 2
    bad = 0
    for p in pages:
        found = check(p, public="--public" in argv)
        bad += bool(found)
        print(("✘ " if found else "✔ ") + f"{os.path.basename(p)}: {len(found)} findings")
        for code, msg in found:
            print(f"    {code} {msg}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

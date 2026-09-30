#!/usr/bin/env python3
"""probe_check.py — open an nk-explorer page in Chrome with ?probe=1 and check what it did against the Python twin.

    python3 probe_check.py page.html [--chrome /path/to/chrome]
    python3 probe_check.py --selftest

explorer_check.py reads the page as a file. This opens it. With ?probe=1 the page moves every control through its
real slider, types answers into its practice questions and presses their Check buttons, and writes what it saw
into <pre id="explorer-probe">. This script reads that and recomputes it with formula.py and concept.py:
  P1  wiring: every move of every control changes the formula line and the chart and marks the number that moved,
      and each control changes the result on at least one of its moves
  P2  the numbers: at every state the page recorded, the formula written with names and with values, the result
      (or the reason it has none) and each control's readout are exactly what the Python twin writes
  P3  compute questions: the page's answer is Python's; the right answer passes typed three ways (plainly, to four
      places, with the unit) and half a tolerance off; two tolerances off and an empty answer fail; "Show it on the
      controls" puts the question's values on the sliders
  P4  reach questions: the page finds the same first passing and first failing setting as Python; set on the real
      sliders and checked, the passing one passes with the fixed controls locked, the failing one fails, one step
      past a lowest or highest answer fails, and so does the first setting further on where the goal is met again
      (a curve that turns back — a ball passes 15 m going up and coming down — must not be graded one step at a time)
A person can see the same report by opening page.html?probe=1 in any browser (it is at the foot of the page).

Needs Google Chrome or Chromium (--chrome names one; if that path is not there, the script says so rather than using
another). Inside an agent's sandbox Chrome's own sandbox often cannot start — it says so, it dies, or it prints
nothing at all — and it then runs once more with --no-sandbox and says so. Some agent sandboxes do not let Chrome
start at all; then the script says that Chrome could not run, and that nothing is known about the page, rather than
blaming the page. A Chrome that ran but printed nothing, not even an empty page, is Chrome's failure too. Exit 0 everything behaved · 1 something did not · 2 no Chrome, Chrome could not run, no report, or the
selftest failed.
"""
import hashlib, html as H, io, json, os, re, shutil, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import concept as K
import formula as F

CANDIDATES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
NOTES = []
LAST = {"exit": None, "empty": False}   # how the last Chrome run ended: 0, its exit code (negative: the signal that ended it),
                                        # or "timeout"; and whether it printed nothing at all


def find_chrome(given=None):
    """the Chrome to use: the one named with --chrome (and no other, if that one is not there), or the first found"""
    for c in [given] if given else CANDIDATES:
        if c and (os.path.isfile(c) or shutil.which(c)):
            return c if os.path.isfile(c) else shutil.which(c)
    return None


def dump(binary, url, no_sandbox=False):
    prof = tempfile.mkdtemp(prefix="explorer-probe-")
    try:
        extra = ["--no-sandbox"] if no_sandbox else []
        try:
            return subprocess.run([binary, "--headless", "--no-first-run", "--disable-gpu", f"--user-data-dir={prof}"] + extra +
                                  ["--window-size=1280,900", "--virtual-time-budget=10000", "--dump-dom", url],
                                  capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess([binary], "timeout", "", "")
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def report(binary, page):
    """the page's own report, or None. PROBE_CACHE (a directory) keeps reports by the page's hash, for the break matrix,
    which changes this script and not the pages"""
    cache = os.environ.get("PROBE_CACHE")
    key = hashlib.sha256(open(page, "rb").read() + binary.encode()).hexdigest()
    if cache and os.path.exists(os.path.join(cache, key)):
        kept = json.loads(open(os.path.join(cache, key), encoding="utf-8").read())
        LAST["exit"], LAST["empty"] = kept["exit"], kept.get("empty", False)
        NOTES.extend(kept.get("notes", []))
        return kept["report"]
    url = "file://" + os.path.abspath(page) + "?probe=1"
    before = len(NOTES)
    r = dump(binary, url)
    blocks = re.findall(r'<pre id="explorer-probe">(\{.*?)</pre>', r.stdout or "", re.S)
    # Chrome's own sandbox often cannot start inside an agent's sandbox: it says so, or it simply dies (Codex's
    # sandbox, 2026-09-23: signal 6 and not a word). Either way it gets one more try without its sandbox.
    if not blocks and (r.returncode != 0 or not (r.stdout or "").strip() or "Failed to initialize sandbox" in (r.stderr or "") + (r.stdout or "")):
        r = dump(binary, url, no_sandbox=True)
        blocks = re.findall(r'<pre id="explorer-probe">(\{.*?)</pre>', r.stdout or "", re.S)
        if blocks:
            NOTES.append("Chrome's own sandbox would not start here, so it ran again with --no-sandbox (the page is your own file)")
    LAST["exit"], LAST["empty"] = r.returncode, not (r.stdout or "").strip()
    # the last match is the element; an earlier one can be text in the page that mentions it
    rep = json.loads(H.unescape(blocks[-1])) if blocks else None
    if cache:
        os.makedirs(cache, exist_ok=True)
        open(os.path.join(cache, key), "w", encoding="utf-8").write(json.dumps({"report": rep, "exit": r.returncode, "empty": LAST["empty"], "notes": NOTES[before:]}))
    return rep


def same(a, b):
    """two numbers the page and Python both computed: equal, or within a relative 1e-12 (Math.pow and ** may differ in
    the last bit)"""
    return a == b or (isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= 1e-12 * max(abs(a), abs(b)))


def same_state(a, b):
    return (a is None) == (b is None) and (a is None or (set(a) == set(b) and all(same(a[k], b[k]) for k in a)))


def judge(concept, rep):
    """[(check, passed, text)] for a page's report"""
    out = []
    tree = F.parse(concept["formula"])
    names = [c["name"] for c in concept["controls"]]
    if rep.get("formula") != concept["formula"]:
        return [("P0", False, f"the report is for the formula {rep.get('formula')!r}, not this page's {concept['formula']!r}")]
    # P1 wiring
    rows = {r["name"]: r["tries"] for r in rep.get("controls", [])}
    for c in concept["controls"]:
        tries = rows.get(c["name"])
        if not tries:
            out.append(("P1", False, f"{c['name']}: the probe did not move it")); continue
        unmarked = [F.fmt(t["to"]) for t in tries if not (t["with"] and t["marked"])]
        still = [F.fmt(t["to"]) for t in tries if not t["chart"]]
        changed = sum(1 for t in tries if t["out"])
        wrong = []
        if unmarked:
            wrong.append(f"moved to {', '.join(unmarked)}, the formula line did not show the new value, marked")
        if still:
            wrong.append(f"moved to {', '.join(still)}, the chart did not change")
        if not changed:
            wrong.append(f"none of its {len(tries)} moves changed the result shown")
        out.append(("P1", not wrong, f"{c['name']}: " + ("; ".join(wrong) if wrong else
                    f"{len(tries)} moves, each changed the formula line and the chart and marked itself; {changed} changed the result")))
    # P2 the numbers
    states = rep.get("states", [])
    want_n = 1 + 3 * len(names) + 2
    bad = []
    for i, s in enumerate(states):
        v = s["values"]
        if sorted(v) != sorted(names):
            bad.append(f"state {i}: controls {sorted(v)}"); continue
        for c in concept["controls"]:
            n = c["name"]
            raw, readout = s["shown"][n]
            if not K.on_grid(c, v[n]) or not same(float(raw), v[n]):
                bad.append(f"state {i}: {n} is {v[n]!r} but its slider says {raw}")
            if readout != K.with_unit(v[n], c):
                bad.append(f"state {i}: {n}'s readout says {readout!r}, Python writes {K.with_unit(v[n], c)!r}")
        if s["sym"] != F.write(tree):
            bad.append(f"state {i}: the formula line says {s['sym']!r}, Python writes {F.write(tree)!r}")
        if s["with"] != F.write(tree, v):
            bad.append(f"state {i}: the line with values says {s['with']!r}, Python writes {F.write(tree, v)!r}")
        try:
            r = F.evaluate(tree, v)
            if s["out"] != F.fmt(r) or s["err"]:
                bad.append(f"state {i}: the result says {s['out']!r} {s['err']!r}, Python gets {F.fmt(r)!r}")
        except F.FormulaError as e:
            if s["out"] != "no value" or s["err"] != f"Here the formula has no value: {e}.":
                bad.append(f"state {i}: the result says {s['out']!r} {s['err']!r}, Python finds no value ({e})")
    if len(states) != want_n:
        bad.append(f"the probe recorded {len(states)} states, not the {want_n} it should")
    out.append(("P2", not bad, "; ".join(bad[:4]) + (f" (and {len(bad) - 4} more)" if len(bad) > 4 else "") if bad else
                f"{len(states)} states: every formula line, result and readout is what the Python twin writes"))
    # P3 and P4 the practice questions
    prac = {p["task"]: p for p in rep.get("practice", [])}
    for i, t in enumerate(concept["practice"]):
        p = prac.get(i)
        label = f"question {i + 1} ({t['type']})"
        if not p or p.get("type") != t["type"]:
            out.append(("P3" if t["type"] == "compute" else "P4", False, f"{label}: the probe did not try it")); continue
        if t["type"] == "compute":
            want = F.evaluate(tree, t["set"])
            fails = []
            if not same(p.get("want"), want):
                fails.append(f"the page's answer {p.get('want')!r} is not Python's {want!r}")
            if p.get("right") is not True:
                fails.append("the answer as the page writes it did not pass")
            if p.get("other_form") is not True:
                fails.append("the answer to four decimal places did not pass")
            if p.get("with_unit") is not True:
                fails.append("the answer typed with its unit did not pass")
            if p.get("inside") is not True:
                fails.append("an answer half a tolerance off did not pass")
            if p.get("near_miss") is not False:
                fails.append("an answer two tolerances off passed")
            if p.get("blank") is not False:
                fails.append("an empty answer passed")
            if p.get("show_sets") is not True:
                fails.append("Show it on the controls did not put the question's values on the sliders")
            out.append(("P3", not fails, f"{label}: " + ("; ".join(fails) if fails else
                        f"answer {F.fmt(want)}; passes typed three ways and half a tolerance off, fails two tolerances off and empty; Show sets the controls")))
        else:
            hit, miss = K.reach_search(concept, tree, t)
            fails = []
            if not same_state(p.get("hit"), hit):
                fails.append(f"the page's first passing setting {p.get('hit')} is not Python's {hit}")
            if not same_state(p.get("miss"), miss):
                fails.append(f"the page's first failing setting {p.get('miss')} is not Python's {miss}")
            if p.get("right") is not True:
                fails.append("the passing setting, checked on the page, did not pass")
            if p.get("locked") is not True:
                fails.append("Check did not lock the question's fixed controls at their values")
            if p.get("miss_passes") is not False:
                fails.append("the failing setting, checked on the page, passed")
            side = "lowest" if t.get("lowest") else "highest" if t.get("highest") else None
            over = None
            if hit and side:
                c = K.control(concept, t[side])
                k = K.jsround((hit[c["name"]] - c["min"]) / c["step"]) + (1 if side == "lowest" else -1)
                if 0 <= k <= K.steps(c):
                    over = dict(hit, **{c["name"]: K.grid(c, k)})
            again = None
            if hit and side:
                c = K.control(concept, t[side])
                away, k0 = (1 if side == "lowest" else -1), K.jsround((hit[c["name"]] - c["min"]) / c["step"])

                def meets_at(j):
                    r = K.value_or_none(tree, dict(hit, **{c["name"]: K.grid(c, j)}))
                    return r is not None and K.meets(t, r)
                j = k0 + 2 * away
                while 0 <= j <= K.steps(c):
                    if meets_at(j) and not meets_at(j - away):
                        again = dict(hit, **{c["name"]: K.grid(c, j)})
                        break
                    j += away
            pa = p.get("again")
            if (again is None) != (pa is None) or (again is not None and not same_state(pa.get("state"), again)):
                fails.append(f"the probe did not try where the goal is met again past the {side or 'answer'} ({again}; the page tried {pa and pa.get('state')})")
            elif again is not None and pa is not None and pa.get("passes") is not False:
                fails.append(f"{t[side]} = {F.fmt(again[t[side]])} meets the goal again further on and passed; the question asks for the {side}")
            po = p.get("overshoot")
            if over is None and po is not None:
                fails.append("the probe stepped past the answer where there is nothing to step to (the end of the slider, or a question with no lowest or highest)")
            elif over is not None and (not po or not same_state(po.get("state"), over)):
                fails.append(f"the probe did not step one past the {side} answer ({over})")
            elif over is not None and (po or {}).get("passes") is not False:
                fails.append(f"one step past the {side} answer ({t[side]} = {F.fmt(over[t[side]])}) still passed")
            done = f"passes at {', '.join(f'{k} = {F.fmt(v)}' for k, v in hit.items() if k not in t['fixed'])}" if hit else ""
            out.append(("P4", not fails, f"{label}: " + ("; ".join(fails) if fails else
                        done + ", fails at the first failing setting" + (f" and one step past the {side}" if over else "") +
                        (f" and where the goal is met again ({t[side]} = {F.fmt(again[t[side]])})" if again else "") + "; the fixed controls lock")))
    return out


def run(page, binary):
    c, why = K.read(io.open(page, encoding="utf-8").read())
    if why:
        return None, why
    rep = report(binary, page)
    if not rep and (LAST["exit"] != 0 or LAST["empty"]):
        how = "did not finish within 120 seconds" if LAST["exit"] == "timeout" else \
              f"was ended by signal {-LAST['exit']}" if isinstance(LAST["exit"], int) and LAST["exit"] < 0 else \
              "printed nothing, not even an empty page," if LAST["exit"] == 0 else f"exited with {LAST['exit']}"
        return None, (f"Chrome {how} before the page could run, with and without its own sandbox: some agent sandboxes do not "
                      "let Chrome start at all. Nothing is known about the page from this. Open page.html?probe=1 in any "
                      "browser; its own summary is at the foot of the page.")
    if not rep:
        import make_explorer as M
        text = io.open(page, encoding="utf-8").read()
        sealed = M.CSP_META.search(text)
        if sealed and sealed.group(0) != '<meta http-equiv="Content-Security-Policy" content="' + M.policy(M.script_hashes(text)) + '">':
            return None, ("the page's scripts are not the ones its Content-Security-Policy names, so the browser ran none of them: "
                          "the page was changed after make_explorer.py built it (explorer_check.py E09 says so too). Build it again.")
        return None, "the page wrote no probe report — is it built by make_explorer.py from this skill's template?"
    return judge(c, rep), None


# ---- selftest ----------------------------------------------------------------------------------------------------
PROBE_IF = "if (/[?&]probe=1\\b/.test(location.search)) {"
def _example(name):
    """build the page from one of the worked examples instead of the starter"""
    def use(c):
        import make_explorer as M
        c.clear()
        c.update(K.loads(io.open(os.path.join(M.ASSETS, "concepts", name + ".json"), encoding="utf-8").read())[0])
    return use


BALL = {"title": "How high a ball thrown straight up goes", "question": "A ball thrown straight up slows down, stops and falls back. How high is it at a given moment?",
        "result": {"name": "h", "label": "Height above the hand", "unit": "m"}, "formula": "v * t - 4.9 * t^2",
        "controls": [{"name": "v", "label": "Speed it leaves the hand at", "unit": "m/s", "min": 10, "max": 30, "step": 1, "value": 20},
                     {"name": "t", "label": "Time since it was thrown", "unit": "s", "min": 0, "max": 4, "step": 0.1, "value": 2}],
        "chart": {"x": "t", "title": "Height, moment by moment"}, "notes": ["Air resistance is left out.", "Below the hand the formula goes negative; the ball would have landed."],
        "source": "the equation of motion under constant acceleration, h = v t - g t² / 2.",
        "practice": [{"type": "compute", "prompt": "Thrown up at 20 m/s: how high is it after 1.5 s?", "set": {"v": 20, "t": 1.5}, "tolerance": 0.05},
                     {"type": "reach", "prompt": "Thrown up at 20 m/s: what is the earliest time at which the ball is within 1 m of a height of 15 m?",
                      "fixed": {"v": 20}, "goal": "within", "target": 15, "tolerance": 1, "lowest": "t"}]}


def _ball(c):
    """a curve that turns back: the ball is within 1 m of 15 m at 0.9-1 s going up and at 3-3.1 s coming down"""
    c.clear()
    c.update(json.loads(json.dumps(BALL)))


def _only_at_the_end(c):
    """the reach question's only passing setting is the slider's last position, so there is no step past it"""
    c["practice"][1].update({"target": 14000, "prompt": "£1,000 at 7% a year: after how many whole years is there £14,000 or more for the first time?"})


def _no_value_at_min(c):
    c["formula"] = "P * (1 + r/100)^n / r * r"       # no value at r = 0, one of the states the probe records


# (name, the check that must go red, [(old, new) in the built page], optional change to the concept first)
BROKEN = [
    ("a report for another formula", "P0", [("var report = { formula: C.formula,", "var report = { formula: C.formula + \" \",")]),
    ("a slider that is not wired", "P1", [('input.addEventListener("input", function () {', 'if (c !== C.controls[0]) input.addEventListener("input", function () {')]),
    ("a probe that skips a control", "P1", [("report.controls.push({ name: c.name, tries: seen });", "if (c !== C.controls[C.controls.length - 1]) report.controls.push({ name: c.name, tries: seen });")]),
    ("the wrong number marked", "P1", [('(p[1] === lastChanged ? " changed" : "")', '(p[1] !== lastChanged ? " changed" : "")')]),
    ("a chart that never redraws", "P1", [("    drawChart();\n  }\n", "  }\n")]),
    ("a result that never updates", "P1", [('$("m-out").textContent = fmt(lastResult);', '$("m-out").textContent = fmt(result(start));')]),
    ("a result rounded its own way", "P2", [('$("m-out").textContent = fmt(lastResult);', '$("m-out").textContent = lastResult.toFixed(2);')]),
    ("a formula line typed by hand", "P2", [('$("m-sym").textContent = Formula.write(tree);', '$("m-sym").textContent = C.formula;')]),
    ("a line with values written its own way", "P2", [("var s = document.createElement(\"span\"); s.textContent = p[0];", "var s = document.createElement(\"span\"); s.textContent = p[0].replace(\"^\", \"**\");")]),
    ("a readout that drops the unit", "P2", [('$("c-" + c.name + "-v").textContent = withUnit(values[c.name], c);', '$("c-" + c.name + "-v").textContent = fmt(values[c.name]);')]),
    ("a value that drifts from its slider", "P2", [("values[c.name] = Number(input.value); lastChanged = c.name;", "values[c.name] = Number(input.value) * 1.0000001; lastChanged = c.name;")]),
    ("a probe that skips a state", "P2", [("reset(); C.controls.forEach(function (c) { move(c.name, c.max); }); record();", "")]),
    ("a missing value explained its own way", "P2", [('"Here the formula has no value: " + e.message + "."', '"No value."')], _no_value_at_min),
    ("a formula that goes wrong only at the question's values", "P3", [("return Math.pow(a, b);", "return b === 5 ? Math.pow(a, b) * 1.001 : Math.pow(a, b);")]),
    ("a grader that refuses exactly the page's own answer", "P3", [("if (!isFinite(a)) return { ok: false, text: \"Type a number.\" };", "if (!isFinite(a) || answer === fmt(want)) return { ok: false, text: \"Type a number.\" };")]),
    ("a grader that refuses an answer given to four decimal places", "P3", [("if (!isFinite(a)) return { ok: false, text: \"Type a number.\" };", "if (!isFinite(a) || /\\.\\d{4}$/.test(answer)) return { ok: false, text: \"Type a number.\" };")]),
    ("a grader that does not read a unit", "P3", [('s = s.replace(/[£$€¥%\\s]/g, "");', 's = s.replace(/[\\s]/g, "");'),
                                                ('[C.result.unit, C.result.unit_one].forEach(function (u) { if (u) s = s.split(u).join(""); });', "")]),
    ("a grader stricter than its tolerance", "P3", [("return Math.abs(a - want) <= t.tolerance + 1e-9", "return Math.abs(a - want) <= t.tolerance / 4 + 1e-9")]),
    ("a compute grader with a wider tolerance than it says", "P3", [("return Math.abs(a - want) <= t.tolerance + 1e-9", "return Math.abs(a - want) <= t.tolerance * 10 + 1e-9")]),
    ("a grader that passes an empty answer", "P3", [("if (!isFinite(a)) return { ok: false, text: \"Type a number.\" };", "if (!isFinite(a)) return { ok: true, text: \"Right.\" };")]),
    ("a Show button that moves the numbers and not the sliders", "P3", [("Object.keys(t.set).forEach(function (k) { values[k] = t.set[k]; inputs[k].value = t.set[k]; });", "Object.keys(t.set).forEach(function (k) { values[k] = t.set[k]; });")]),
    ("a compute grader that wants the exact text", "P3", [("return Math.abs(a - want) <= t.tolerance + 1e-9 * Math.max(1, Math.abs(want))", "return String(answer) === fmt(want)")]),
    ("a probe that skips a question", "P4", [("report.practice.push({ task: i, type: t.type, hit: hit,", "if (false) report.practice.push({ task: i, type: t.type, hit: hit,")]),
    ("a within goal graded tighter than its tolerance", "P4", [("Math.abs(r - t.target) <= t.tolerance + slack;", "Math.abs(r - t.target) <= t.tolerance * 0.64 + slack;")], _example("at-least-one-success")),
    ("a probe that walks the settings in another order", "P4", [("for (var j = 0; j <= stepsOf(c) && !(hit && miss); j++)", "for (var j = stepsOf(c); j >= 0 && !(hit && miss); j--)")]),
    ("a Check that grades the starting values, not the sliders", "P4", [("say(verdict, gradeReach(t)); });", "say(verdict, gradeReach(t, reachState({ fixed: start }))); });")]),
    ("a reach Check that does not fix the question's values", "P4", [("check.addEventListener(\"click\", function () { lock(t.fixed); state.textContent", "check.addEventListener(\"click\", function () { state.textContent")]),
    ("a Check that passes one wrong setting", "P4", [("say(verdict, gradeReach(t)); });", "say(verdict, values.n === 0 ? { ok: true, text: \"Yes.\" } : gradeReach(t)); });")]),
    ("a reach grader that forgets lowest", "P4", [('    var side = t.lowest ? "lowest" : t.highest ? "highest" : null;\n    if (side) {', '    var side = null;\n    if (side) {')]),
    ("a probe that steps two past the answer", "P4", [('k = Math.round((hit[c.name] - c.min) / c.step) + (side === "lowest" ? 1 : -1);', 'k = Math.round((hit[c.name] - c.min) / c.step) + (side === "lowest" ? 2 : -2);')]),
    ("a state with a control the page does not have", "P2", [("return { values: copy(values), shown: shown,", "return { values: Object.assign(copy(values), { zz: 1 }), shown: shown,")]),
    ("a probe that steps past the end of the slider", "P4", [("if (k >= 0 && k <= stepsOf(c)) { var o = copy(hit);", "if (true) { var o = copy(hit);")], _only_at_the_end),
    ("a reach grader that looks only one step further", "P4", [("for (var k = Math.round((v[c.name] - c.min) / c.step) + dir; k >= 0 && k <= stepsOf(c); k += dir) {",
                                                                "for (var k = Math.round((v[c.name] - c.min) / c.step) + dir, one = k; k >= 0 && k <= stepsOf(c) && k === one; k += dir) {")], _ball),
    ("a probe that never looks past the answer's stretch", "P4", [("if (meetsAt(j) && !meetsAt(j - away)) {", "if (false) {")], _ball),
]


def selftest():
    binary = find_chrome()
    if not binary:
        print("probe_check selftest: no Chrome here, nothing to test against"); return 2
    import make_explorer as M
    ok = []
    start, _ = K.read(io.open(M.TEMPLATE, encoding="utf-8").read())
    with tempfile.TemporaryDirectory() as t:
        pages = [("the starter", M.render(start))]
        for f in sorted(os.listdir(os.path.join(M.ASSETS, "concepts"))):
            if f.endswith(".json") and f != "compound-interest.json":
                c, _ = K.loads(io.open(os.path.join(M.ASSETS, "concepts", f), encoding="utf-8").read())
                pages.append((f"the example {f}", M.render(c)))
        pages.append(("the ball thrown up (a curve that turns back)", M.render(BALL)))
        for name, text in pages:
            path = os.path.join(t, "good.html"); io.open(path, "w", encoding="utf-8").write(text)
            res, why = run(path, binary)
            reds = [f"{c} {m}" for c, p, m in (res or []) if not p]
            cond = res is not None and not reds and {c for c, _, _ in res} >= {"P1", "P2", "P3", "P4"}
            ok.append(cond)
            print(f"  {'✔' if cond else '✘'} {name} behaves: {len(res or [])} checks, " + (why or "; ".join(reds) or "all pass"))
        base = M.render(start)
        for name, check, subs, *change in BROKEN:
            c = json.loads(json.dumps(start))
            for f in change:
                f(c)
            page, anchors = M.render(c), []
            for old, new in subs:
                anchors.append(page.count(old))
                page = page.replace(old, new, 1)
            page = M.seal(page)          # sealed again, as by someone who knew the policy, so the edited page runs
            path = os.path.join(t, "bad.html")
            io.open(path, "w", encoding="utf-8").write(page)
            res, why = run(path, binary)
            red = sorted({c for c, p, _ in (res or []) if not p})
            cond = all(n == 1 for n in anchors) and check in red
            ok.append(cond)
            print(f"  {'✔' if cond else '✘'} {name} → want {check} red, got {red or ['nothing red']}" + (f" ({why})" if why else "") +
                  ("" if all(n == 1 for n in anchors) else f" (anchors appear {anchors} times)"))
        path = os.path.join(t, "nobattery.html")
        io.open(path, "w", encoding="utf-8").write(M.seal(base.replace(PROBE_IF, "if (false) {", 1)))
        res, why = run(path, binary)
        cond = res is None and base.count(PROBE_IF) == 1 and "template" in (why or "")
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a page without the battery gives no report rather than a pass")
        # the same kind of edit, not sealed again: the browser holds the page to its policy and runs none of its scripts
        path = os.path.join(t, "unsealed.html")
        io.open(path, "w", encoding="utf-8").write(base.replace("/* ---- practice: graded on the result ---- */", "/* ---- practice ---- */", 1))
        res, why = run(path, binary)
        cond = res is None and "ran none of them" in (why or "")
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a page changed after it was sealed: the browser runs none of its scripts, and the script says why → {(why or '')[:50]}…")
        # a Chrome that dies before the page runs (as it did inside Codex's sandbox) is named, and the page is not blamed
        fake = os.path.join(t, "dying-chrome")
        io.open(fake, "w").write("#!/bin/sh\nkill -ABRT $$\n")
        os.chmod(fake, 0o755)
        good = os.path.join(t, "good.html"); io.open(good, "w", encoding="utf-8").write(base)
        res, why = run(good, fake)
        cond = res is None and "Chrome was ended by signal 6" in (why or "") and "template" not in (why or "")
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a Chrome that dies before the page runs is named, not the page → {(why or '')[:60]}…")
        # a Chrome that exits 0 and prints nothing at all, with and without its sandbox, is named too (2026-09-23 audit:
        # under a sandbox that could not read the page, the retry exited 0 with 0 bytes and the page was blamed)
        mute = os.path.join(t, "silent-chrome")
        io.open(mute, "w").write("#!/bin/sh\nexit 0\n")
        os.chmod(mute, 0o755)
        res, why = run(good, mute)
        cond = res is None and "Chrome printed nothing" in (why or "") and "template" not in (why or "")
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a Chrome that exits 0 and prints nothing is named, not the page → {(why or '')[:60]}…")
        cond = find_chrome(os.path.join(t, "no-such-chrome")) is None and find_chrome() is not None
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a --chrome path that is not there is not swapped for another Chrome")
        # a Chrome that dies inside its own sandbox but runs without it gets the second try, and says so
        fussy = os.path.join(t, "fussy-chrome")
        io.open(fussy, "w").write('#!/bin/sh\ncase "$*" in *--no-sandbox*) exec "$REAL_CHROME" "$@";; *) kill -ABRT $$;; esac\n')
        os.chmod(fussy, 0o755)
        os.environ["REAL_CHROME"] = binary
        NOTES.clear()
        res, why = run(good, fussy)
        cond = res is not None and all(p for _, p, _ in res) and any("--no-sandbox" in n for n in NOTES)
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a Chrome that dies only inside its own sandbox gets a second try without it → {len(res or [])} checks, {'the note says so' if NOTES else 'no note'}")
        # each reason for the second try on its own: an error exit with something printed, and Chrome's own message
        for n, (label, body) in enumerate((("fails with a message", 'echo "crashed early"; exit 1'),
                                          ("reports its sandbox failed", 'echo "Failed to initialize sandbox" >&2; echo "<html><head></head><body></body></html>"; exit 0'))):
            fake = os.path.join(t, f"fake-chrome-{n}")
            io.open(fake, "w").write('#!/bin/sh\ncase "$*" in *--no-sandbox*) exec "$REAL_CHROME" "$@";; *) ' + body + ';; esac\n')
            os.chmod(fake, 0o755)
            NOTES.clear()
            res, why = run(good, fake)
            cond = res is not None and all(p for _, p, _ in res) and any("--no-sandbox" in n for n in NOTES)
            ok.append(cond)
            print(f"  {'✔' if cond else '✘'} a Chrome that {label} inside its own sandbox gets a second try without it → {len(res or [])} checks, {'the note says so' if NOTES else 'no note'}")
        # one that exits 0 and prints nothing inside its own sandbox gets the second try as well
        quiet = os.path.join(t, "quiet-chrome")
        io.open(quiet, "w").write('#!/bin/sh\ncase "$*" in *--no-sandbox*) exec "$REAL_CHROME" "$@";; *) exit 0;; esac\n')
        os.chmod(quiet, 0o755)
        NOTES.clear()
        res, why = run(good, quiet)
        cond = res is not None and all(p for _, p, _ in res) and any("--no-sandbox" in n for n in NOTES)
        ok.append(cond)
        print(f"  {'✔' if cond else '✘'} a Chrome that prints nothing inside its own sandbox gets a second try without it → {len(res or [])} checks, {'the note says so' if NOTES else 'no note'}")
    print(f"probe_check selftest: {sum(ok)}/{len(ok)} passed")
    return 0 if all(ok) else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    given = argv[argv.index("--chrome") + 1] if "--chrome" in argv and argv.index("--chrome") + 1 < len(argv) else None
    args = [a for a in argv if not a.startswith("--") and a != given]
    if len(args) != 1:
        print(__doc__.strip().split("\n\n")[1]); return 2
    binary = find_chrome(given)
    if not binary:
        print(f"no Chrome at {given}" if given else "no Chrome or Chromium found; open the page with ?probe=1 in any browser to see its own report, or pass --chrome"); return 2
    res, why = run(args[0], binary)
    if res is None:
        print(why); return 2
    for n in NOTES:
        print("note: " + n)
    for check, passed, text in res:
        print(f"  {'✔' if passed else '✘'} {check} {text}")
    bad = sum(1 for _, p, _ in res if not p)
    print(f"{len(res) - bad}/{len(res)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

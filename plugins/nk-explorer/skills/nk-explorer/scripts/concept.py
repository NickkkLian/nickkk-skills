#!/usr/bin/env python3
"""concept.py — the concept block of an nk-explorer page and the rules it has to meet.

The page is built from one JSON block (<script type="application/json" id="concept">). make_explorer.py refuses a
concept that breaks a rule here; explorer_check.py reads the block back out of a finished page and applies the same
rules again; probe_check.py uses the grid and grading helpers to recompute what the page did. The page's own
JavaScript does the same arithmetic (grid, withUnit, gradeReach) — the probe compares the two.

    python3 concept.py concept.json      # print the problems, if any (exit 1 when there are some)
    python3 concept.py --selftest        # the arithmetic the page shares with this file; the rules themselves are
                                         # tested page by page in explorer_check.py --selftest

The rules, by code (explorer_check.py adds the page rules E08-E14):
  E01  the block: present once, valid JSON, every field there with the right type, no unknown or repeated keys
  E02  the formula: parses in the language, uses only the page's controls, and the result has a name of its own
  E04  the controls: names, ranges, a whole number of steps, a starting value on the grid, and every position shown
       exactly at six significant digits (so a readout never shows a number the page does not use)
  E03  every control changes the result shown somewhere on its range (the others where they start)
  E05  the starting values give a result, and the chart has a control for its axis and a curve to draw
  E06  compute questions: set every control on its grid, state each of those values in the prompt, and a tolerance
       no other answer passes — every position of each slider is tried, the others at the question's values, since a
       curve that turns back can bring a far position close
  E07  reach questions: fix some controls, leave one or two free, state the fixed values and the target (and the
       tolerance of a within goal) in the prompt, can be reached, and are not already reached

"States a value" is checked by pairing: every value is paired with its own number in the prompt, written in numerals,
and a number cannot stand for a value it visibly belongs elsewhere from — one written with another control's unit
(5 years is not the 5% rate), a different currency or %, or as another name's "x = 5". A number with no unit, or with
a unit word no control uses (6 metres per second squared), can stand for any value it equals. A number that only
says how to answer or which question this is stands for no value; it is recognised by where it stands (a label such
as "Task 2:" or "Question 3 of 4:", a bracket such as "(2 marks)", a precision such as "to 2 decimals" or "in 2
lines"), as set out above instruction() below, not by a list of phrasings. Names begin with a letter: _x and __proto__ are refused, since a page keeps its values in plain JavaScript
objects.
E01, E02 and E04 are gates: when one fails the later rules are not run, because they would only repeat it.
"""
import json, math, os, re, sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import formula as F

NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
PREFIX_UNITS = ("£", "$", "€", "¥")
GOALS = ("at least", "at most", "within")
MAX_CONTROLS, MAX_STEPS, MAX_SEARCH, MAX_TASKS = 6, 2000, 200000, 8
BLOCK = re.compile(r'<script type="application/json" id="concept">(.*?)</script>', re.S)

# field -> (type, required); "num" means a finite int or float that is not a bool
TOP = {"title": ("str", True), "question": ("str", True), "result": ("dict", True), "formula": ("str", True),
       "controls": ("list", True), "chart": ("dict", True), "notes": ("list", True), "source": ("str", True),
       "practice": ("list", True)}
RESULT = {"name": ("str", True), "label": ("str", True), "unit": ("str", False), "unit_one": ("str", False)}
CONTROL = {"name": ("str", True), "label": ("str", True), "unit": ("str", False), "unit_one": ("str", False), "min": ("num", True),
           "max": ("num", True), "step": ("num", True), "value": ("num", True)}
CHART = {"x": ("str", True), "title": ("str", True)}
COMPUTE = {"type": ("str", True), "prompt": ("str", True), "set": ("dict", True), "tolerance": ("num", True)}
REACH = {"type": ("str", True), "prompt": ("str", True), "fixed": ("dict", True), "goal": ("str", True),
         "target": ("num", True), "tolerance": ("num", False), "lowest": ("str", False), "highest": ("str", False)}


# ---- the arithmetic the page does too ----------------------------------------------------------------------------
def jsround(x):
    """Math.round: halves go up, not to even as Python's round() does."""
    return math.floor(x + 0.5)


def steps(c):
    return jsround((c["max"] - c["min"]) / c["step"])


def grid(c, k):
    """the k-th position of a control, to 12 significant digits (the page: Number((min + k*step).toPrecision(12)))"""
    return float("%.12g" % (c["min"] + k * c["step"]))


def on_grid(c, x):
    k = jsround((x - c["min"]) / c["step"])
    return 0 <= k <= steps(c) and abs(grid(c, k) - x) <= 1e-9 * max(1.0, abs(x))


def with_unit(x, u):
    """a currency sign in front (money with one decimal gets a second), % stuck to the number, any other unit after a
    space; u is a control or the result, and its unit_one is used for exactly 1 or -1 (the page: withUnit)"""
    unit = ((u.get("unit_one") if abs(x) == 1 and u.get("unit_one") else u.get("unit")) or "") if u else ""
    if not unit:
        return F.fmt(x)
    if unit in PREFIX_UNITS:                            # money with one decimal reads as pence: £7.50, not £7.5
        m = F.fmt(abs(x))
        return ("-" if x < 0 else "") + unit + (m + "0" if re.fullmatch(r"\d+\.\d", m) else m)
    return F.fmt(x) + ("%" if unit == "%" else " " + unit)


def value_or_none(tree, values):
    try:
        return F.evaluate(tree, values)
    except F.FormulaError:
        return None


def shown(tree, values):
    """the result line as the page shows it: the number, or 'no value'"""
    r = value_or_none(tree, values)
    return "no value" if r is None else F.fmt(r)


def control(concept, name):
    return next(c for c in concept["controls"] if c["name"] == name)


def start_values(concept):
    return {c["name"]: c["value"] for c in concept["controls"]}


def chart_xs(c):
    """the 201 points the page's chart samples along its control, whatever the control's step"""
    return [c["min"] + (c["max"] - c["min"]) * i / 200 for i in range(201)]


def meets(t, r):
    """the page's meets(): a goal counts as met within a billionth of the target, so a value the formula should hit
    exactly is not missed by a rounding error in the last bit (0.52 is 0.020000000000000018 away from 0.5)"""
    slack = 1e-9 * max(1.0, abs(t["target"]))
    if t["goal"] == "at least":
        return r >= t["target"] - slack
    if t["goal"] == "at most":
        return r <= t["target"] + slack
    return abs(r - t["target"]) <= t["tolerance"] + slack


def reach_state(concept, t, values=None):
    v = dict(values or start_values(concept))
    v.update(t["fixed"])
    return v


def grade_reach(concept, tree, t, v):
    """the page's gradeReach(): the state meets the goal, and for lowest/highest no position of that control further
    toward that end meets it too (the other controls as they are) — every position, not only the next one, since a
    curve can turn back: a ball thrown up passes 15 m on the way up and again on the way down"""
    r = value_or_none(tree, v)
    if r is None or not meets(t, r):
        return False
    side = "lowest" if t.get("lowest") else "highest" if t.get("highest") else None
    if side:
        c = control(concept, t[side])
        d = -1 if side == "lowest" else 1
        k = jsround((v[c["name"]] - c["min"]) / c["step"]) + d
        while 0 <= k <= steps(c):
            u = dict(v)
            u[c["name"]] = grid(c, k)
            r2 = value_or_none(tree, u)
            if r2 is not None and meets(t, r2):
                return False
            k += d
    return True


def reach_search(concept, tree, t):
    """the first state that passes and the first that fails, free controls in page order, each from its min up —
    the same walk as the page's probe, so the two can be compared state for state"""
    free = [c for c in concept["controls"] if c["name"] not in t["fixed"]]
    found = {"hit": None, "miss": None}

    def walk(k, v):
        if found["hit"] is not None and found["miss"] is not None:
            return
        if k == len(free):
            g = grade_reach(concept, tree, t, v)
            if g and found["hit"] is None:
                found["hit"] = dict(v)
            if not g and found["miss"] is None:
                found["miss"] = dict(v)
            return
        c = free[k]
        for j in range(steps(c) + 1):
            if found["hit"] is not None and found["miss"] is not None:
                break
            v[c["name"]] = grid(c, j)
            walk(k + 1, v)

    walk(0, reach_state(concept, t))
    return found["hit"], found["miss"]


# a number written in a prompt: a minus (or the minus sign), a currency sign, the digits with commas between groups of
# three, and whatever follows it
MENTION = re.compile(r"(?<![\w.,])(?P<s1>[-\u2212])?(?P<cur>[£$€¥])?(?P<s2>[-\u2212])?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\d]|\.\d|,\d{3})")


# A number that says how to answer, or which question this is, rather than a value the answer is worked out from. It
# is recognised by where it stands in the prompt, not by a list of phrasings, and only when no unit of the concept is
# written with it (a currency sign, % or one of the concept's unit words makes it a value), except the last two kinds:
#   a label      a capitalised word (or #) and a whole number, then ':' '.' ')' ']' or 'of M' / '/M', at the start of the prompt, of a
#                sentence or of a bracket: Task 2:, Exercise 2., Q 2:, Question 2 of 4: (the 4 too), (Part 3)
#   a bracket    that holds only a whole number and words: (2 marks), (4 s.f.), [3 points]
#   a precision  a whole number after 'to' or 'in' followed by a word, or after 'nearest': to 2 decimals,
#                correct to 4 s.f., to 2-decimal-place accuracy, answer in 2 lines, to the nearest 10
#   and any number after 'nearest', 'question', 'part' or 'step', or followed by a word for decimals or significant
#                figures, with or without a preposition (Give 2 decimals, 3 significant figures)
LABEL_START = r"(?:^|[.!?:;]\s+|\n\s*|[(\[]\s*)"
LABEL_BEFORE = re.compile(LABEL_START + r"(?:(?P<word>[A-Z][A-Za-z]{0,11})\.?\s*|#\s*)$")
LABEL_OF_BEFORE = re.compile(LABEL_START + r"(?:(?P<word>[A-Z][A-Za-z]{0,11})\.?\s*|#\s*)?\d+\s*(?:of|/)\s*$")
LABEL_END = r"(?:\s*[:)\]]|\.(?!\d)|\s*$)"
LABEL_AFTER = re.compile(r"(?:" + LABEL_END + r"|\s*(?:of|/)\s*\d+" + LABEL_END + ")")
BRACKET = re.compile(r"(?:\s*[A-Za-z][A-Za-z.\-]*)+\s*[)\]]")
PRECISION_BEFORE = re.compile(r"\b(?:to|in)\s+$", re.I)
NEAREST_BEFORE = re.compile(r"\bnearest\s*$", re.I)
WORD_AFTER = re.compile(r"\s*-?\s*[A-Za-z]")
INSTRUCTION_AFTER = re.compile(r"\s*-?\s*(?:decimal\s+places?|decimals?(?![A-Za-z])|d\.?p\.?(?![A-Za-z])|significant\s+(?:figures?|figs?|digits?)|sig\.?\s*figs?|s\.?f\.?(?![A-Za-z])|places?(?![A-Za-z])|digits?(?![A-Za-z]))", re.I)
INSTRUCTION_BEFORE = re.compile(r"\b(?:question|part|step)\s*$", re.I)


def instruction(before, number, tail, vocabulary):
    """True when a number with no unit of the concept only says how to answer or which question this is (above)"""
    if not re.fullmatch(r"\d+", number):          # labels, counts and precisions are whole numbers; 0.02 is a value
        return False
    label = LABEL_BEFORE.search(before)
    if label and LABEL_AFTER.match(tail) and (label.group("word") or "").lower() not in {u.lower() for u in vocabulary}:
        return True
    if LABEL_OF_BEFORE.search(before) and re.match(LABEL_END, tail):
        return True
    if re.search(r"[(\[]\s*$", before) and BRACKET.match(tail):
        return True
    return bool(PRECISION_BEFORE.search(before) and WORD_AFTER.match(tail))


def mentions(text, vocabulary):
    """the numbers a prompt states: [{value, unit, name}] — unit is the currency sign or % written with it, or the
    first word of the vocabulary (the concept's units) that follows it; name is set when it is written 'x = 5'"""
    found = []
    for m in MENTION.finditer(text):
        value = float(m.group("num").replace(",", "")) * (-1 if (m.group("s1") or m.group("s2")) else 1)
        tail, unit = text[m.end():], None
        if NEAREST_BEFORE.search(text[:m.start()]) or INSTRUCTION_BEFORE.search(text[:m.start()]) or INSTRUCTION_AFTER.match(tail):
            continue                # the nearest 10, question 2, 2 decimal places, 4 s.f.: even with a unit word next to it
        if m.group("cur"):
            unit = m.group("cur")
        elif re.match(r"\s?%", tail):
            unit = "%"
        else:
            for u in sorted(vocabulary, key=len, reverse=True):
                if u not in PREFIX_UNITS and u != "%" and re.match(r"\s*-?\s*" + re.escape(u) + r"(?![A-Za-z])", tail, re.I):
                    unit = u.lower(); break
        tie = re.search(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_]*)\s*=\s*$", text[:m.start()])
        if unit is None and not tie and instruction(text[:m.start()], m.group("num"), tail, vocabulary):
            continue
        found.append({"value": value, "unit": unit, "name": tie.group(1) if tie else None, "text": m.group(0)})
    return found


def unstated(text, wanted, vocabulary):
    """wanted: [(name, value, units, label)] — the ones that cannot each be paired with a number of their own in the
    prompt: equal in value, and not visibly another quantity's (another name's x = …, a unit that is not its own)"""
    ms = mentions(text, vocabulary)

    def fits(q, m):
        name, value, units, _ = q
        if abs(m["value"] - value) > 1e-9 * max(1.0, abs(value)):
            return False
        if m["name"]:
            return m["name"] == name
        return m["unit"] is None or m["unit"] in units

    pair = {}                       # mention index -> wanted index (Kuhn's augmenting paths; a handful of each)

    def place(i, seen):
        for j, m in enumerate(ms):
            if j not in seen and fits(wanted[i], m):
                seen.add(j)
                if j not in pair or place(pair[j], seen):
                    pair[j] = i
                    return True
        return False
    for i in range(len(wanted)):
        place(i, set())
    placed = set(pair.values())
    return [q[3] for i, q in enumerate(wanted) if i not in placed]


def units_of(q):
    return {u if u in PREFIX_UNITS or u == "%" else u.lower() for u in (q.get("unit"), q.get("unit_one")) if u}


def vocabulary(concept):
    return {u for q in [concept["result"]] + concept["controls"] for u in (q.get("unit"), q.get("unit_one")) if u}


# ---- reading the block ---------------------------------------------------------------------------------------------
def _no_repeats(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"the key '{k}' appears twice in one object")
        seen[k] = v
    return seen


def read(html):
    """the concept of a page: (concept, None) or (None, why not)"""
    blocks = BLOCK.findall(html)
    if len(blocks) != 1:
        return None, f"the page has {len(blocks)} concept blocks (<script type=\"application/json\" id=\"concept\">); it needs exactly one"
    return loads(blocks[0])


def loads(text):
    try:
        return json.loads(text, object_pairs_hook=_no_repeats), None
    except ValueError as e:
        return None, f"the concept block is not valid JSON: {e}"


def dumps(concept):
    """the block's text for a page: '<' written as \\u003c so no string in it can close the script element"""
    return json.dumps(concept, indent=2, ensure_ascii=False).replace("<", "\\u003c")


# ---- the rules -------------------------------------------------------------------------------------------------------
def _typed(where, obj, spec, out):
    if not isinstance(obj, dict):
        out.append(f"{where} should be an object")
        return
    for k in obj:
        if k not in spec:
            out.append(f"{where} has a field '{k}' this skill does not know (known: {', '.join(spec)})")
    for k, (kind, required) in spec.items():
        if k not in obj:
            if required:
                out.append(f"{where} has no '{k}'")
            continue
        v = obj[k]
        if kind == "num":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                out.append(f"{where}: '{k}' should be a number, not {json.dumps(v, ensure_ascii=False)}")
        elif kind == "str":
            if not isinstance(v, str) or (required and not v.strip()):
                out.append(f"{where}: '{k}' should be {'non-empty ' if required else ''}text, not {json.dumps(v, ensure_ascii=False)}")
        elif not isinstance(v, {"dict": dict, "list": list}[kind]):
            out.append(f"{where}: '{k}' should be {'an object' if kind == 'dict' else 'a list'}")


def structure(c):
    out = []
    _typed("the concept", c, TOP, out)
    if out:
        return out
    if len(c["title"]) > 90:
        out.append(f"the title is {len(c['title'])} characters; keep it to 90")
    _typed("result", c["result"], RESULT, out)
    _typed("chart", c["chart"], CHART, out)
    if not 1 <= len(c["controls"]) <= MAX_CONTROLS:
        out.append(f"there are {len(c['controls'])} controls; a page has 1 to {MAX_CONTROLS}")
    for i, ctl in enumerate(c["controls"]):
        _typed(f"controls[{i}]", ctl, CONTROL, out)
    if not c["notes"] or not all(isinstance(n, str) and n.strip() for n in c["notes"]):
        out.append("notes should be a list of one or more sentences saying what the formula leaves out")
    if not 1 <= len(c["practice"]) <= MAX_TASKS:
        out.append(f"there are {len(c['practice'])} practice questions; a page has 1 to {MAX_TASKS}")
    for i, t in enumerate(c["practice"]):
        kind = t.get("type") if isinstance(t, dict) else None
        if kind not in ("compute", "reach"):
            out.append(f"practice[{i}]: 'type' should be \"compute\" or \"reach\", not {json.dumps(kind)}")
            continue
        _typed(f"practice[{i}]", t, COMPUTE if kind == "compute" else REACH, out)
        for key in ("set", "fixed"):
            for name, v in (t.get(key) or {}).items() if isinstance(t.get(key), dict) else ():
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                    out.append(f"practice[{i}]: {key}.{name} should be a number, not {json.dumps(v, ensure_ascii=False)}")
    return out


def problems(c):
    """[(code, message)] — empty when the concept can be built"""
    if not isinstance(c, dict):
        return [("E01", "the concept should be a JSON object")]
    found = [("E01", m) for m in structure(c)]
    if found:
        return found
    names = [ctl["name"] for ctl in c["controls"]]
    # E02 the formula
    try:
        tree = F.parse(c["formula"])
    except F.FormulaError as e:
        return [("E02", f"the formula does not parse: {e}")]
    for n in F.names(tree):
        if n not in names:
            found.append(("E02", f"the formula uses '{n}', which is not a control (the controls are {', '.join(names)})"))
    rn = c["result"]["name"]
    if not NAME.match(rn) or rn in F.FUNCS:
        found.append(("E02", f"the result's name '{rn}' should be a plain name (a letter, then letters, digits or _) that is not a function"))
    elif rn in names:
        found.append(("E02", f"the result is called '{rn}', like a control; give it a name of its own"))
    if found:
        return found
    # E04 the controls
    for ctl in c["controls"]:
        n = ctl["name"]
        if not NAME.match(n) or n in F.FUNCS:
            found.append(("E04", f"'{n}' cannot be a control's name: begin with a letter, then letters, digits or _, and not a function's name"))
        if names.count(n) > 1:
            found.append(("E04", f"two controls are called '{n}'"))
        if not ctl["min"] < ctl["max"]:
            found.append(("E04", f"{n}: min {ctl['min']} should be below max {ctl['max']}"))
            continue
        if not ctl["step"] > 0:
            found.append(("E04", f"{n}: step should be above 0"))
            continue
        raw = (ctl["max"] - ctl["min"]) / ctl["step"]
        if abs(raw - jsround(raw)) > 1e-9 * max(1.0, raw):
            found.append(("E04", f"{n}: a step of {F.fmt(ctl['step'])} does not go evenly from {F.fmt(ctl['min'])} to {F.fmt(ctl['max'])}"))
            continue
        if steps(ctl) > MAX_STEPS:
            found.append(("E04", f"{n}: {steps(ctl)} steps is more than {MAX_STEPS}; use a bigger step"))
            continue
        if not on_grid(ctl, ctl["value"]):
            found.append(("E04", f"{n}: the starting value {F.fmt(ctl['value'])} is not one of the slider's positions ({F.fmt(ctl['min'])}, {F.fmt(grid(ctl, 1))}, ... {F.fmt(ctl['max'])})"))
        inexact = next((k for k in range(steps(ctl) + 1) if float(F.fmt(grid(ctl, k))) != grid(ctl, k)), None)
        if inexact is not None:
            found.append(("E04", f"{n}: the position {grid(ctl, inexact)!r} reads {F.fmt(grid(ctl, inexact))} at six significant digits, so its readout and the formula line would show a number the page does not use; choose a range and step whose positions need six digits or fewer"))
    if found:
        return found
    start = start_values(c)
    used = F.names(tree)
    # E05 (first half) the starting values give a result. E03 compares every position with the start, so when the
    # start has no value E03 is not run: each control would "never change the result" and repeat this one problem.
    try:
        F.evaluate(tree, start)
        start_ok = True
    except F.FormulaError as e:
        start_ok = False
        found.append(("E05", f"at the starting values the formula has no value ({e}); the page would open on an error"))
    # E03 every control does something
    for ctl in (c["controls"] if start_ok else []):
        n = ctl["name"]
        if n not in used:
            found.append(("E03", f"the control {n} ({ctl['label']}) is not in the formula, so moving it changes nothing"))
            continue
        seen = set()
        for k in range(steps(ctl) + 1):
            v = dict(start)
            v[n] = grid(ctl, k)
            seen.add(shown(tree, v))
            if len(seen) > 1:
                break
        if len(seen) < 2:
            found.append(("E03", f"moving {n} across its whole range never changes the result shown (always {seen.pop()}) with the other controls where they start"))
    # E05 (second half) the chart
    if c["chart"]["x"] not in names:
        found.append(("E05", f"the chart runs along '{c['chart']['x']}', which is not a control"))
    else:
        xc = control(c, c["chart"]["x"])
        pts = sum(1 for x in chart_xs(xc) if value_or_none(tree, dict(start, **{xc["name"]: x})) is not None)
        if pts < 2:
            found.append(("E05", f"along {xc['name']} the formula has a value at {pts} of the chart's points; there is no curve to draw"))
    # E06 compute questions
    for i, t in enumerate(c["practice"]):
        if t["type"] != "compute":
            continue
        where = f"practice[{i}]"
        missing = [n for n in names if n not in t["set"]]
        extra = [n for n in t["set"] if n not in names]
        if missing or extra:
            found.append(("E06", f"{where}: 'set' should give every control and nothing else" +
                          (f"; it leaves out {', '.join(missing)}" if missing else "") + (f"; {', '.join(extra)} is not a control" if extra else "")))
            continue
        off = [f"{n} = {F.fmt(t['set'][n])}" for n in names if not on_grid(control(c, n), t["set"][n])]
        if off:
            found.append(("E06", f"{where}: {', '.join(off)} is not a position of its slider, so 'Show it on the controls' could not show it"))
            continue
        vocab = vocabulary(c)
        unsaid = unstated(t["prompt"], [(n, float(t["set"][n]), units_of(control(c, n)), f"{n} = {with_unit(t['set'][n], control(c, n))}") for n in names], vocab)
        if unsaid:
            found.append(("E06", f"{where}: the question never states {', '.join(unsaid)}, though the answer is computed with it — write each value in numerals, with its unit or as name = value"))
        want = value_or_none(tree, t["set"])
        if want is None:
            found.append(("E06", f"{where}: at the values it sets the formula has no value, so there is no answer"))
            continue
        if not t["tolerance"] > 0:
            found.append(("E06", f"{where}: the tolerance should be above 0 (answers are typed, and rounded)"))
            continue
        # the nearest other answer any one slider gives: every position of each control, the others at the question's
        # values — not only the next position that changes the answer, since a curve that turns back can bring a far
        # position close (a ball is at nearly the same height at 1.5 s and at 2.6 s), and a staircase (ceil) gives the
        # same answer for several positions in a row
        near = []
        for ctl in c["controls"]:
            k0 = jsround((t["set"][ctl["name"]] - ctl["min"]) / ctl["step"])
            for k in range(steps(ctl) + 1):
                if k == k0:
                    continue
                r2 = value_or_none(tree, dict(t["set"], **{ctl["name"]: grid(ctl, k)}))
                if r2 is not None and F.fmt(r2) != F.fmt(want):
                    near.append((abs(r2 - want), ctl["name"], grid(ctl, k), r2, abs(k - k0)))
        if near and t["tolerance"] + 1e-9 * max(1.0, abs(want)) >= min(near)[0]:      # the page allows an answer the same hair
            d, n, x, r2, far = min(near)
            found.append(("E06", f"{where}: a tolerance of {F.fmt(t['tolerance'])} also passes the answer for {n} = {F.fmt(x)}, " +
                          ("one step away" if far == 1 else f"{far} steps away") + f" ({F.fmt(r2)}); keep it under {F.fmt(d)}"))
    # E07 reach questions
    for i, t in enumerate(c["practice"]):
        if t["type"] != "reach":
            continue
        where = f"practice[{i}]"
        bad = [n for n in t["fixed"] if n not in names]
        if bad:
            found.append(("E07", f"{where}: {', '.join(bad)} in 'fixed' is not a control"))
            continue
        off = [f"{n} = {F.fmt(v)}" for n, v in t["fixed"].items() if not on_grid(control(c, n), v)]
        if off:
            found.append(("E07", f"{where}: {', '.join(off)} is not a position of its slider"))
            continue
        free = [n for n in names if n not in t["fixed"]]
        if not 1 <= len(free) <= 2:
            found.append(("E07", f"{where}: it leaves {len(free)} controls free ({', '.join(free) or 'none'}); fix all but one or two"))
            continue
        if t["goal"] not in GOALS:
            found.append(("E07", f"{where}: the goal should be one of {', '.join(GOALS)}, not '{t['goal']}'"))
            continue
        if t["goal"] == "within" and not (isinstance(t.get("tolerance"), (int, float)) and t["tolerance"] > 0):
            found.append(("E07", f"{where}: a 'within' goal needs a tolerance above 0"))
            continue
        if t["goal"] != "within" and "tolerance" in t:
            found.append(("E07", f"{where}: a tolerance means nothing to an '{t['goal']}' goal; take it out or make the goal 'within'"))
            continue
        sides = [s for s in ("lowest", "highest") if s in t]
        if len(sides) > 1:
            found.append(("E07", f"{where}: ask for the lowest or the highest, not both"))
            continue
        if sides and t[sides[0]] not in free:
            found.append(("E07", f"{where}: '{sides[0]}' names {t[sides[0]]}, which is not one of the free controls ({', '.join(free)})"))
            continue
        size = 1
        for n in free:
            size *= steps(control(c, n)) + 1
        if size > MAX_SEARCH:
            found.append(("E07", f"{where}: the free controls have {size} settings between them; the checker walks at most {MAX_SEARCH}"))
            continue
        res, rn_ = c["result"], c["result"]["name"]
        wanted = [(n, float(v), units_of(control(c, n)), f"{n} = {with_unit(v, control(c, n))}") for n, v in t["fixed"].items()]
        wanted.append((rn_, float(t["target"]), units_of(res), f"the target {with_unit(t['target'], res)}"))
        if t["goal"] == "within":
            wanted.append((rn_, float(t["tolerance"]), units_of(res), f"the tolerance {with_unit(t['tolerance'], res)}"))
        unsaid = unstated(t["prompt"], wanted, vocabulary(c))
        if unsaid:
            found.append(("E07", f"{where}: the question never states {', '.join(unsaid)} — write each in numerals, with its unit or as name = value"))
        if grade_reach(c, tree, t, reach_state(c, t)):
            found.append(("E07", f"{where}: the page's starting values already pass it, so it asks for nothing"))
            continue
        hit, _ = reach_search(c, tree, t)
        if hit is None:
            found.append(("E07", f"{where}: no setting of {', '.join(free)} passes it"))
    return found


def selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    ok = []

    def say(cond, text):
        ok.append(bool(cond)); print(f"  {'PASS' if cond else 'FAIL'}  {text}")

    tenth = {"min": 0, "max": 1, "step": 0.1}
    say(grid(tenth, 3) == 0.3 and 0 + 3 * 0.1 != 0.3, "a slider's third tenth is 0.3, not 0.30000000000000004")
    say(steps(tenth) == 10 and on_grid(tenth, 0.7) and not on_grid(tenth, 0.75) and not on_grid(tenth, 1.1), "positions: ten steps, 0.7 on the grid, 0.75 and 1.1 off it")
    say((jsround(2.5), jsround(-2.5), jsround(0.49)) == (3, -2, 0), "halves round up, as Math.round does (2.5 -> 3, -2.5 -> -2)")
    years = {"unit": "years", "unit_one": "year"}
    say([with_unit(1, years), with_unit(2, years), with_unit(-1, years)] == ["1 year", "2 years", "-1 year"], "a unit's singular is used for exactly 1 and -1")
    say([with_unit(-5, {"unit": "£"}), with_unit(7.5, {"unit": "%"}), with_unit(3, {}), with_unit(3, None)] == ["-£5", "7.5%", "3", "3"],
        "a currency sign goes in front (after a minus), % sticks to the number, no unit is just the number")
    say([with_unit(7.5, {"unit": "£"}), with_unit(-0.5, {"unit": "$"}), with_unit(2318.548, {"unit": "£"}), with_unit(0.125, {"unit": "€"})] == ["£7.50", "-$0.50", "£2318.55", "€0.125"],
        "money with one decimal gets a second; two or more decimals are left as they are")
    t = {"goal": "within", "target": 0.5, "tolerance": 0.02}
    say(meets(t, 0.52) and meets(t, 0.48) and not meets(t, 0.53) and meets({"goal": "at most", "target": 9}, 9) and not meets({"goal": "at least", "target": 9}, 8.99),
        "goals: within is inclusive at both ends, at most and at least include the target")
    c, why = loads(open(os.path.join(here, "..", "assets", "concepts", "compound-interest.json"), encoding="utf-8").read())
    tree = F.parse(c["formula"])
    reach = c["practice"][1]
    hit, miss = reach_search(c, tree, reach)
    say(hit == {"P": 1000, "r": 7, "n": 11} and miss == {"P": 1000, "r": 7, "n": 0}, f"the reach walk finds the first pass at n = 11 and the first fail at n = 0 (got {hit}, {miss})")
    say(grade_reach(c, tree, reach, dict(hit, n=11)) and not grade_reach(c, tree, reach, dict(hit, n=12)),
        "lowest: 11 years passes, 12 does not (it reaches the goal, but so does 11)")
    no_side = dict(reach); no_side.pop("lowest")
    say(grade_reach(c, tree, no_side, dict(hit, n=12)), "without lowest, 12 years passes too")
    ball = {"controls": [{"name": "t", "min": 0, "max": 4, "step": 0.1}], "result": {"name": "h"}}
    up = {"goal": "within", "target": 15, "tolerance": 1, "lowest": "t", "fixed": {}}
    bt = F.parse("20 * t - 4.9 * t^2")
    say(not grade_reach(ball, bt, up, {"t": 3.0}) and grade_reach(ball, bt, up, {"t": 0.9}),
        "lowest looks at every lower position: a ball thrown up at 20 m/s is within 1 m of 15 m at 3 s, but the lowest is 0.9 s")
    vocab = {"£", "%", "years", "year"}
    rate, years = ("r", 5.0, {"%"}, "r = 5%"), ("n", 5.0, {"years", "year"}, "n = 5 years")
    say(unstated("£2,000 at 3% a year for 5 years.", [("P", 2000.0, {"£"}, "P = £2000"), rate, years], vocab) == ["r = 5%"],
        "a 5 that is written as years does not state a 5% rate")
    say(unstated("£2,000 at 5% a year for 5 years.", [("P", 2000.0, {"£"}, "P = £2000"), rate, years], vocab) == [],
        "each value paired with its own number: £2,000, 5%, 5 years")
    say(unstated("With a = 2 and b = 3, what is y at x = -2?", [("a", 3.0, set(), "a = 3"), ("b", 2.0, set(), "b = 2"), ("x", -2.0, set(), "x = -2")], set()) == ["a = 3", "b = 2"]
        and unstated("With a = 2 and b = 3, what is y at x = -2?", [("a", 2.0, set(), "a"), ("b", 3.0, set(), "b"), ("x", -2.0, set(), "x")], set()) == [],
        "name = value ties a number to its name, and a minus is read (x = -2)")
    say(unstated("6 metres per second squared, for 1 second", [("a", 6.0, {"m/s squared"}, "a"), ("t", 1.0, {"seconds", "second"}, "t")], {"m/s squared", "seconds", "second", "m", "km/h"}) == [],
        "a unit word no control uses (metres) does not stop a number standing for its value")
    say(unstated("£2,000 at 3% for 5 years: the amount, to 2 decimal places?", [rate[:1] + (2.0,) + rate[2:]], vocab) == ["r = 5%"]
        and unstated("Round to the nearest 10: 3 significant figures", [("k", 10.0, set(), "k = 10"), ("m", 3.0, set(), "m = 3")], set()) == ["k = 10", "m = 3"],
        "a number that only says how to answer (2 decimal places, the nearest 10, 3 significant figures) stands for no value")
    # the class, not a list of phrasings: each prompt says 3% for 5 years, the data uses r = 2 or n = 4, and the only
    # 2 or 4 in the prompt says how to answer or which question it is (0.1.0 paired it with the value in all of these)
    r2, n4 = [("P", 2000.0, {"£"}, "P"), ("r", 2.0, {"%"}, "r = 2%"), years], [("P", 2000.0, {"£"}, "P"), rate[:1] + (3.0,) + rate[2:], ("n", 4.0, {"years", "year"}, "n = 4 years")]
    forms = ["{} What is the amount, to 2 decimals?", "{} What is the amount, correct to 2 decimal digits?", "{} What is the amount, to 4 s.f.?",
             "{} What is the amount, to 4 significant figs?", "{} What is the amount, to 2-decimal-place accuracy?", "{} What is the amount (2 marks)?",
             "{} Answer in 2 lines.", "{} Give 2 decimals.", "Task 2: {}", "Exercise 2. {}", "Q 2: {}", "Question 3 of 4: {}", "Step 1 of 4: {}", "(Part 2) {}", "#2: {}"]
    data = "£2,000 at 3% a year for 5 years."
    missed = [f for f in forms if not unstated(f.format(data), r2 if "2" in f else n4, vocab)]
    say(not missed, f"a number that only says how to answer or which question it is stands for no value, in {len(forms)} forms of the class"
        + "".join(f"; paired: {f.format('…')}" for f in missed))
    kept = [p for p, want in [("£2,000 at 3% a year for 5 years. Task 2: the amount, to 2 decimals?", [("P", 2000.0, {"£"}, "P"), ("r", 3.0, {"%"}, "r"), years]),
                              ("With a 5% chance each try, how many tries: within 2 of 10?", [("t", 2.0, set(), "t"), ("g", 10.0, set(), "g"), ("p", 5.0, {"%"}, "p")]),
                              ("Each try works 20% of the time: the chance in 5 tries?", [("p", 20.0, {"%"}, "p"), ("n", 5.0, {"tries", "try"}, "n")])]
            if unstated(p, want, vocab | {"tries", "try"})]
    say(not kept, "and a number that is a value is still read as one: 'within 2 of 10', 'in 5 tries', a label and a precision beside the values"
        + "".join(f"; not paired: {p}" for p in kept))
    for f in sorted(os.listdir(os.path.join(here, "..", "assets", "concepts"))):
        c, why = loads(open(os.path.join(here, "..", "assets", "concepts", f), encoding="utf-8").read())
        found = [why] if why else problems(c)
        say(not found, f"the example {f} meets every concept rule" + "".join(f"; {x}" for x in found))
    bad = json.loads(json.dumps(c))
    bad["practice"][0]["tolerance"] = 0
    say(problems(bad) and all(code == "E06" for code, _ in problems(bad)), "a zero tolerance is refused with E06 (the rest of the rules are tested page by page in explorer_check.py)")
    print(f"concept selftest: {sum(ok)}/{len(ok)} passed")
    return 0 if all(ok) else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if len(argv) != 1:
        print(__doc__.strip().split("\n\n")[1]); return 2
    c, why = loads(open(argv[0], encoding="utf-8").read())
    if why:
        print("E01 " + why); return 1
    found = problems(c)
    for code, m in found:
        print(f"{code} {m}")
    print(f"{len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

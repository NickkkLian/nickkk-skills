#!/usr/bin/env python3
"""story_check.py — consistency checks for a novel outline written as story.json (see references/schema.md).

    python3 story_check.py story.json [--max-open 5] [--strict] [--json OUT]
    python3 story_check.py --selftest

Errors (exit 1):
  S01 references   ids are unique; every reference (relations, participants, places, causes, rules, chapter events,
                   act beats, point of view, clue and question chapters) points at something that exists; every spine
                   event is told in at least one chapter
  S02 timeline     a cause happens before its effect; a character does not act in a chapter before they are
                   introduced or after they exit
  S03 names        two characters share a name or alias, or two names differ by one letter (readers confuse them)
  S04 clues        a clue is paid off before it is planted, or never paid off (unless marked "left open on purpose")
  S05 motivation   a spine event has no "what happened" or no "so what changed", or the two say the same thing; a
                   character in two or more spine events has no desire or no fear
Warnings (exit 0; exit 1 with --strict):
  S06 load         at the end of a chapter the reader holds more than --max-open unanswered questions and unpaid
                   clues at once (a starting value to tune, not a measured limit); the one-sentence retelling is
                   missing or is more than one sentence
  S07 caps         the outline does not write caps for main characters and places (no cap written = no cap), or
                   exceeds them
  S08 wrapper      every spine event depends on the same world rule: take that rule away and the whole story
                   collapses, so the story may be wrapping paper for the rule
Standard library only.
"""
import json, re, sys, tempfile, os


def lev(a, b):
    if abs(len(a) - len(b)) > 1:
        return 2
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check(story, max_open=5):
    errs, warns = [], []
    E = lambda code, msg: errs.append((code, msg))
    W = lambda code, msg: warns.append((code, msg))
    world = story.get("world", {})
    chars = story.get("characters", [])
    spine = story.get("spine", [])
    chapters = story.get("chapters", [])
    clues = story.get("foreshadowing", [])
    questions = story.get("questions", [])
    rules = {r.get("id") for r in world.get("rules", [])}
    places = {p.get("id") for p in world.get("places", [])}
    cids = [c.get("id") for c in chars]
    eids = [e.get("id") for e in spine]
    chap_ns = [c.get("n") for c in chapters]
    # S01 references
    for label, ids in (("character", cids), ("event", eids), ("chapter", chap_ns)):
        dup = sorted({i for i in ids if ids.count(i) > 1}, key=str)
        if dup:
            E("S01", f"duplicate {label} id(s): {dup}")
    cset, eset, nset = set(cids), set(eids), set(chap_ns)
    for c in chars:
        for r in c.get("relations", []):
            if r.get("to") not in cset:
                E("S01", f"{c.get('id')} relation points at unknown character {r.get('to')!r}")
    for e in spine:
        for p in e.get("participants", []):
            if p not in cset:
                E("S01", f"{e.get('id')} participant {p!r} is not a character")
        if e.get("place") and e["place"] not in places:
            E("S01", f"{e.get('id')} place {e['place']!r} is not in world.places")
        for c in e.get("causes", []):
            if c not in eset:
                E("S01", f"{e.get('id')} cause {c!r} is not a spine event")
        for r in e.get("depends_on_rules", []):
            if r not in rules:
                E("S01", f"{e.get('id')} depends on unknown rule {r!r}")
    told = {}
    for ch in chapters:
        if ch.get("pov") and ch["pov"] not in cset:
            E("S01", f"chapter {ch.get('n')} point of view {ch['pov']!r} is not a character")
        for ev in ch.get("events", []):
            if ev not in eset:
                E("S01", f"chapter {ch.get('n')} tells unknown event {ev!r}")
            else:
                told.setdefault(ev, []).append(ch.get("n"))
    for act in story.get("structure", {}).get("acts", []):
        for beat in act.get("beats", []):
            for ev in beat.get("events", []):
                if ev not in eset:
                    E("S01", f"beat {beat.get('name')!r} points at unknown event {ev!r}")
    for e in spine:
        if e.get("id") not in told:
            E("S01", f"spine event {e.get('id')} is never told in a chapter")
    for item, kind in [(c, "clue") for c in clues] + [(q, "question") for q in questions]:
        for key in ("planted_in", "paid_off_in", "opened_in", "answered_in"):
            v = item.get(key)
            if v is not None and v not in nset:
                E("S01", f"{kind} {item.get('id')} {key} chapter {v} does not exist")
    # S02 timeline
    t = {e.get("id"): e.get("t") for e in spine}
    for e in spine:
        for c in e.get("causes", []):
            if c in t and t[c] is not None and e.get("t") is not None and t[c] >= e["t"]:
                E("S02", f"{e['id']} (t={e['t']}) is caused by {c} (t={t[c]}), which does not happen earlier")
    first_ch = {ev: min(ns) for ev, ns in told.items()}
    for c in chars:
        intro, exit_ = c.get("introduced_in"), c.get("exits_in")
        for e in spine:
            if c.get("id") in e.get("participants", []) and e.get("id") in first_ch:
                n = first_ch[e["id"]]
                if intro is not None and n < intro:
                    E("S02", f"{c.get('name')} acts in chapter {n} ({e['id']}) before being introduced in chapter {intro}")
                if exit_ is not None and n > exit_:
                    E("S02", f"{c.get('name')} acts in chapter {n} ({e['id']}) after exiting in chapter {exit_}")
    # S03 names
    names = []
    for c in chars:
        for nm in [c.get("name", "")] + list(c.get("aliases", [])):
            if nm:
                names.append((nm.strip(), c.get("id")))
    for i, (a, ca) in enumerate(names):
        for b, cb in names[i + 1:]:
            if ca == cb:
                continue
            al, bl = a.lower(), b.lower()
            if al == bl:
                E("S03", f"{ca} and {cb} are both called {a!r}")
            elif min(len(al), len(bl)) >= 4 and lev(al, bl) <= 1:
                E("S03", f"{a!r} ({ca}) and {b!r} ({cb}) differ by one letter")
            elif max(len(al), len(bl)) <= 3 and len(al) == len(bl) >= 2 and re.search(r"[一-鿿]", a + b) and lev(al, bl) <= 1:
                E("S03", f"{a!r} ({ca}) and {b!r} ({cb}) differ by one character")
    # S04 clues
    for f in clues:
        p, q = f.get("planted_in"), f.get("paid_off_in")
        if q is None and not f.get("left_open_on_purpose"):
            E("S04", f"clue {f.get('id')} ({f.get('clue', '')[:40]!r}) is planted in chapter {p} and never paid off")
        elif p is not None and q is not None and q < p:
            E("S04", f"clue {f.get('id')} is paid off in chapter {q} before it is planted in chapter {p}")
    # S05 motivation
    count = {}
    for e in spine:
        wh, sc = (e.get("what_happened") or "").strip(), (e.get("so_what_changed") or "").strip()
        if not wh or not sc:
            E("S05", f"{e.get('id')} needs both 'what happened' and 'so what changed'")
        elif wh.lower() == sc.lower():
            E("S05", f"{e.get('id')} says the same thing for 'what happened' and 'so what changed'")
        for p in e.get("participants", []):
            count[p] = count.get(p, 0) + 1
    for c in chars:
        if count.get(c.get("id"), 0) >= 2 and (not (c.get("desire") or "").strip() or not (c.get("fear") or "").strip()):
            E("S05", f"{c.get('name')} is in {count[c['id']]} spine events but has no {'desire' if not (c.get('desire') or '').strip() else 'fear'}")
    # S06 load
    for n in sorted(x for x in chap_ns if isinstance(x, int)):
        open_q = [q.get("id") for q in questions if q.get("opened_in") is not None and q["opened_in"] <= n and (q.get("answered_in") is None or q["answered_in"] > n)]
        open_c = [f.get("id") for f in clues if f.get("planted_in") is not None and f["planted_in"] <= n and (f.get("paid_off_in") is None or f["paid_off_in"] > n)]
        if len(open_q) + len(open_c) > max_open:
            W("S06", f"after chapter {n} the reader holds {len(open_q) + len(open_c)} open threads at once ({', '.join(open_q + open_c)}); limit {max_open}")
    rt = (story.get("retelling") or "").strip()
    if not rt:
        W("S06", "no one-sentence retelling (what happens, and what is different afterwards)")
    elif len(re.findall(r"[.!?。！？](?:\s|$)", rt)) > 1:
        W("S06", "the retelling is more than one sentence")
    # S07 caps
    caps = story.get("caps") or {}
    if "main_characters" not in caps or "places" not in caps:
        W("S07", "caps for main_characters and places are not written; no cap written means no cap")
    else:
        mains = [c for c in chars if c.get("role") in ("protagonist", "antagonist", "main")]
        if len(mains) > caps["main_characters"]:
            W("S07", f"{len(mains)} main characters, cap {caps['main_characters']}")
        if len(places) > caps["places"]:
            W("S07", f"{len(places)} places, cap {caps['places']}")
    # S08 wrapper
    deps = [set(e.get("depends_on_rules", [])) for e in spine]
    if len(deps) >= 3 and all(deps):
        common = set.intersection(*deps)
        if common:
            W("S08", f"every spine event depends on rule(s) {sorted(common)}: remove it and the whole story collapses — check it is a story, not wrapping for the rule")
    return errs, warns


def sample():
    return {
        "title": "The Next-Year Light", "idea": "A lighthouse keeper realises the ships she guides in arrive from next year.",
        "retelling": "A keeper who guides ships from next year uses what they know to save her town, and loses the life she would have had.",
        "caps": {"main_characters": 4, "places": 3},
        "world": {"rules": [{"id": "R1", "rule": "Ships that see the light in fog arrive one year early", "cost": "each early ship takes a year from the keeper's memory"}],
                  "not_allowed": ["no one else can see the fog light"], "places": [{"id": "P1", "name": "Gull Point light"}, {"id": "P2", "name": "Harbour town"}]},
        "characters": [
            {"id": "C1", "name": "Maren", "role": "protagonist", "desire": "keep the town alive", "fear": "forgetting her brother", "secret": "she lit the fog light on purpose", "introduced_in": 1, "relations": [{"to": "C2", "kind": "sibling"}]},
            {"id": "C2", "name": "Tobias", "role": "main", "desire": "leave the town", "fear": "the sea", "secret": "his ship is on next year's list", "introduced_in": 1, "relations": [{"to": "C1", "kind": "sibling"}]},
            {"id": "C3", "name": "Harbourmaster Quill", "role": "antagonist", "desire": "control the harbour", "fear": "losing the town's trust", "secret": "", "introduced_in": 2, "relations": [{"to": "C1", "kind": "rival"}]}],
        "spine": [
            {"id": "E1", "t": 1, "title": "The early ship", "what_happened": "A ship docks with next year's newspapers", "so_what_changed": "Maren knows the storm is coming", "participants": ["C1"], "place": "P1", "depends_on_rules": ["R1"]},
            {"id": "E2", "t": 2, "title": "The warning", "what_happened": "Maren tells the town about the storm", "so_what_changed": "Quill calls her a liar and closes the harbour", "participants": ["C1", "C3"], "place": "P2", "causes": ["E1"]},
            {"id": "E3", "t": 3, "title": "The list", "what_happened": "Tobias finds his own name on next year's lost list", "so_what_changed": "Tobias stays instead of sailing", "participants": ["C2", "C1"], "place": "P2", "causes": ["E1"]},
            {"id": "E4", "t": 4, "title": "The price", "what_happened": "Maren lights the fog light again to bring the rescue ship early", "so_what_changed": "The town survives and Maren forgets a year with her brother", "participants": ["C1", "C2", "C3"], "place": "P1", "causes": ["E2", "E3"], "depends_on_rules": ["R1"]}],
        "structure": {"acts": [{"name": "I", "beats": [{"name": "Inciting incident", "events": ["E1"]}]}, {"name": "II", "beats": [{"name": "Midpoint", "events": ["E3"]}]}, {"name": "III", "beats": [{"name": "Climax", "events": ["E4"]}]}]},
        "foreshadowing": [{"id": "F1", "clue": "Maren cannot remember last winter", "planted_in": 1, "paid_off_in": 4}],
        "questions": [{"id": "Q1", "question": "Who lit the fog light?", "opened_in": 1, "answered_in": 3}],
        "chapters": [{"n": 1, "title": "Fog", "pov": "C1", "events": ["E1"]}, {"n": 2, "title": "Liar", "pov": "C1", "events": ["E2"]}, {"n": 3, "title": "The list", "pov": "C2", "events": ["E3"]}, {"n": 4, "title": "Light", "pov": "C1", "events": ["E4"]}],
    }


def selftest():
    import copy
    ok, lines = True, []

    def chk(cond, label):
        nonlocal ok
        ok &= bool(cond); lines.append(f"  {'✔' if cond else '✘'} {label}")
    e, w = check(sample())
    chk(not e and not w, f"control sample → 0 errors, 0 warnings ({e + w})")

    def mut(fn):
        s = copy.deepcopy(sample()); fn(s); return s

    cases = [
        ("S01", mut(lambda s: s["chapters"][1]["events"].append("E9")), "error"),
        ("S01", mut(lambda s: s["chapters"][3].update(events=[])), "error"),
        ("S02", mut(lambda s: s["spine"][1].update(t=0)), "error"),
        ("S02", mut(lambda s: s["characters"][2].update(introduced_in=3)), "error"),
        ("S03", mut(lambda s: s["characters"][2].update(name="Maren")), "error"),
        ("S03", mut(lambda s: s["characters"][1].update(name="Mareng")), "error"),
        ("S03", mut(lambda s: [s["characters"][0].update(name="李明"), s["characters"][1].update(name="李鸣")]), "error"),
        ("S04", mut(lambda s: s["foreshadowing"][0].update(paid_off_in=None)), "error"),
        ("S04", mut(lambda s: s["foreshadowing"][0].update(planted_in=4, paid_off_in=2)), "error"),
        ("S05", mut(lambda s: s["spine"][0].update(so_what_changed="")), "error"),
        ("S05", mut(lambda s: s["characters"][1].update(fear="")), "error"),
        ("S06", mut(lambda s: s["questions"].extend({"id": f"Q{i}", "question": "?", "opened_in": 1, "answered_in": 4} for i in range(2, 8))), "warn"),
        ("S06", mut(lambda s: s.update(retelling="One. Two.")), "warn"),
        ("S07", mut(lambda s: s.pop("caps")), "warn"),
        ("S08", mut(lambda s: [ev.update(depends_on_rules=["R1"]) for ev in s["spine"]]), "warn"),
        # one exclusive sample per remaining branch (a break matrix found these branches without a sample)
        ("S01", mut(lambda s: s["spine"].append(copy.deepcopy(s["spine"][3]))), "error"),
        ("S01", mut(lambda s: s["characters"][0]["relations"].append({"to": "C9", "kind": "friend"})), "error"),
        ("S01", mut(lambda s: s["spine"][0]["participants"].append("C9")), "error"),
        ("S01", mut(lambda s: s["spine"][0].update(place="P9")), "error"),
        ("S01", mut(lambda s: s["spine"][1]["causes"].append("E9")), "error"),
        ("S01", mut(lambda s: s["spine"][1].update(depends_on_rules=["R9"])), "error"),
        ("S01", mut(lambda s: s["chapters"][0].update(pov="C9")), "error"),
        ("S01", mut(lambda s: s["structure"]["acts"][0]["beats"][0]["events"].append("E9")), "error"),
        ("S01", mut(lambda s: s["foreshadowing"][0].update(paid_off_in=9)), "error"),
        ("S02", mut(lambda s: s["characters"][2].update(exits_in=3)), "error"),
        ("S05", mut(lambda s: s["spine"][0].update(so_what_changed=s["spine"][0]["what_happened"])), "error"),
        ("S06", mut(lambda s: s.pop("retelling")), "warn"),
        ("S07", mut(lambda s: s["caps"].update(main_characters=2)), "warn"),
        ("S07", mut(lambda s: s["caps"].update(places=1)), "warn"),
    ]
    for code, story, kind in cases:
        e, w = check(story)
        got = {c for c, _ in (e if kind == "error" else w)}
        other = {c for c, _ in (w if kind == "error" else e)}
        chk(got == {code} and not other, f"{code} sample → exactly one {kind} code {code} (got errors {sorted({c for c,_ in e})}, warnings {sorted({c for c,_ in w})})")
    ok_left, _ = check(mut(lambda s: s["foreshadowing"][0].update(paid_off_in=None, left_open_on_purpose=True)))
    chk(not ok_left, "a clue marked left_open_on_purpose is not an error")
    import contextlib, io
    with tempfile.TemporaryDirectory() as d:
        bad_json = os.path.join(d, "bad.json"); open(bad_json, "w").write("{ not json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc_missing = main([os.path.join(d, "missing.json")])
            rc_bad = main([bad_json])
        chk(rc_missing == 2 and rc_bad == 2, f"a missing or invalid story file exits 2 without a traceback ({rc_missing}, {rc_bad})")
    return ok, lines


def main(argv):
    if "--selftest" in argv:
        ok, lines = selftest(); print(f"story_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines)); return 0 if ok else 2
    files = [a for a in argv if not a.startswith("--") and (argv.index(a) == 0 or argv[argv.index(a) - 1] not in ("--max-open", "--json"))]
    if not files:
        print(__doc__); return 2
    max_open = int(argv[argv.index("--max-open") + 1]) if "--max-open" in argv else 5
    try:
        story = json.load(open(files[0], encoding="utf-8"))
    except (OSError, ValueError) as e:                   # missing file, unreadable file or invalid JSON: exit 2, no traceback
        print(f"✘ cannot read {files[0]}: {e}")
        return 2
    errs, warns = check(story, max_open)
    for code, msg in errs:
        print(f"✘ {code}  {msg}")
    for code, msg in warns:
        print(f"! {code}  {msg}")
    print(f"{'✘' if errs else '✔'} {files[0]}: {len(errs)} error(s), {len(warns)} warning(s)")
    if "--json" in argv:
        json.dump({"errors": errs, "warnings": warns}, open(argv[argv.index("--json") + 1], "w"), indent=1, ensure_ascii=False)
    return 1 if errs or ("--strict" in argv and warns) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

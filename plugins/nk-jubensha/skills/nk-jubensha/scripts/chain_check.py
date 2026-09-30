#!/usr/bin/env python3
"""chain_check.py — check a party murder-mystery game (game.json) for the faults that make it unfair or unplayable.

    python3 chain_check.py game.json [--json OUT] [--strict]
    python3 chain_check.py --selftest

It reads structure, not prose: every deduction step must stand on clues that a player actually receives, the
culprit's cover must break only through the clues written for that, the solution must not sit in anyone's booklet,
and every role must have something to do. Whether a clue's words really support a step is a question for the
blind detective run (detective.py), not for this script.

Checks (E = error, W = warning):
  J01 E  structure: duplicate ids, references to things that do not exist, not exactly one culprit, a culprit who is
         not a player, a player count that does not match, steps that wait on each other in a circle
  J02 E  a step with no clue, or a step that needs a clue no player receives ("unsolvable: clue X missing")
  J03 E  an orphan clue: no step, red herring or goal uses it
  J04 E  a dead end: a red herring with nothing that resolves it, or resolved only by a clue nobody receives
  J05 E  the cover breaks some other way: a break token outside the intended clues, a token the intended clues do
         not carry, a break clue only the culprit holds, or a step naming the culprit that skips the break
  J06 E  a leak: a declared solution secret in any player-facing text (the culprit's private pages excepted), or
         no secret declared at all
  J07 E  solvable by elimination alone (every innocent is cleared without the proof against the culprit), or no
         positive proof against the culprit
  J08 E  a step that stands only on clues in the culprit's own booklet (the culprit will keep them)
  J09 E  a role with nothing to do: no goal, no secret, nothing to tell the table, a culprit with nothing to hide,
         an innocent with nothing to find, or a player the chain never needs and nobody suspects
  J10 W  the busiest role has more than twice the hooks of the quietest (a starting ratio to tune)
  J11 W  a step every clue of which sits in one innocent's booklet: if that player stays quiet it cannot be made
  J12 E  the trick: a family not in the taxonomy, or no false belief / how / why / trace written
  J13 W  a long run of host-only text (solution summary, trick how) repeated in player-facing text

Exit: 0 clean (warnings allowed) · 1 errors, or warnings with --strict · 2 unreadable file or failed self-test.
Standard library only, Python 3.9+.
"""
import copy, json, os, re, sys

TAXONOMY = {
    "T1": "time moved", "T2": "place moved", "T3": "presence faked", "T4": "identity swapped",
    "T5": "hand hidden", "T6": "way in or out", "T7": "trail planted", "T8": "wrong case",
}
STEP_KINDS = {"establish", "eliminate", "explain", "break", "implicate", "motive", "conclude"}
GOAL_KINDS = {"find", "hide", "bond"}
SOURCE_KINDS = {"booklet", "search", "host", "none"}
OVERLAP = 16          # J13: characters of host-only text that may not reappear verbatim in player text
BALANCE = 0.5         # J10: quietest role's hooks must be at least this share of the busiest role's


def _ids(xs):
    return [x.get("id") for x in xs if isinstance(x, dict)]


class Game:
    """Indexes over one game dict. Nothing here judges; the checks below do."""

    def __init__(self, g):
        self.g = g
        self.meta = g.get("meta") or {}
        self.chars = [c for c in g.get("characters") or [] if isinstance(c, dict)]
        self.npcs = [c for c in g.get("npcs") or [] if isinstance(c, dict)]
        self.places = [p for p in g.get("places") or [] if isinstance(p, dict)]
        self.rounds = [r for r in g.get("rounds") or [] if isinstance(r, dict)]
        self.clues = [c for c in g.get("clues") or [] if isinstance(c, dict)]
        self.sol = g.get("solution") or {}
        self.steps = [s for s in self.sol.get("steps") or [] if isinstance(s, dict)]
        self.herrings = [h for h in self.sol.get("herrings") or [] if isinstance(h, dict)]
        self.char = {c.get("id"): c for c in self.chars}
        self.players = {c.get("id") for c in self.chars if c.get("player", True)}
        self.clue = {c.get("id"): c for c in self.clues}
        self.step = {s.get("id"): s for s in self.steps}
        self.place = {p.get("id") for p in self.places}
        self.round = {r.get("n") for r in self.rounds}
        self.culprit = self.sol.get("culprit")

    def name(self, cid):
        c = self.char.get(cid)
        return (c.get("name") or cid) if c else str(cid)

    def received(self, clue):
        """True: a player gets it. False: nobody does. None: its source names something that does not exist (J01)."""
        src = clue.get("source") or {}
        k = src.get("kind")
        if k == "booklet":
            return None if src.get("holder") not in self.char else src.get("holder") in self.players
        if k == "search":
            if src.get("place") not in self.place or src.get("round") not in self.round:
                return None
            return True
        if k == "host":
            return None if src.get("round") not in self.round else True
        if k == "none":
            return False
        return None

    def culprit_held(self, clue):
        src = clue.get("source") or {}
        return src.get("kind") == "booklet" and src.get("holder") == self.culprit

    def ancestors(self, sid):
        """every step this one waits on, directly or through others (cycles tolerated)"""
        seen, todo = set(), list((self.step.get(sid) or {}).get("after") or [])
        while todo:
            x = todo.pop()
            if x in seen or x not in self.step:
                continue
            seen.add(x)
            todo += self.step[x].get("after") or []
        return seen

    def player_texts(self):
        """(where, text) for everything a player reads or hears. The culprit's private sections, the culprit's goals
        and clues only the culprit holds are the culprit's own pages; host-only fields never appear here."""
        out = []
        for k in ("title", "premise", "setting", "duration", "difficulty"):
            if isinstance(self.meta.get(k), str):
                out.append((f"meta.{k}", self.meta[k]))
        for w in self.meta.get("warnings") or []:
            out.append(("meta.warnings", str(w)))
        for p in self.places:
            out.append((f"place {p.get('id')}", str(p.get("name", "")) + " " + str(p.get("desc", ""))))
        for r in self.rounds:
            out.append((f"round {r.get('n')}", str(r.get("title", "")) + " " + str(r.get("say", ""))))
        for c in self.chars:
            cid, own = c.get("id"), c.get("id") == self.culprit
            out.append((f"{self.name(cid)} intro", str(c.get("intro", ""))))
            for i, s in enumerate(c.get("sections") or []):
                if own and s.get("share") != "table":
                    continue
                out.append((f"{self.name(cid)} booklet §{i + 1} ({s.get('share')})", str(s.get("title", "")) + " " + str(s.get("text", ""))))
            if not own:
                for gl in c.get("goals") or []:
                    out.append((f"{self.name(cid)} goal {gl.get('id')}", str(gl.get("text", ""))))
        for cl in self.clues:
            if self.culprit_held(cl):
                continue
            out.append((f"clue {cl.get('id')}", str(cl.get("title", "")) + " " + str(cl.get("text", ""))))
        return out


def check(g):
    """list of (code, message); codes starting with W are warnings"""
    G, out = Game(g), []

    def add(code, msg):
        out.append((code, msg))

    # ── J01 structure ──
    seen = {}
    for kind, xs in (("character", G.chars), ("npc", G.npcs), ("place", G.places), ("clue", G.clues),
                     ("step", G.steps), ("herring", G.herrings)):
        for x in _ids(xs):
            if x in seen:
                add("J01", f"id {x!r} used twice ({seen[x]} and {kind})")
            seen[x] = kind
    for cl in G.clues:
        if not str(cl.get("text", "")).strip():
            add("J01", f"clue {cl.get('id')} has no text")
        if (cl.get("source") or {}).get("kind") not in SOURCE_KINDS:
            add("J01", f"clue {cl.get('id')}: source kind must be one of {sorted(SOURCE_KINDS)}")
        elif G.received(cl) is None:
            add("J01", f"clue {cl.get('id')}: its source names a holder, place or round that does not exist")
    for s in G.steps:
        for c in s.get("clues") or []:
            if c not in G.clue:
                add("J01", f"step {s.get('id')} cites clue {c}, which does not exist")
        for a in s.get("after") or []:
            if a not in G.step:
                add("J01", f"step {s.get('id')} waits on step {a}, which does not exist")
        if s.get("kind") not in STEP_KINDS:
            add("J01", f"step {s.get('id')}: kind must be one of {sorted(STEP_KINDS)}")
        if s.get("target") is not None and s.get("target") not in G.char:
            add("J01", f"step {s.get('id')} names {s.get('target')}, who is not a character")
        if s.get("id") in G.ancestors(s.get("id")):
            add("J01", f"step {s.get('id')} waits on itself through other steps")
    for h in G.herrings:
        if h.get("points_to") not in G.char:
            add("J01", f"red herring {h.get('id')} points to {h.get('points_to')}, who is not a character")
        for c in (h.get("clues") or []) + (h.get("resolved_by") or []):
            if c not in G.clue:
                add("J01", f"red herring {h.get('id')} cites clue {c}, which does not exist")
    for c in G.chars:
        for gl in c.get("goals") or []:
            for x in gl.get("clues") or []:
                if x not in G.clue:
                    add("J01", f"{G.name(c.get('id'))}'s goal {gl.get('id')} cites clue {x}, which does not exist")
    flagged = [c.get("id") for c in G.chars if c.get("culprit")]
    if len(flagged) != 1 or G.culprit not in G.players or flagged[0] != G.culprit:
        add("J01", f"exactly one player must be the culprit and match solution.culprit (flagged {flagged}, solution says {G.culprit!r})")
    if G.meta.get("players") != len(G.players):
        add("J01", f"meta.players says {G.meta.get('players')} but {len(G.players)} characters are players")

    # ── J02 every step stands on clues a player receives ──
    for s in G.steps:
        if not s.get("clues"):
            add("J02", f"step {s.get('id')} ({s.get('claim', '')[:40]}) cites no clue")
        for c in s.get("clues") or []:
            if c in G.clue and G.received(G.clue[c]) is False:
                add("J02", f"unsolvable: step {s.get('id')} needs clue {c}, which no player receives")

    # ── J03 orphan clues ──
    used = set()
    for s in G.steps:
        used |= set(s.get("clues") or [])
    for h in G.herrings:
        used |= set(h.get("clues") or []) | set(h.get("resolved_by") or [])
    for c in G.chars:
        for gl in c.get("goals") or []:
            used |= set(gl.get("clues") or [])
    for cl in G.clues:
        if cl.get("id") not in used:
            add("J03", f"clue {cl.get('id')} ({cl.get('title', '')}) is used by no step, red herring or goal")

    # ── J04 dead ends ──
    for h in G.herrings:
        res = [c for c in h.get("resolved_by") or [] if c in G.clue]
        if not h.get("resolved_by"):
            add("J04", f"dead end: red herring {h.get('id')} (pointing at {G.name(h.get('points_to'))}) has nothing that resolves it")
        elif res and not any(G.received(G.clue[c]) for c in res):
            add("J04", f"dead end: red herring {h.get('id')} is resolved only by clues no player receives ({', '.join(res)})")

    # ── J05 the cover breaks only through the intended clues ──
    al = G.sol.get("alibi") or {}
    brk = G.step.get(al.get("step"))
    if not al or not brk or brk.get("kind") != "break":
        add("J05", "solution.alibi must name a step of kind 'break' (the step where the culprit's cover gives way)")
    else:
        bclues = [G.clue[c] for c in brk.get("clues") or [] if c in G.clue]
        tokens = [t for t in al.get("tokens") or [] if str(t).strip()]
        if not tokens:
            add("J05", "solution.alibi.tokens is empty: name the words that carry the break, so a leak elsewhere can be found")
        for t in tokens:
            if not any(t in str(c.get("title", "")) + str(c.get("text", "")) for c in bclues):
                add("J05", f"break token {t!r} is in none of the intended clues ({', '.join(brk.get('clues') or [])}): they do not carry the break")
        intended = {c.get("id") for c in bclues}
        for where, text in G.player_texts():
            if where.startswith("clue ") and where[5:] in intended:
                continue
            for t in tokens:
                if t in text:
                    add("J05", f"the cover can break another way: {where} contains break token {t!r}")
        for c in bclues:
            if G.culprit_held(c):
                add("J05", f"break clue {c.get('id')} sits only in the culprit's booklet")
        for s in G.steps:
            names_culprit = s.get("kind") == "conclude" or (s.get("kind") == "implicate" and s.get("target") == G.culprit)
            if names_culprit and brk.get("id") not in G.ancestors(s.get("id")):
                add("J05", f"step {s.get('id')} points at the culprit without going through the break ({brk.get('id')})")

    # ── J06 leaks ──
    secrets = [x for x in G.sol.get("secrets") or [] if str(x).strip()]
    if not secrets:
        add("J06", "solution.secrets is empty: declare the phrases that give the answer away, so leaks can be found")
    for where, text in G.player_texts():
        for x in secrets:
            if x in text:
                add("J06", f"leak: {where} contains the solution phrase {x!r}")

    # ── J07 not by elimination alone ──
    proof = [s for s in G.steps if s.get("kind") == "implicate" and s.get("target") == G.culprit]
    if not proof:
        add("J07", "no positive proof against the culprit: add a step of kind 'implicate' that names them")
    positive = {s.get("id") for s in G.steps if s.get("kind") in ("break", "implicate")}
    innocents = G.players - {G.culprit}
    cleared = {s.get("target") for s in G.steps
               if s.get("kind") == "eliminate" and not (G.ancestors(s.get("id")) & positive)}
    if innocents and innocents <= cleared:
        add("J07", "solvable by elimination alone: every innocent player is cleared without the proof against the culprit "
                   f"({', '.join(G.name(x) for x in sorted(innocents))})")

    # ── J08 steps the culprit can sink ──
    for s in G.steps:
        known = [G.clue[c] for c in s.get("clues") or [] if c in G.clue]
        if known and all(G.culprit_held(c) for c in known):
            add("J08", f"step {s.get('id')} stands only on clues in the culprit's own booklet ({', '.join(c.get('id') for c in known)})")

    # ── J09 every role has something to do ──
    cited = set()
    for s in G.steps:
        cited |= set(s.get("clues") or [])
    for h in G.herrings:
        cited |= set(h.get("clues") or []) | set(h.get("resolved_by") or [])
    suspected = {h.get("points_to") for h in G.herrings} | {s.get("target") for s in G.steps}
    hooks = {}
    for c in G.chars:
        cid = c.get("id")
        if cid not in G.players:
            continue
        goals, secs = c.get("goals") or [], c.get("sections") or []
        held = [cl.get("id") for cl in G.clues if (cl.get("source") or {}).get("kind") == "booklet"
                and (cl.get("source") or {}).get("holder") == cid and cl.get("id") in cited]
        kinds = {gl.get("kind") for gl in goals}
        if not goals:
            add("J09", f"{G.name(cid)} has no goal")
        if not any(s.get("share") == "private" for s in secs):
            add("J09", f"{G.name(cid)} has no secret (no private section)")
        if not any(s.get("share") == "table" for s in secs):
            add("J09", f"{G.name(cid)} has nothing to tell the table (no table section)")
        if goals and cid == G.culprit and "hide" not in kinds:
            add("J09", f"the culprit {G.name(cid)} has no goal of kind 'hide'")
        if goals and cid != G.culprit and "find" not in kinds:
            add("J09", f"{G.name(cid)} is innocent and has no goal of kind 'find'")
        if not held and cid not in suspected:
            add("J09", f"{G.name(cid)} holds nothing the chain needs, no red herring points at them and no step names them")
        hooks[cid] = len(goals) + len(held) + sum(1 for h in G.herrings if h.get("points_to") == cid)

    # ── J10 balance (warning) ──
    if len(hooks) >= 2:
        lo, hi = min(hooks, key=hooks.get), max(hooks, key=hooks.get)
        if hooks[lo] < BALANCE * hooks[hi]:
            add("W10", f"J10 {G.name(lo)} has {hooks[lo]} hooks (goals, needed clues, suspicion) and {G.name(hi)} has {hooks[hi]}")

    # ── J11 single points of failure (warning) ──
    for s in G.steps:
        known = [G.clue[c] for c in s.get("clues") or [] if c in G.clue]
        holders = {(c.get("source") or {}).get("holder") for c in known}
        if known and all((c.get("source") or {}).get("kind") == "booklet" for c in known) and len(holders) == 1 \
                and G.culprit not in holders:
            add("W11", f"J11 step {s.get('id')} stands only on {G.name(holders.pop())}'s booklet: if that player stays quiet it cannot be made")

    # ── J12 the trick ──
    tr = g.get("trick") or {}
    if tr.get("family") not in TAXONOMY:
        add("J12", f"trick.family {tr.get('family')!r} is not a taxonomy family ({', '.join(TAXONOMY)})")
    for k in ("false_belief", "how", "why", "trace"):
        if not str(tr.get(k, "")).strip():
            add("J12", f"trick.{k} is empty")

    # ── J13 host-only text repeated in player text (warning) ──
    host = re.sub(r"\s+", "", str(G.sol.get("summary", "")) + "\u0000" + str(tr.get("how", "")))
    grams = {host[i:i + OVERLAP] for i in range(len(host) - OVERLAP + 1) if "\u0000" not in host[i:i + OVERLAP]}
    for where, text in G.player_texts():
        t = re.sub(r"\s+", "", text)
        hit = next((t[i:i + OVERLAP] for i in range(len(t) - OVERLAP + 1) if t[i:i + OVERLAP] in grams), None)
        if hit:
            add("W13", f"J13 {where} repeats host-only text word for word: {hit!r}")
    return out


# ── self-test: one sample per rule, each must trip exactly its codes; the clean control must trip none ──
def _fixture():
    return {
        "schema": "nk-jubensha/1",
        "meta": {"title": "The Slow Clock", "players": 3, "premise": "A retired judge is found dead in his study.",
                 "setting": "A country house, one winter evening."},
        "trick": {"family": "T1", "false_belief": "Vale died after ten, when Ash was in the hall.",
                  "how": "Before the killing the culprit turned the study clock twenty minutes slow.",
                  "why": "It makes Ash look elsewhere at the moment of death.",
                  "trace": "The clock disagrees with the church bell."},
        "places": [{"id": "P1", "name": "study"}, {"id": "P2", "name": "hall"}],
        "rounds": [{"n": 1, "title": "first search"}, {"n": 2, "title": "second search"}],
        "characters": [
            {"id": "A", "name": "Ash", "player": True, "culprit": True, "intro": "The nephew.",
             "sections": [{"title": "Evening", "text": "I sat in the hall from half nine.", "share": "table"},
                          {"title": "Truth", "text": "I did it. Ash moved the clock and the hands were set back.", "share": "private"}],
             "goals": [{"id": "A1", "kind": "hide", "text": "Keep them away from the clock."},
                       {"id": "A2", "kind": "bond", "text": "Stay close to Bell."}]},
            {"id": "B", "name": "Bell", "player": True, "intro": "The housekeeper.",
             "sections": [{"title": "Evening", "text": "I brought tea at twenty to ten.", "share": "table"},
                          {"title": "Secret", "text": "I took money from the desk.", "share": "private"}],
             "goals": [{"id": "B1", "kind": "find", "text": "Find who did it."}]},
            {"id": "C", "name": "Cole", "player": True, "intro": "The gardener.",
             "sections": [{"title": "Evening", "text": "I was by the chapel.", "share": "table"},
                          {"title": "Secret", "text": "I am the judge's son.", "share": "private"}],
             "goals": [{"id": "C1", "kind": "find", "text": "Learn why he died."}]},
        ],
        "npcs": [{"id": "V", "name": "Vale", "role": "victim"}],
        "clues": [
            {"id": "C1", "title": "Body", "text": "Vale was found at ten.", "source": {"kind": "host", "round": 1}},
            {"id": "C2", "title": "Tea", "text": "Vale was alive at twenty to ten.", "source": {"kind": "booklet", "holder": "B"}},
            {"id": "C3", "title": "Clock", "text": "The study clock's hands were set back twenty minutes.", "source": {"kind": "search", "place": "P1", "round": 1}},
            {"id": "C4", "title": "Bell", "text": "The chapel bell rang ten while the study clock showed twenty to.", "source": {"kind": "booklet", "holder": "C"}},
            {"id": "C5", "title": "Glove", "text": "Ash's glove behind the study curtain.", "source": {"kind": "search", "place": "P1", "round": 2}},
            {"id": "C6", "title": "Will", "text": "A new will leaves Ash nothing.", "source": {"kind": "search", "place": "P2", "round": 2}},
            {"id": "C7", "title": "Scarf", "text": "Bell's scarf on the study floor.", "source": {"kind": "booklet", "holder": "C"}},
            {"id": "C8", "title": "Morning", "text": "Bell dusted the study in the morning and left without her scarf.", "source": {"kind": "search", "place": "P2", "round": 1}},
            {"id": "C9", "title": "Chapel", "text": "The vicar saw Cole at the chapel from nine to ten.", "source": {"kind": "host", "round": 2}},
            {"id": "C10", "title": "Found", "text": "Ash says he found the body.", "source": {"kind": "booklet", "holder": "A"}},
        ],
        "solution": {
            "culprit": "A", "victim": "V",
            "summary": "The nephew killed his uncle at a quarter to ten, after slowing the study timepiece.",
            "steps": [
                {"id": "S1", "kind": "establish", "claim": "Death between 9:40 and 10.", "clues": ["C1", "C2", "C10"]},
                {"id": "S2", "kind": "break", "claim": "The clock was slow, so Ash's time is wrong.", "clues": ["C3", "C4"], "after": ["S1"]},
                {"id": "S3", "kind": "implicate", "target": "A", "claim": "Ash was in the study.", "clues": ["C5"], "after": ["S2"]},
                {"id": "S4", "kind": "motive", "claim": "Ash loses the inheritance.", "clues": ["C6"]},
                {"id": "S5", "kind": "eliminate", "target": "C", "claim": "Cole was at the chapel.", "clues": ["C9"]},
                {"id": "S6", "kind": "conclude", "target": "A", "claim": "Ash did it.", "clues": ["C5", "C6"], "after": ["S3", "S4"]},
            ],
            "alibi": {"holder": "A", "claim": "In the hall at ten to ten.", "step": "S2", "tokens": ["set back"]},
            "herrings": [{"id": "H1", "points_to": "B", "clues": ["C7"], "resolved_by": ["C8"]}],
            "secrets": ["Ash moved the clock"],
        },
    }


def _selftest_cases():
    def m(f):
        g = _fixture(); f(g); return g

    def clue(g, cid):
        return next(c for c in g["clues"] if c["id"] == cid)

    def char(g, cid):
        return next(c for c in g["characters"] if c["id"] == cid)

    def step(g, sid):
        return next(s for s in g["solution"]["steps"] if s["id"] == sid)

    extra_player = {"id": "D", "name": "Dove", "player": True, "intro": "A guest.",
                    "sections": [{"title": "Evening", "text": "I slept.", "share": "table"},
                                 {"title": "Secret", "text": "I owe money.", "share": "private"}],
                    "goals": [{"id": "D1", "kind": "find", "text": "Find out."}, {"id": "D2", "kind": "bond", "text": "Befriend Bell."},
                              {"id": "D3", "kind": "bond", "text": "Befriend Cole."}]}
    return [
        ("clean control", _fixture(), set()),
        ("J01 a clue deleted while a step still cites it", m(lambda g: g["clues"].remove(clue(g, "C5"))), {"J01"}),
        ("J01 steps that wait on each other in a circle", m(lambda g: step(g, "S1").__setitem__("after", ["S6"])), {"J01"}),
        ("J01 a player count that does not match", m(lambda g: g["meta"].__setitem__("players", 4)), {"J01"}),
        ("J02 a clue taken out of every booklet and search", m(lambda g: clue(g, "C6").__setitem__("source", {"kind": "none"})), {"J02"}),
        ("J02 a step with no clue", m(lambda g: step(g, "S4").__setitem__("clues", [])), {"J02"}),
        ("J03 an orphan clue", m(lambda g: g["clues"].append({"id": "C11", "title": "Vase", "text": "A cracked vase.", "source": {"kind": "search", "place": "P2", "round": 1}})), {"J03"}),
        ("J04 a red herring nothing resolves", m(lambda g: (g["solution"]["herrings"][0].__setitem__("resolved_by", []), g["clues"].remove(clue(g, "C8")))), {"J04"}),
        ("J04 a red herring resolved only by a clue nobody receives", m(lambda g: clue(g, "C8").__setitem__("source", {"kind": "none"})), {"J04"}),
        ("J05 a break token in an innocent's booklet", m(lambda g: char(g, "B")["sections"][0].__setitem__("text", "I brought tea; the hands were set back, I think.")), {"J05"}),
        ("J05 the intended clues do not carry the token", m(lambda g: g["solution"]["alibi"].__setitem__("tokens", ["set back", "wound down"])), {"J05"}),
        ("J05 a step names the culprit without the break", m(lambda g: step(g, "S3").__setitem__("after", [])), {"J05"}),
        ("J05 a break clue only the culprit holds", m(lambda g: clue(g, "C4").__setitem__("source", {"kind": "booklet", "holder": "A"})), {"J05"}),
        ("J05 no break step declared", m(lambda g: g["solution"]["alibi"].__setitem__("step", "S1")), {"J05"}),
        ("J06 the solution leaked into an innocent's booklet", m(lambda g: char(g, "C")["sections"][1].__setitem__("text", "I saw it: Ash moved the clock.")), {"J06"}),
        ("J06 the solution in the culprit's cover story", m(lambda g: char(g, "A")["sections"][0].__setitem__("text", "Ash moved the clock? Nonsense.")), {"J06"}),
        ("J06 no secret declared", m(lambda g: g["solution"].__setitem__("secrets", [])), {"J06"}),
        ("J07 every innocent cleared without the proof", m(lambda g: g["solution"]["steps"].append({"id": "S7", "kind": "eliminate", "target": "B", "claim": "Bell was elsewhere.", "clues": ["C8"]})), {"J07"}),
        ("J07 no positive proof against the culprit", m(lambda g: step(g, "S3").__setitem__("kind", "establish")), {"J07"}),
        ("J08 a step only the culprit can prove", m(lambda g: clue(g, "C6").__setitem__("source", {"kind": "booklet", "holder": "A"})), {"J08"}),
        ("J09 a player with no goal", m(lambda g: char(g, "B").__setitem__("goals", [])), {"J09"}),
        ("J09 a player with no secret", m(lambda g: char(g, "C")["sections"].pop(1)), {"J09"}),
        ("J09 a culprit with nothing to hide", m(lambda g: char(g, "A")["goals"][0].__setitem__("kind", "find")), {"J09"}),
        ("J09 a player the chain never needs", m(lambda g: (g["characters"].append(copy.deepcopy(extra_player)), g["meta"].__setitem__("players", 4))), {"J09"}),
        ("J10 one role with far more to do", m(lambda g: char(g, "B")["goals"].extend({"id": f"B{i}", "kind": "bond", "text": "x"} for i in range(2, 8))), {"W10"}),
        ("J11 a step only one innocent can prove", m(lambda g: clue(g, "C9").__setitem__("source", {"kind": "booklet", "holder": "B"})), {"W11"}),
        ("J12 a trick family outside the taxonomy", m(lambda g: g["trick"].__setitem__("family", "T99")), {"J12"}),
        ("J12 a trick with no trace", m(lambda g: g["trick"].__setitem__("trace", "")), {"J12"}),
        ("J13 host text copied into a clue", m(lambda g: clue(g, "C5").__setitem__("text", "Ash's glove. The nephew killed his uncle at a quarter to ten.")), {"W13"}),
        # every J01 line has a sample of its own (the break matrix found eleven reporting lines no sample could see)
        ("J01 an id used twice", m(lambda g: g["clues"].append(dict(clue(g, "C1")))), {"J01"}),
        ("J01 a clue with no text", m(lambda g: clue(g, "C6").__setitem__("text", "")), {"J01"}),
        ("J01 a clue source of an unknown kind", m(lambda g: clue(g, "C6").__setitem__("source", {"kind": "shelf"})), {"J01"}),
        ("J01 a search card in a place that does not exist", m(lambda g: clue(g, "C6").__setitem__("source", {"kind": "search", "place": "P9", "round": 1})), {"J01"}),
        ("J01 a step waiting on a step that does not exist", m(lambda g: step(g, "S4").__setitem__("after", ["S99"])), {"J01"}),
        ("J01 a step of an unknown kind", m(lambda g: step(g, "S4").__setitem__("kind", "vibe")), {"J01"}),
        ("J01 a step naming someone who is not a character", m(lambda g: step(g, "S5").__setitem__("target", "Z")), {"J01"}),
        ("J01 a red herring pointing at nobody", m(lambda g: g["solution"]["herrings"][0].__setitem__("points_to", "Z")), {"J01"}),
        ("J01 a red herring citing a clue that does not exist", m(lambda g: g["solution"]["herrings"][0].__setitem__("clues", ["C7", "C99"])), {"J01"}),
        ("J01 a goal citing a clue that does not exist", m(lambda g: char(g, "A")["goals"][0].__setitem__("clues", ["C99"])), {"J01"}),
        ("J01 two players flagged as the culprit", m(lambda g: char(g, "B").__setitem__("culprit", True)), {"J01"}),
        ("J05 no break tokens declared", m(lambda g: g["solution"]["alibi"].__setitem__("tokens", [])), {"J05"}),
        ("J09 a player with nothing to tell the table", m(lambda g: char(g, "C")["sections"].pop(0)), {"J09"}),
        ("J09 an innocent with nothing to find", m(lambda g: char(g, "B")["goals"][0].__setitem__("kind", "bond")), {"J09"}),
        # controls that must stay clean: an over-firing rule turns them red
        ("clean: a clearing after the proof does not count (J07)", m(lambda g: g["solution"]["steps"].append(
            {"id": "S7", "kind": "eliminate", "target": "B", "claim": "Bell is cleared once Ash is proved.", "clues": ["C8"], "after": ["S3"]})), set()),
        ("clean: a small imbalance is tolerated (J10)", m(lambda g: char(g, "B")["goals"].append({"id": "B2", "kind": "bond", "text": "Protect Cole."})), set()),
    ]


def selftest():
    ok, lines = True, []
    for label, g, want in _selftest_cases():
        got = {c for c, _ in check(g)}
        hit = got == want
        ok &= hit
        lines.append(f"  {'✔' if hit else '✘'} {label}" + ("" if hit else f" → want {sorted(want)}, got {sorted(got)}"))
    return ok, lines


def load(path):
    try:
        g = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"cannot read {path}: {e}"
    if not isinstance(g, dict):
        return None, f"{path} is not a JSON object"
    return g, None


def report(findings):
    errs = [f for f in findings if not f[0].startswith("W")]
    warns = [f for f in findings if f[0].startswith("W")]
    lines = [f"{len(errs)} errors, {len(warns)} warnings"]
    lines += [f"  ERROR {c}  {m}" for c, m in errs]
    lines += [f"  warn  {m}" for _, m in warns]
    return errs, warns, lines


def main(argv):
    ok, lines = selftest()
    if not ok or "--selftest" in argv:
        print(f"chain_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed")
        print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — no results are trusted")
            return 2
        return 0
    files = [a for a in argv if not a.startswith("--") and (argv.index(a) == 0 or argv[argv.index(a) - 1] != "--json")]
    if not files:
        print(__doc__)
        return 2
    g, err = load(files[0])
    if err:
        print(err)
        return 2
    findings = check(g)
    errs, warns, lines = report(findings)
    print(f"chain_check · {files[0]} · " + lines[0])
    print("\n".join(lines[1:]))
    if "--json" in argv:
        json.dump([{"code": c, "message": m} for c, m in findings], open(argv[argv.index("--json") + 1], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return 1 if errs or ("--strict" in argv and warns) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

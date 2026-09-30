#!/usr/bin/env python3
"""detective.py — play the game blind: build what the table knows, hand it to a model that never saw the solution,
and grade what it answers against the solution.

    python3 detective.py prompt game.json --out prompt.md
    python3 detective.py run --engine claude|codex --prompt prompt.md --out RUN_DIR [--model M] [--timeout SECONDS]
    python3 detective.py grade game.json RUN_DIR/answer.txt [--json OUT]
    python3 detective.py --selftest

prompt  The table's material only: every character's table pages (private pages stay out; the culprit contributes
        only the cover story), the search cards, the host's announcements and the clues innocent players hold. The
        culprit's own clues, goals, the trick, the solution and the host text stay out. It refuses to write a prompt
        that contains a declared solution phrase or a long run of host-only or culprit-only text.
run     Starts a second session in an empty temporary folder with the prompt on standard input and keeps the raw
        transcript: `claude -p` with every tool switched off, or `codex exec` in a read-only sandbox with no user
        config and no saved session. RUN_DIR gets transcript.jsonl, answer.txt, stderr.txt and run.json (the exact
        command, versions, timing, and how many tool calls or commands the session made; it should be zero).
        Inside Claude Code a subagent given only the prompt text is the other way to run it (see SKILL.md).
grade   SOLVED in N steps (right culprit, and the cover broken through the intended clues) · RIGHT NAME, COVER NOT
        BROKEN (named by elimination or a guess) · WRONG (accused someone else) · UNSOLVABLE (the detective said the
        material is not enough) · UNREADABLE (no JSON answer). For every verdict but SOLVED it lists the solution
        steps nobody reached and the clues that carry them, with who holds each: "unsolvable: clue C07 missing".
        It also checks where the answer came from: verified only when the answer's folder holds the run.json and
        transcript.jsonl of `detective.py run`, the answer is the transcript's last message word for word, and the
        session made no tool calls. Anything else starts with UNVERIFIED (no run record, an edited answer, a session
        that used tools) before the verdict: a grade on an answer the game's writer typed or tidied says nothing.

Exit: prompt/run 0 ok, 1 refused or failed · grade 0 SOLVED and verified, 3 SOLVED but unverified, 1 any other
verdict, 2 unreadable · 2 failed self-test.
Standard library only, Python 3.9+; `run` needs the claude or codex command line installed and signed in.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chain_check  # noqa: E402

LEAK_RUN = 16   # characters of host-only or culprit-only text that may not appear in a prompt word for word

HEAD = {
    "zh": {"title": "{t} · 桌上的全部材料", "premise": "前提", "places": "场所", "accounts": "每个人对大家说的话（任何人都可能说谎）",
           "host": "主持人公布的", "search": "搜证找到的线索卡", "held": "玩家手里的线索（持有人拿了出来）", "round": "第{n}轮",
           "holds": "{n}持有", "act": "第{n}幕"},
    "en": {"title": "{t} · everything on the table", "premise": "Premise", "places": "Places",
           "accounts": "What each character tells the table (anyone may be lying)", "host": "Announced by the host",
           "search": "Clue cards found in the searches", "held": "Clues players hold (shared by their holders)",
           "round": "round {n}", "holds": "held by {n}", "act": "act {n}"},
}

INSTRUCTIONS = """You are the detective at a murder-mystery party game. Below is everything the players have put on the table
after both search rounds: what each character says about themselves (anyone may be lying, the culprit certainly is),
the clue cards found in the searches, the host's announcements, and the clues players hold in their booklets.
Pages and held clues are written to the character they belong to, so "you" in them means that character.
You have not seen the solution. Nothing outside this message belongs to the task: do not read files, run commands
or search the web.

Work out who killed the victim, how, and why, from this material only.
- Every step of your reasoning cites the clue IDs it stands on, like [C07]. A character's own account is a claim,
  not a fact, unless a clue backs it.
- Do not name anyone by elimination alone. If you name someone, show the evidence that points at them, and explain
  how they got past whatever makes them look innocent.
- If the material is not enough to name the culprit with evidence, say so: verdict "unsolvable", and write exactly
  which fact is missing.

Answer with one JSON object and nothing else:
{"verdict": "solved" or "unsolvable", "culprit": "<name, or empty>", "how": "<how it was done>", "why": "<motive>",
 "chain": [{"step": 1, "claim": "<one deduction>", "clues": ["C04", "C02"]}],
 "cleared": [{"who": "<name>", "why": "<why not them>", "clues": ["C24"]}],
 "missing": "<if unsolvable: the fact that is missing>", "confidence": "high, medium or low"}
Write the claims in the language of the material."""


def lang(g):
    return "en" if (g.get("meta") or {}).get("lang") == "en" else "zh"


def packet(g):
    """the table's material as text, and the set of clue ids in it"""
    G, h = chain_check.Game(g), HEAD[lang(g)]
    out = [f"# {h['title'].format(t=G.meta.get('title', ''))}", "", f"## {h['premise']}", str(G.meta.get("premise", "")),
           str(G.meta.get("setting", "")), "", f"## {h['places']}"]
    out += [f"- {p.get('name')}: {p.get('desc', '')}".rstrip(": ") for p in G.places]
    out += ["", f"## {h['accounts']}"]
    for c in G.chars:
        if c.get("id") not in G.players:
            continue
        out += ["", f"### {c.get('name')}: {c.get('intro', '')}"]
        for s in c.get("sections") or []:
            if s.get("share") == "table":
                out.append(f"({h['act'].format(n=s.get('act', 1))}) {s.get('title', '')}: {s.get('text', '')}")
    shown = set()

    def line(cl, extra):
        shown.add(cl.get("id"))
        return f"[{cl.get('id')}] {cl.get('title', '')} ({extra}): {cl.get('text', '')}"

    pname = {p.get("id"): p.get("name") for p in G.places}
    out += ["", f"## {h['host']}"]
    out += [line(cl, h["round"].format(n=cl["source"].get("round"))) for cl in G.clues if (cl.get("source") or {}).get("kind") == "host"]
    out += ["", f"## {h['search']}"]
    out += [line(cl, h["round"].format(n=cl["source"].get("round")) + " · " + str(pname.get(cl["source"].get("place"), "")))
            for cl in G.clues if (cl.get("source") or {}).get("kind") == "search"]
    out += ["", f"## {h['held']}"]
    out += [line(cl, h["holds"].format(n=G.name(cl["source"].get("holder"))))
            for cl in G.clues if (cl.get("source") or {}).get("kind") == "booklet"
            and cl["source"].get("holder") in G.players and not G.culprit_held(cl)]
    return "\n".join(out) + "\n", shown


def _flat(s):
    return re.sub(r"\s+", "", str(s))


def _run_in(src, flat, allowed=""):
    """the first LEAK_RUN-long run of src that appears in flat and not in allowed"""
    s = _flat(src)
    return next((s[i:i + LEAK_RUN] for i in range(len(s) - LEAK_RUN + 1)
                 if s[i:i + LEAK_RUN] in flat and s[i:i + LEAK_RUN] not in allowed), None)


def leaks(g, text):
    """What in a prompt would give the answer away: a declared solution phrase; a run of the solution summary or the
    trick's how (pure answer text, refused wherever it came from); a run of a private page or a culprit-only clue that
    no table page or shown clue contains (so the packet itself let it through). A private page that repeats a public
    clue word for word is not a leak: the clue is on the table anyway."""
    G, found = chain_check.Game(g), []
    for x in G.sol.get("secrets") or []:
        if x and x in text:
            found.append(f"solution phrase {x!r}")
    flat = _flat(text)
    for where, src in (("solution summary", G.sol.get("summary", "")), ("trick how", (g.get("trick") or {}).get("how", ""))):
        hit = _run_in(src, flat)
        if hit:
            found.append(f"{where}: {hit!r}")
    public = [G.meta.get(k, "") for k in ("title", "premise", "setting")] + [str(p.get("name", "")) + str(p.get("desc", "")) for p in G.places]
    for c in G.chars:
        public.append(c.get("intro", ""))
        public += [str(s.get("title", "")) + str(s.get("text", "")) for s in c.get("sections") or [] if s.get("share") == "table"]
    public += [str(cl.get("title", "")) + str(cl.get("text", "")) for cl in G.clues if not G.culprit_held(cl) and G.received(cl)]
    allowed = "\u0000".join(_flat(x) for x in public)
    for c in G.chars:
        for s in c.get("sections") or []:
            if s.get("share") == "private":
                hit = _run_in(s.get("text", ""), flat, allowed)
                if hit:
                    found.append(f"{c.get('name')}'s private page: {hit!r}")
    for cl in G.clues:
        if G.culprit_held(cl):
            hit = _run_in(cl.get("text", ""), flat, allowed)
            if hit:
                found.append(f"culprit-held clue {cl.get('id')}: {hit!r}")
    return found


def build_prompt(g):
    body, shown = packet(g)
    text = INSTRUCTIONS + "\n\n---\n\n" + body
    return text, shown, leaks(g, text)


# ── grading ──
def extract_json(text):
    """the answer object: a fenced block, else the first balanced {...} that parses"""
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    for s in starts:
        depth, instr, esc = 0, False, False
        for j in range(s, len(text)):
            ch = text[j]
            if instr:
                esc = (ch == "\\" and not esc)
                if ch == '"' and not esc:
                    instr = False
                if ch != "\\":
                    esc = False
                continue
            if ch == '"':
                instr = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[s:j + 1])
                        if isinstance(obj, dict):
                            return obj
                    except ValueError:
                        pass
                    break
    return None


def who_holds(G, cid):
    cl = G.clue.get(cid) or {}
    src = cl.get("source") or {}
    if src.get("kind") == "booklet":
        return f"held by {G.name(src.get('holder'))}"
    if src.get("kind") == "search":
        pl = next((p.get("name") for p in G.places if p.get("id") == src.get("place")), src.get("place"))
        return f"search card, round {src.get('round')}, {pl}"
    if src.get("kind") == "host":
        return f"host, round {src.get('round')}"
    return "nobody receives it"


def resolve(G, named):
    """the character a detective named: an exact id or name; else the one character whose name contains the named
    text or is contained in it ("Lin Wen" for "Lin Wen — storyteller"); None when nobody or more than one fits"""
    n = named.strip()
    if not n:
        return None
    exact = [c.get("id") for c in G.chars if n in (c.get("id"), c.get("name"))]
    if len(exact) == 1:
        return exact[0]
    near = [c.get("id") for c in G.chars if c.get("name") and (c["name"] in n or (len(n) >= 2 and n in c["name"]))]
    return near[0] if len(near) == 1 else None


def provenance(answer_path, answer_text):
    """(verified, line) — whether the answer's own folder shows a blind session wrote it: a run.json and a transcript
    written by `detective.py run`, the answer equal to the last message in that transcript, a session that made no tool
    calls or commands and ended normally. An answer typed or tidied by the session that wrote the game fails here."""
    d = os.path.dirname(os.path.abspath(answer_path))
    rj, tj = os.path.join(d, "run.json"), os.path.join(d, "transcript.jsonl")
    if not (os.path.isfile(rj) and os.path.isfile(tj)):
        return False, "NO RUN RECORD: no run.json and transcript.jsonl beside the answer, so nothing shows that a blind session wrote it"
    try:
        info = json.load(open(rj, encoding="utf-8"))
    except ValueError:
        return False, "NO RUN RECORD: run.json is not readable"
    last = final_text(str(info.get("engine", "")), open(tj, encoding="utf-8", errors="replace").read(), os.path.join(d, "\u0000none"))
    if last.strip() != (answer_text or "").strip():
        return False, "ANSWER EDITED: answer.txt is not the last message of transcript.jsonl"
    if info.get("tool_calls_or_commands"):
        return False, f"the detective session made {info.get('tool_calls_or_commands')} tool calls or commands, so it may have read more than the prompt"
    if info.get("exit") != 0:
        return False, f"the detective session did not end normally (exit {info.get('exit')})"
    models = ", ".join(info.get("models_in_transcript") or []) or str(info.get("model"))
    return True, f"run record: {info.get('engine')} ({info.get('version')}), {models}, 0 tool calls, the answer is the transcript's last message"


def grade(g, answer_text, answer_path=None):
    """(verdict line, detail lines, facts dict). With answer_path, the answer's folder is checked for a run record
    (provenance); a SOLVED without one is marked UNVERIFIED."""
    G = chain_check.Game(g)
    a = extract_json(answer_text or "")
    if not isinstance(a, dict):
        return "UNREADABLE — no JSON answer found", [], {"verdict": "UNREADABLE"}
    chain = [x for x in a.get("chain") or [] if isinstance(x, dict)]
    cited = []
    for x in chain:
        for c in x.get("clues") or []:
            if isinstance(c, str):
                cited.append(c.strip().strip("[]"))
    cited_set = set(cited)
    shown = packet(g)[1]
    stray = sorted(c for c in cited_set if c not in shown)
    reached = {}
    for s in G.steps:
        keys = s.get("key") or s.get("clues") or []
        reached[s.get("id")] = any(c in cited_set for c in keys)
    brk = (G.sol.get("alibi") or {}).get("step")
    culprit = G.char.get(G.culprit) or {}
    named = str(a.get("culprit") or "").strip()
    right = bool(named) and resolve(G, named) == G.culprit
    said_unsolvable = str(a.get("verdict", "")).lower().startswith("unsolv") or not named
    n = len(chain)
    missing = [s for s in G.steps if not reached[s.get("id")]]

    def missing_lines():
        out = []
        for s in missing:
            keys = s.get("key") or s.get("clues") or []
            out.append(f"  not reached {s.get('id')} ({s.get('kind')}): {s.get('claim', '')}")
            out.append("      needs " + " or ".join(f"{c} ({who_holds(G, c)})" for c in keys))
        return out

    facts = {"steps_in_answer": n, "cited": sorted(cited_set), "stray_citations": stray,
             "reached": sorted(k for k, v in reached.items() if v), "not_reached": [s.get("id") for s in missing],
             "named": named, "culprit": culprit.get("name"), "break_step": brk}
    brk_keys = (G.step.get(brk) or {}).get("key") or (G.step.get(brk) or {}).get("clues") or []
    if said_unsolvable:
        head = (f"UNSOLVABLE — the detective could not name anyone with evidence; "
                + (f"unsolvable: clue {' / '.join(brk_keys)} missing (break step {brk})" if not reached.get(brk) else "the break was reached"))
        verdict = "UNSOLVABLE"
    elif not right:
        head = f"WRONG — accused {named}; the culprit is {culprit.get('name')}"
        verdict = "WRONG"
    elif not reached.get(brk):
        order = sorted(cited_set, key=lambda c: (-cited.count(c), c))
        head = (f"RIGHT NAME, COVER NOT BROKEN — named {named} without citing any break clue ({', '.join(brk_keys)}): "
                f"a guess, elimination, or a cover that breaks another way; read the chain, it leaned on {', '.join(order[:8]) or 'nothing'}")
        verdict = "RIGHT_NAME_NO_BREAK"
    else:
        head = (f"SOLVED in {n} steps — named {culprit.get('name')} and broke the cover through "
                f"{', '.join(c for c in brk_keys if c in cited_set)}; {sum(reached.values())} of {len(G.steps)} solution steps reached")
        verdict = "SOLVED"
    facts["verdict"] = verdict
    detail = []
    if a.get("missing"):
        detail.append(f"  the detective says missing: {a.get('missing')}")
    if verdict != "SOLVED":
        detail += missing_lines()
    elif missing:
        detail += [f"  also not reached: {', '.join(s.get('id') for s in missing)} (the answer did not need them or took another route)"]
    if stray:
        detail.append(f"  cited clue ids that are not on the table: {', '.join(stray)} (a leak or an invention: look)")
    if answer_path is not None:
        ok, line = provenance(answer_path, answer_text)
        facts["verified"] = ok
        detail.insert(0, "  " + line)
        if not ok:
            head = "UNVERIFIED (" + line.split(":")[0].lower() + ") · as graded: " + head
    return head, detail, facts


# ── running a second session ──
def engine_argv(engine, tmp, answer_path, model=None):
    if engine == "claude":
        exe = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"
        return [exe, "-p", "--output-format", "stream-json", "--verbose", "--tools", "", "--no-session-persistence"] + \
               (["--model", model] if model else [])
    if engine == "codex":
        exe = os.environ.get("CODEX_BIN") or shutil.which("codex") or "codex"
        return [exe, "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config", "-s", "read-only",
                "-C", tmp, "-o", answer_path] + (["-m", model] if model else []) + ["-"]
    if engine.startswith("stub:"):            # self-test only: a stand-in that prints what a session would
        return [sys.executable, "-c", engine[5:]]
    raise ValueError(f"unknown engine {engine!r} (claude or codex)")


def final_text(engine, transcript, answer_path):
    """the session's last answer: the file codex wrote with -o, else the last result (claude stream-json) or the last
    agent message (codex --json) in the transcript"""
    if os.path.isfile(answer_path) and open(answer_path, encoding="utf-8").read().strip():
        return open(answer_path, encoding="utf-8").read()
    last = ""
    for ln in transcript.splitlines():
        try:
            ev = json.loads(ln)
        except ValueError:
            continue
        if ev.get("type") == "result" and isinstance(ev.get("result"), str):
            last = ev["result"]
        item = ev.get("item") or {}
        if ev.get("type") == "item.completed" and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            last = item["text"]
    return last or (transcript if engine.startswith("stub:") else "")


def models_used(transcript):
    """model names the transcript itself reports (claude stream-json carries them; codex --json does not)"""
    return sorted(set(re.findall(r'"model"\s*:\s*"([^"]+)"', transcript)))


def tool_calls(transcript):
    n = 0
    for ln in transcript.splitlines():
        try:
            ev = json.loads(ln)
        except ValueError:
            continue
        blob = json.dumps(ev)
        if ev.get("type") == "assistant":
            n += sum(1 for part in ((ev.get("message") or {}).get("content") or []) if isinstance(part, dict) and part.get("type") == "tool_use")
        elif '"command_execution"' in blob and ev.get("type") in ("item.started", "item.completed") and \
                (ev.get("item") or {}).get("type") == "command_execution" and ev.get("type") == "item.started":
            n += 1
    return n


def answer_file(out_dir):
    """absolute, because codex resolves -o inside the folder it was given with -C (a relative path fails there)"""
    return os.path.abspath(os.path.join(out_dir, "answer.txt"))


def run(engine, prompt_path, out_dir, model=None, timeout=900):
    prompt = open(prompt_path, encoding="utf-8").read()
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="nkj-detective-")
    answer_path = answer_file(out_dir)
    if os.path.exists(answer_path):
        os.remove(answer_path)
    argv = engine_argv(engine, tmp, answer_path, model)
    before = sorted(os.listdir(tmp))
    t0 = time.time()
    try:
        r = subprocess.run(argv, input=prompt, capture_output=True, text=True, cwd=tmp, timeout=timeout)
        rc, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = "timeout", (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
    except OSError as e:
        rc, out, err = "not started", "", str(e)
    after = sorted(os.listdir(tmp))
    open(os.path.join(out_dir, "transcript.jsonl"), "w", encoding="utf-8").write(out)
    open(os.path.join(out_dir, "stderr.txt"), "w", encoding="utf-8").write(err)
    text = final_text(engine, out, answer_path)
    if not os.path.isfile(answer_path):
        open(answer_path, "w", encoding="utf-8").write(text)
    version = ""
    if not engine.startswith("stub:"):
        try:
            version = subprocess.run([argv[0], "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            version = "unknown"
    info = {"engine": engine, "version": version, "model": model or "(the CLI's default)", "models_in_transcript": models_used(out),
            "argv": [("<empty temp folder>" if a == tmp else "<run folder>/answer.txt" if a == answer_path else a) for a in argv]
                    if not engine.startswith("stub:") else ["<stub>"],
            "prompt_file": os.path.basename(prompt_path),
            "prompt_chars": len(prompt), "cwd": "<empty temp folder>", "cwd_before": before, "cwd_after": after,
            "exit": rc, "seconds": round(time.time() - t0, 1), "tool_calls_or_commands": tool_calls(out),
            "started": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0))}
    json.dump(info, open(os.path.join(out_dir, "run.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    return info


# ── self-test ──
def selftest():
    ok, lines = True, []

    def chk(cond, label):
        nonlocal ok
        ok &= bool(cond)
        lines.append(f"  {'✔' if cond else '✘'} {label}")

    g = chain_check._fixture()
    text, shown, lk = build_prompt(g)
    chk(not lk, f"D01 the fixture's prompt has no leak ({lk})")
    chk("Ash moved the clock" not in text and "I did it" not in text, "D02 the culprit's private page stays out")
    chk("I took money from the desk." not in text and "I am the judge's son." not in text, "D03 innocents' private pages stay out")
    chk("Ash says he found the body." not in text and "C10" not in shown, "D04 a clue only the culprit holds stays out")
    chk("I sat in the hall from half nine." in text, "D05 the culprit's cover story is on the table")
    chk(all(f"[{c}]" in text for c in ("C1", "C3", "C5", "C9", "C2", "C4", "C7")), "D06 host, search and innocent-held clues are on the table")
    chk("Keep them away" not in text and "Find who did it" not in text and "slowing the study timepiece" not in text, "D07 goals and the solution stay out")
    g2 = chain_check._fixture()
    g2["characters"][1]["sections"][0]["text"] += " Ash moved the clock."
    chk(any("solution phrase" in x for x in build_prompt(g2)[2]), "D08 a solution phrase in a table page is refused")
    g3 = chain_check._fixture()
    g3["clues"][4]["text"] += " The nephew killed his uncle at a quarter to ten."
    chk(any("solution summary" in x for x in build_prompt(g3)[2]), "D09 host-only text copied into a clue is refused")
    leaky = text + "\n" + g["characters"][0]["sections"][1]["text"] + "\n" + g["characters"][2]["sections"][1]["text"]
    lk2 = leaks(g, leaky)
    chk(any("Ash's private page" in x for x in lk2) and any("Cole's private page" in x for x in lk2),
        "D21 a packet that lets private pages through is refused")
    good = json.dumps({"verdict": "solved", "culprit": "Ash", "chain": [
        {"step": 1, "claim": "window", "clues": ["C1", "C2"]}, {"step": 2, "claim": "slow clock", "clues": ["C3", "C4"]},
        {"step": 3, "claim": "glove", "clues": ["C5"]}, {"step": 4, "claim": "will", "clues": ["C6"]}]})
    v = grade(g, "Here is my answer:\n```json\n" + good + "\n```")
    chk(v[0].startswith("SOLVED in 4 steps"), f"D10 a right answer through the break is SOLVED ({v[0][:40]})")
    noskip = json.dumps({"verdict": "solved", "culprit": "Ash", "chain": [{"step": 1, "claim": "only one left", "clues": ["C9", "C8"]}]})
    chk(grade(g, noskip)[0].startswith("RIGHT NAME, COVER NOT BROKEN"), "D11 the right name without the break is not SOLVED")
    wrong = json.dumps({"verdict": "solved", "culprit": "Bell", "chain": [{"step": 1, "claim": "scarf", "clues": ["C7"]}]})
    w = grade(g, wrong)
    chk(w[0].startswith("WRONG") and any("not reached S2" in d for d in w[1]), "D12 a wrong accusation is WRONG and lists what was not reached")
    uns = json.dumps({"verdict": "unsolvable", "culprit": "", "chain": [], "missing": "when did he die"})
    u = grade(g, uns)
    chk(u[0].startswith("UNSOLVABLE") and "clue C3 / C4 missing" in u[0], f"D13 unsolvable names the missing break clues ({u[0][60:120]})")
    chk(grade(g, "I think it was the butler.")[0].startswith("UNREADABLE"), "D14 an answer with no JSON is UNREADABLE")
    stray = json.dumps({"verdict": "solved", "culprit": "Ash", "chain": [{"step": 1, "claim": "x", "clues": ["C3", "C10"]}]})
    chk(any("not on the table: C10" in d for d in grade(g, stray)[1]), "D15 a citation of a clue that is not on the table is flagged")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "prompt.md")
        open(p, "w", encoding="utf-8").write(text)
        stub = "import sys; sys.stdin.read(); print('{\"verdict\": \"solved\", \"culprit\": \"Ash\", \"chain\": []}')"
        info = run("stub:" + stub, p, os.path.join(d, "run"))
        ans = open(os.path.join(d, "run", "answer.txt"), encoding="utf-8").read()
        chk(info["exit"] == 0 and '"culprit": "Ash"' in ans and os.path.isfile(os.path.join(d, "run", "transcript.jsonl")),
            "D16 run keeps the transcript and the answer")
        chk(info["cwd_before"] == [] and info["tool_calls_or_commands"] == 0, "D17 run starts in an empty folder and counts tool calls")
    a = engine_argv("claude", "/tmp/x", "/tmp/a")
    chk("--tools" in a and a[a.index("--tools") + 1] == "" and "-p" in a, "D18 claude runs with every tool switched off")
    b = engine_argv("codex", "/tmp/x", "/tmp/a")
    chk(all(f in b for f in ("--ephemeral", "--ignore-user-config", "read-only", "--skip-git-repo-check")) and b[-1] == "-",
        "D19 codex runs read-only, with no user config and no saved session, prompt on stdin")
    tr = "\n".join([json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}]}}),
                    json.dumps({"type": "item.started", "item": {"type": "command_execution", "command": "ls"}})])
    chk(tool_calls(tr) == 2, "D20 tool calls and commands in a transcript are counted")
    cx = "\n".join([json.dumps({"type": "thread.started"}),
                    json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "{\"culprit\": \"Ash\"}"}})])
    chk(final_text("codex", cx, "/nonexistent/answer.txt") == "{\"culprit\": \"Ash\"}", "D22 a codex answer is read from its agent message when -o wrote nothing")
    cl = json.dumps({"type": "system", "model": "m-1"}) + "\n" + json.dumps({"type": "result", "result": "ok"})
    chk(final_text("claude", cl, "/nonexistent/a") == "ok" and models_used(cl) == ["m-1"], "D23 a claude answer and its model are read from the transcript")
    chk(os.path.isabs(answer_file(os.path.join("run", "one"))), "D24 the answer path is absolute (codex resolves -o inside its own folder)")
    echoed = ('The format was {"verdict": "solved" or "unsolvable", "chain": [{"step": 1, "clues": ["C1"]}]}; my answer:\n```json\n'
              + good + "\n```")
    chk(grade(g, echoed)[0].startswith("SOLVED"), "D25 an answer after an echoed template is read from its fenced block")
    g5 = chain_check._fixture()
    g5["characters"][0]["name"] = "Ash — the nephew"
    chk(grade(g5, good)[0].startswith("SOLVED"), "D26 a culprit named without the role in the name still counts")
    g6 = chain_check._fixture()
    g6["characters"][0]["name"] = "Ash Vale"
    g6["characters"][1]["name"] = "Ash Bell"
    chk(resolve(chain_check.Game(g6), "Ash") is None and resolve(chain_check.Game(g6), "Ash Vale") == "A",
        "D27 a partial name two characters share counts for nobody")
    with tempfile.TemporaryDirectory() as d3:
        bare = os.path.join(d3, "bare", "answer.txt"); os.makedirs(os.path.dirname(bare))
        open(bare, "w", encoding="utf-8").write(good)
        h = grade(g, good, bare)
        chk(h[0].startswith("UNVERIFIED (no run record)") and "SOLVED in 4 steps" in h[0] and h[2].get("verified") is False,
            "D28 an answer with no run record is graded UNVERIFIED, first word")
        stub_ok = "import sys; sys.stdin.read(); print(" + repr(good) + ")"
        open(os.path.join(d3, "p.md"), "w", encoding="utf-8").write(text)
        run("stub:" + stub_ok, os.path.join(d3, "p.md"), os.path.join(d3, "r"))
        ans = open(os.path.join(d3, "r", "answer.txt"), encoding="utf-8").read()
        v = grade(g, ans, os.path.join(d3, "r", "answer.txt"))
        chk(v[2].get("verified") is True and "UNVERIFIED" not in v[0], "D29 an answer written by run, unchanged, is verified")
        open(os.path.join(d3, "r", "answer.txt"), "w", encoding="utf-8").write(good.replace('"C5"', '"C5", "C4"'))
        e = grade(g, open(os.path.join(d3, "r", "answer.txt"), encoding="utf-8").read(), os.path.join(d3, "r", "answer.txt"))
        chk(e[0].startswith("UNVERIFIED (answer edited)"), "D30 an answer edited after the run is marked UNVERIFIED")
        rj = os.path.join(d3, "r", "run.json"); ri = json.load(open(rj)); ri["tool_calls_or_commands"] = 2; json.dump(ri, open(rj, "w"))
        open(os.path.join(d3, "r", "answer.txt"), "w", encoding="utf-8").write(ans)
        t2 = grade(g, ans, os.path.join(d3, "r", "answer.txt"))
        chk(t2[0].startswith("UNVERIFIED") and t2[2].get("verified") is False, "D31 a detective session that used tools is marked UNVERIFIED")
        ri["tool_calls_or_commands"] = 0; ri["exit"] = "timeout"; json.dump(ri, open(rj, "w"))
        t3 = grade(g, ans, os.path.join(d3, "r", "answer.txt"))
        chk(t3[0].startswith("UNVERIFIED") and t3[2].get("verified") is False, "D32 a detective session that did not end normally is marked UNVERIFIED")
    return ok, lines


def main(argv):
    ok, lines = selftest()
    if not ok or "--selftest" in argv:
        print(f"detective selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed")
        print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — no results are trusted")
            return 2
        return 0
    if not argv or argv[0] not in ("prompt", "run", "grade"):
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]

    def opt(name, default=None):
        return rest[rest.index(name) + 1] if name in rest else default

    flagged = {opt(x) for x in ("--out", "--engine", "--prompt", "--model", "--timeout", "--json")}
    files = [a for a in rest if not a.startswith("--") and a not in flagged]
    if cmd == "prompt":
        if not files:
            print(__doc__); return 2
        g, err = chain_check.load(files[0])
        if err:
            print(err); return 2
        text, shown, lk = build_prompt(g)
        if lk:
            print("refused: the prompt would give the solution away:\n  " + "\n  ".join(lk)); return 1
        out = opt("--out")
        if out:
            open(out, "w", encoding="utf-8").write(text)
        else:
            sys.stdout.write(text)
        print(f"prompt: {len(text)} characters, {len(shown)} clues on the table, 0 leaks" + (f" → {out}" if out else ""), file=sys.stderr)
        return 0
    if cmd == "run":
        eng, pr, out = opt("--engine"), opt("--prompt"), opt("--out")
        if eng not in ("claude", "codex") or not pr or not out:
            print(__doc__); return 2
        info = run(eng, pr, out, opt("--model"), int(opt("--timeout", "900")))
        print(json.dumps(info, ensure_ascii=False, indent=1))
        return 0 if info["exit"] == 0 else 1
    if cmd == "grade":
        if len(files) < 2:
            print(__doc__); return 2
        g, err = chain_check.load(files[0])
        if err:
            print(err); return 2
        try:
            ans = open(files[1], encoding="utf-8").read()
        except OSError as e:
            print(f"cannot read {files[1]}: {e}"); return 2
        head, detail, facts = grade(g, ans, files[1])
        print(head)
        if detail:
            print("\n".join(detail))
        if opt("--json"):
            json.dump(facts, open(opt("--json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if facts["verdict"] == "SOLVED":
            return 0 if facts.get("verified") else 3
        return 2 if facts["verdict"] == "UNREADABLE" else 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""booklets.py — render a game.json as printable HTML: one booklet per player, the clue cards, the host handbook and a
cover page that links them.

    python3 booklets.py game.json --out DIR [--tokens design-tokens.css] [--runs RUN_DIR ...]
    python3 booklets.py --selftest

Writes DIR/index.html (cover and cast), DIR/<id>.html (one booklet per player: their pages act by act, the clues
they hold, their goals), DIR/clues.html (search cards and host announcements, by round) and DIR/host.html (truth,
trick, flow, clue table, solution chain, red herrings, hints, reveal, vote, check results, and the verdict of every
detective run passed with --runs). Every page is one file with its styles inline and no outside requests, so the set
works offline at a table. Labels are Chinese unless meta.lang is "en". A booklet holds only what its player may see;
the culprit's booklet is the only one with the truth in it. Standard library only, Python 3.9+.
"""
import html, json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chain_check  # noqa: E402

L = {
    "zh": {"act": "第{n}幕", "table": "可以对大家说", "private": "只有你知道", "clues": "你手里的线索", "goals": "你的任务",
           "find": "查明", "hide": "隐瞒", "bond": "关系", "wait": "等主持人说开始，再读这一幕。", "booklet": "人物本",
           "only_yours": "每位玩家只打开自己的人物本。", "host_only": "主持人手册 · 请勿给玩家看", "cards": "线索卡",
           "search": "搜证", "host": "主持人公布", "round": "第{n}轮", "place": "地点", "cast": "角色", "players": "人数",
           "duration": "时长", "difficulty": "难度", "warnings": "内容提示", "truth": "真相", "trick": "诡计",
           "flow": "流程", "table_clues": "线索分布", "chain": "推理链", "herrings": "误导线", "hints": "提示（由浅到深）",
           "reveal": "复盘稿", "vote": "投票", "endings": "结局", "checks": "结构检查", "runs": "盲侦探", "holder": "持有人",
           "used": "用于", "resolved": "化解", "points": "指向", "false_belief": "假象", "how": "做法", "why": "为什么",
           "trace": "痕迹", "family": "类别", "answer": "答案", "none": "无", "who": "谁", "open": "打开",
           "not_player": "（非玩家）", "culprit": "凶手"},
    "en": {"act": "Act {n}", "table": "You may tell the table", "private": "Only you know", "clues": "Clues you hold",
           "goals": "Your goals", "find": "find", "hide": "hide", "bond": "bond", "wait": "Read this act when the host says so.",
           "booklet": "Booklet", "only_yours": "Each player opens only their own booklet.", "host_only": "Host handbook · players keep out",
           "cards": "Clue cards", "search": "Search", "host": "Host announces", "round": "Round {n}", "place": "Place", "cast": "Cast",
           "players": "Players", "duration": "Length", "difficulty": "Difficulty", "warnings": "Content notes", "truth": "Truth",
           "trick": "Trick", "flow": "Flow", "table_clues": "Where every clue is", "chain": "Solution chain", "herrings": "Red herrings",
           "hints": "Hints (mild to strong)", "reveal": "Reveal", "vote": "Vote", "endings": "Endings", "checks": "Structure checks",
           "runs": "Blind detective", "holder": "Holder", "used": "Used by", "resolved": "Resolved by", "points": "Points at",
           "false_belief": "False belief", "how": "How", "why": "Why", "trace": "Trace", "family": "Family", "answer": "Answer",
           "none": "none", "who": "Who", "open": "Open", "not_player": "(not a player)", "culprit": "culprit"},
}

FAMILY_ZH = {"T1": "时间错位", "T2": "地点错位", "T3": "在场伪造", "T4": "身份错置", "T5": "真凶另手", "T6": "出入之谜",
             "T7": "伪造指向", "T8": "案件错位"}   # the Chinese labels in references/trick-taxonomy.md

CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:var(--text-md)/var(--leading-relaxed) var(--font-sans)}
main{max-width:760px;margin:0 auto;padding:var(--space-8) var(--gutter,20px) var(--space-12)}
h1,h2,h3{font-family:var(--font-display);line-height:var(--leading-tight);margin:0}
h1{font-size:var(--text-3xl)} h2{font-size:var(--text-xl);margin:var(--space-8) 0 var(--space-3)} h3{font-size:var(--text-md);margin:var(--space-4) 0 var(--space-2)}
p{margin:var(--space-2) 0} a{color:var(--link,var(--accent))}
.kicker{font:600 var(--text-xs)/1.4 var(--font-mono);letter-spacing:.04em;color:var(--text-2);text-transform:uppercase}
.lede{font-size:var(--text-lg);color:var(--text-2);margin:var(--space-3) 0}
.meta{display:flex;flex-wrap:wrap;gap:var(--space-2);margin:var(--space-4) 0;padding:0;list-style:none}
.meta li{border:1px solid var(--border);border-radius:999px;padding:2px 12px;font-size:var(--text-sm);background:var(--surface)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:var(--space-4);margin:var(--space-3) 0}
.card.private{border-left:3px solid var(--point)} .card.table{border-left:3px solid var(--brand-sage,var(--accent))}
.tag{display:inline-block;font:600 var(--text-2xs)/1 var(--font-mono);padding:3px 8px;border-radius:999px;background:var(--accent-tint);color:var(--accent-tint-text);margin-right:6px;vertical-align:1px}
.tag.table{background:var(--sage-tint,var(--accent-tint));color:var(--sage-tint-text,var(--accent-tint-text))}
.tag.private{background:var(--point-tint,var(--neutral-tint));color:var(--point-text,var(--text))}
.id{font:600 var(--text-xs)/1 var(--font-mono);color:var(--text-2)}
.text{white-space:pre-wrap}
.wait{color:var(--text-3);font-style:italic}
.act{margin-top:var(--space-8)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:var(--space-3)}
.cards .card{margin:0}
table{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--border);font-size:var(--text-sm)}
th,td{border-top:1px solid var(--border);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--surface-2);color:var(--text-2);font-size:var(--text-xs)}
.cast li{margin:var(--space-2) 0} .ok{color:var(--success)} .bad{color:var(--danger)} .warn{color:var(--warning)}
.banner{background:var(--danger-tint,var(--surface-2));color:var(--danger-tint-text,var(--text));border-radius:var(--radius-md);padding:var(--space-3) var(--space-4);font-weight:600}
@media print{body{background:#fff;color:#111} main{max-width:none;padding:0} .act{break-before:page} .cards .card{break-inside:avoid} a{color:inherit;text-decoration:none}}
@page{size:A4;margin:16mm}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def page(title, body, tokens, lang):
    return (f'<!doctype html>\n<html lang="{"en" if lang == "en" else "zh-CN"}" data-theme="paper"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
            f"<style>{tokens}\n{CSS}</style></head><body><main>{body}</main></body></html>\n")


def lang_of(g):
    return "en" if (g.get("meta") or {}).get("lang") == "en" else "zh"


def booklet(G, c, t):
    cid = c.get("id")
    out = [f'<p class="kicker">{esc(G.meta.get("title"))} · {t["booklet"]}</p>', f"<h1>{esc(c.get('name'))}</h1>",
           f'<p class="lede">{esc(c.get("intro"))}</p>']
    acts = sorted({s.get("act", 1) for s in c.get("sections") or []} |
                  {(cl.get("source") or {}).get("act", 1) for cl in G.clues
                   if (cl.get("source") or {}).get("kind") == "booklet" and (cl.get("source") or {}).get("holder") == cid})
    for n in acts:
        out.append(f'<section class="act"><h2>{t["act"].format(n=n)}</h2>')
        if n > 1:
            out.append(f'<p class="wait">{t["wait"]}</p>')
        for s in [s for s in c.get("sections") or [] if s.get("act", 1) == n]:
            share = "private" if s.get("share") == "private" else "table"
            out.append(f'<div class="card {share}"><span class="tag {share}">{t[share]}</span><h3 style="display:inline">{esc(s.get("title"))}</h3>'
                       f'<p class="text">{esc(s.get("text"))}</p></div>')
        held = [cl for cl in G.clues if (cl.get("source") or {}).get("kind") == "booklet"
                and (cl.get("source") or {}).get("holder") == cid and (cl.get("source") or {}).get("act", 1) == n]
        if held:
            out.append(f"<h3>{t['clues']}</h3>")
            out += [f'<div class="card"><span class="id">{esc(cl.get("id"))}</span> <b>{esc(cl.get("title"))}</b>'
                    f'<p class="text">{esc(cl.get("text"))}</p></div>' for cl in held]
        if n == acts[0] and c.get("goals"):
            out.append(f"<h3>{t['goals']}</h3><ul>")
            out += [f'<li><span class="tag">{esc(t.get(gl.get("kind"), gl.get("kind")))}</span>{esc(gl.get("text"))}</li>' for gl in c.get("goals")]
            out.append("</ul>")
        out.append("</section>")
    return "".join(out)


def where(G, cl, t):
    src = cl.get("source") or {}
    k = src.get("kind")
    if k == "booklet":
        return f'{t["holder"]}: {esc(G.name(src.get("holder")))}'
    if k == "search":
        pl = next((p.get("name") for p in G.places if p.get("id") == src.get("place")), src.get("place"))
        return f'{t["search"]} · {t["round"].format(n=src.get("round"))} · {esc(pl)}'
    if k == "host":
        return f'{t["host"]} · {t["round"].format(n=src.get("round"))}'
    return t["none"]


def clue_cards(G, t):
    out = [f'<p class="kicker">{esc(G.meta.get("title"))}</p><h1>{t["cards"]}</h1>']
    for r in G.rounds:
        n = r.get("n")
        items = [cl for cl in G.clues if (cl.get("source") or {}).get("kind") in ("search", "host") and (cl.get("source") or {}).get("round") == n]
        if not items:
            continue
        out.append(f'<section class="act"><h2>{t["round"].format(n=n)} · {esc(r.get("title"))}</h2><div class="cards">')
        out += [f'<div class="card"><span class="id">{esc(cl.get("id"))}</span> <b>{esc(cl.get("title"))}</b>'
                f'<p class="kicker">{where(G, cl, t)}</p><p class="text">{esc(cl.get("text"))}</p></div>' for cl in items]
        out.append("</div></section>")
    return "".join(out)


def host_page(G, g, t, findings, runs):
    sol, tr, host = G.sol, g.get("trick") or {}, g.get("host") or {}
    cited = {}
    for s in G.steps:
        for c in s.get("clues") or []:
            cited.setdefault(c, []).append(s.get("id"))
    for h in G.herrings:
        for c in (h.get("clues") or []) + (h.get("resolved_by") or []):
            cited.setdefault(c, []).append(h.get("id"))
    out = [f'<p class="banner">{t["host_only"]}</p><p class="kicker">{esc(G.meta.get("title"))}</p><h1>{t["host_only"].split(" · ")[0]}</h1>',
           f'<h2>{t["truth"]}</h2><p><b>{t["culprit"]}: {esc(G.name(G.culprit))}</b></p><p class="text">{esc(sol.get("summary"))}</p>',
           f'<h2>{t["trick"]}</h2><table><tr><th>{t["family"]}</th><td>{esc(tr.get("family"))} {esc((FAMILY_ZH if t is L["zh"] else chain_check.TAXONOMY).get(tr.get("family"), ""))} · {esc(tr.get("mechanism"))}</td></tr>']
    for k in ("false_belief", "how", "why", "trace"):
        out.append(f"<tr><th>{t[k]}</th><td>{esc(tr.get(k))}</td></tr>")
    out.append("</table>")
    if host.get("flow"):
        out.append(f'<h2>{t["flow"]}</h2>')
        out += [f'<h3>{t["round"].format(n=f.get("round"))}</h3><p class="text">{esc(f.get("text"))}</p>' for f in host["flow"]]
    out.append(f'<h2>{t["table_clues"]}</h2><table><tr><th>ID</th><th></th><th>{t["place"]}</th><th>{t["used"]}</th></tr>')
    out += [f'<tr><td class="id">{esc(cl.get("id"))}</td><td>{esc(cl.get("title"))}</td><td>{where(G, cl, t)}</td>'
            f'<td>{esc(", ".join(cited.get(cl.get("id"), [])))}</td></tr>' for cl in G.clues]
    out.append(f'</table><h2>{t["chain"]}</h2><table><tr><th>ID</th><th></th><th>{t["who"]}</th><th>{t["used"]}</th></tr>')
    for s in G.steps:
        out.append(f'<tr><td class="id">{esc(s.get("id"))}<br>{esc(s.get("kind"))}</td><td>{esc(s.get("claim"))}</td>'
                   f'<td>{esc(G.name(s.get("target")) if s.get("target") else "")}</td><td class="id">{esc(", ".join(s.get("clues") or []))}'
                   f'{("<br>← " + esc(", ".join(s.get("after")))) if s.get("after") else ""}</td></tr>')
    out.append("</table>")
    if G.herrings:
        out.append(f'<h2>{t["herrings"]}</h2><table><tr><th>ID</th><th>{t["points"]}</th><th></th><th>{t["resolved"]}</th></tr>')
        out += [f'<tr><td class="id">{esc(h.get("id"))}</td><td>{esc(G.name(h.get("points_to")))}</td><td>{esc(h.get("note"))} '
                f'<span class="id">{esc(", ".join(h.get("clues") or []))}</span></td><td class="id">{esc(", ".join(h.get("resolved_by") or []))}</td></tr>'
                for h in G.herrings]
        out.append("</table>")
    if host.get("hints"):
        out.append(f'<h2>{t["hints"]}</h2><ol>' + "".join(f'<li>{esc(h.get("text"))} <span class="id">{esc(h.get("step"))}</span></li>' for h in host["hints"]) + "</ol>")
    if host.get("reveal"):
        out.append(f'<h2>{t["reveal"]}</h2><p class="text">{esc(host["reveal"])}</p>')
    if host.get("vote"):
        out.append(f'<h2>{t["vote"]}</h2><ol>' + "".join(f'<li>{esc(v.get("q"))}<br><span class="kicker">{t["answer"]}</span> {esc(v.get("answer"))}</li>' for v in host["vote"]) + "</ol>")
    if host.get("endings"):
        out.append(f'<h2>{t["endings"]}</h2>' + "".join(f'<div class="card"><b>{esc(e.get("when"))}</b><p class="text">{esc(e.get("text"))}</p></div>' for e in host["endings"]))
    errs = [f for f in findings if not f[0].startswith("W")]
    out.append(f'<h2>{t["checks"]}</h2><p class="{"bad" if errs else "ok"}">chain_check: {len(errs)} errors, {len(findings) - len(errs)} warnings</p>')
    if findings:
        out.append("<ul>" + "".join(f'<li class="{"warn" if c.startswith("W") else "bad"}">{esc(c)} {esc(m)}</li>' for c, m in findings) + "</ul>")
    if runs:
        out.append(f'<h2>{t["runs"]}</h2><ul>' + "".join(f"<li><b>{esc(name)}</b>: {esc(v)}</li>" for name, v in runs) + "</ul>")
    return "".join(out)


def cover(G, t):
    m = G.meta
    out = [f'<p class="kicker">nk-jubensha</p><h1>{esc(m.get("title"))}</h1><p class="lede">{esc(m.get("premise"))}</p>',
           f'<p>{esc(m.get("setting"))}</p><ul class="meta">']
    for k in ("players", "duration", "difficulty"):
        if m.get(k):
            out.append(f"<li>{t[k]}: {esc(m.get(k))}</li>")
    out.append("</ul>")
    if m.get("warnings"):
        out.append(f'<p><b>{t["warnings"]}:</b> {esc("；".join(m["warnings"]) if lang_of(G.g) == "zh" else "; ".join(m["warnings"]))}</p>')
    out.append(f'<h2>{t["cast"]}</h2><p>{t["only_yours"]}</p><ul class="cast">')
    out += [f'<li><a href="{esc(safe_name(c.get("id")))}.html"><b>{esc(c.get("name"))}</b></a> · {esc(c.get("intro"))}</li>' for c in G.chars if c.get("id") in G.players]
    out.append(f'</ul><h2>{t["cards"]}</h2><p><a href="clues.html">{t["open"]} clues.html</a></p>'
               f'<h2>{t["host_only"]}</h2><p><a href="host.html">{t["open"]} host.html</a></p>')
    return "".join(out)


def read_runs(dirs):
    """(name, verdict line) from each detective run folder's grade.txt (first line)"""
    runs = []
    for d in dirs:
        p = os.path.join(d, "grade.txt")
        if os.path.isfile(p):
            first = open(p, encoding="utf-8").read().strip().splitlines()
            runs.append((os.path.basename(os.path.normpath(d)), first[0] if first else ""))
    return runs


def safe_name(cid):
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(cid))


def render(g, out_dir, tokens, runs=()):
    G, lang = chain_check.Game(g), lang_of(g)
    t = L[lang]
    os.makedirs(out_dir, exist_ok=True)
    written = []

    def write(name, title, body):
        p = os.path.join(out_dir, name)
        open(p, "w", encoding="utf-8").write(page(title, body, tokens, lang))
        written.append(name)

    write("index.html", G.meta.get("title", "game"), cover(G, t))
    for c in G.chars:
        if c.get("id") in G.players:
            write(f"{safe_name(c.get('id'))}.html", f"{G.meta.get('title', '')} · {c.get('name')}", booklet(G, c, t))
    write("clues.html", f"{G.meta.get('title', '')} · {t['cards']}", clue_cards(G, t))
    write("host.html", f"{G.meta.get('title', '')} · {t['host_only']}", host_page(G, g, t, chain_check.check(g), list(runs)))
    return written


# ── self-test ──
def selftest():
    ok, lines = True, []

    def chk(cond, label):
        nonlocal ok
        ok &= bool(cond)
        lines.append(f"  {'✔' if cond else '✘'} {label}")

    g = chain_check._fixture()
    with tempfile.TemporaryDirectory() as d:
        files = render(g, d, ":root{--selftest-token:1}", runs=[("run-1", "SOLVED in 4 steps")])
        chk(sorted(files) == sorted(["index.html", "A.html", "B.html", "C.html", "clues.html", "host.html"]), "B01 one booklet per player plus cover, cards and host")
        read = {f: open(os.path.join(d, f), encoding="utf-8").read() for f in files}
        chk(all("--selftest-token:1" in v and "<!doctype html>" in v for v in read.values()), "B02 every page is a full document with the tokens inline")
        chk("Ash moved the clock" in read["A.html"], "B03 the culprit's booklet carries the truth")
        chk(not any("Ash moved the clock" in read[f] for f in ("B.html", "C.html", "clues.html", "index.html")), "B04 the truth is in no other player page")
        chk("I took money from the desk." in read["B.html"] and "I took money from the desk." not in read["C.html"], "B05 a secret appears only in its own booklet")
        chk("Vale was alive at twenty to ten." in read["B.html"] and "Vale was alive at twenty to ten." not in read["clues.html"], "B06 a booklet clue sits in its holder's booklet, not on the cards")
        chk("The study clock&#x27;s hands were set back twenty minutes." in read["clues.html"], "B07 search cards are on the cards page")
        chk("The nephew killed his uncle" in read["host.html"] and "SOLVED in 4 steps" in read["host.html"], "B08 the host page has the truth and the detective verdict")
        chk(not re.search(r"(?:src|href)\s*=\s*[\"']?https?://", "".join(read.values())), "B09 no page asks for anything from outside")
        chk(all(read[f].count("<script") == 0 for f in files), "B10 no scripts: the pages work printed and offline")
        g2 = chain_check._fixture()
        g2["characters"][1]["sections"][0]["text"] = "<script>alert(1)</script>"
        files2 = render(g2, os.path.join(d, "x"), "")
        chk("<script>alert" not in open(os.path.join(d, "x", "B.html"), encoding="utf-8").read(), "B11 text from the game is escaped")
        g3 = chain_check._fixture()
        g3["meta"]["lang"] = "en"
        render(g3, os.path.join(d, "en"), "")
        chk("Your goals" in open(os.path.join(d, "en", "A.html"), encoding="utf-8").read(), "B12 meta.lang en switches the labels")
        chk("你的任务" in read["A.html"], "B13 labels default to Chinese")
        chk("时间错位" in read["host.html"] and "time moved" in open(os.path.join(d, "en", "host.html"), encoding="utf-8").read(),
            "B14 the trick family is named in the game's language")
        g4 = chain_check._fixture()
        for c in g4["characters"]:
            if c["id"] == "B":
                c["id"] = "B/2"
        for cl in g4["clues"]:
            if (cl.get("source") or {}).get("holder") == "B":
                cl["source"]["holder"] = "B/2"
        g4["solution"]["herrings"][0]["points_to"] = "B/2"
        files4 = render(g4, os.path.join(d, "ids"), "")
        links = re.findall(r'href="([^"]+)\.html"', open(os.path.join(d, "ids", "index.html"), encoding="utf-8").read())
        chk(all(f"{x}.html" in files4 for x in links if x not in ("clues", "host")) and "B_2.html" in files4,
            "B15 every booklet link on the cover points at a file that was written")
    return ok, lines


def main(argv):
    ok, lines = selftest()
    if not ok or "--selftest" in argv:
        print(f"booklets selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed")
        print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — nothing rendered")
            return 2
        return 0
    if "--out" not in argv:
        print(__doc__)
        return 2
    out = argv[argv.index("--out") + 1]
    tok_path = argv[argv.index("--tokens") + 1] if "--tokens" in argv else os.path.join(HERE, "..", "assets", "design-tokens.css")
    runs = []
    if "--runs" in argv:
        i = argv.index("--runs") + 1
        while i < len(argv) and not argv[i].startswith("--"):
            runs.append(argv[i]); i += 1
    flagged = {out, tok_path, *runs}
    files = [a for a in argv if not a.startswith("--") and a not in flagged]
    if not files:
        print(__doc__)
        return 2
    g, err = chain_check.load(files[0])
    if err:
        print(err)
        return 2
    try:
        tokens = open(tok_path, encoding="utf-8").read()
    except OSError:
        print(f"token file not found: {tok_path} (pass --tokens)")
        return 2
    written = render(g, out, tokens, read_runs(runs))
    print(f"wrote {len(written)} pages to {out}: " + ", ".join(written))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

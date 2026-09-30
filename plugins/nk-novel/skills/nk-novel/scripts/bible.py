#!/usr/bin/env python3
"""bible.py — render story.json into a single-file "story bible" page: retelling, world rules and what the world does
not allow, cast (desire / fear / secret), relationship map, event spine (what happened → so what changed), structure,
clues planted → paid off, open questions, chapter outline, and the consistency check results.

    python3 bible.py story.json --out bible.html [--tokens design-tokens.css] [--max-open 5]
    python3 bible.py --selftest

The page is one file with its styles inline (tokens from --tokens, default: ../assets/design-tokens.css next to this
script). Web fonts load from Google Fonts when online; the page stays readable offline. Standard library only.
"""
import html, json, math, os, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from story_check import check, sample  # noqa: E402

esc = lambda s: html.escape(str(s if s is not None else ""))


def _label(name):
    words = str(name or "").split()
    lines = [words[0], " ".join(words[1:])] if len(words) > 1 else words[:1]
    lines = [l if len(l) <= 16 else l[:15] + "…" for l in lines if l]
    longest = max((len(l) for l in lines), default=0)
    return lines, (12 if longest <= 9 else 10 if longest <= 13 else 9)


def _short(kind, cap=18):
    """Edge labels stay short so crossing edges do not stack sentences on top of each other; the full text is in
    the hover title and in the relations list under the map."""
    kind = str(kind or "").strip()
    if len(kind) <= cap:
        return kind
    cut = kind[:cap - 1]
    if kind[cap - 1] != " " and " " in cut[5:]:           # the cut fell inside a word: drop that partial word
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:-") + "…"


def relations_list(chars):
    names = {c.get("id"): c.get("name") for c in chars}
    items = [f'<li><b>{esc(c.get("name"))}</b> → <b>{esc(names.get(r.get("to"), r.get("to")))}</b>: {esc(r.get("kind"))}</li>'
             for c in chars for r in c.get("relations", [])]
    return f'<ul class="relations">{"".join(items)}</ul>' if items else ""


def relation_map(chars):
    n = len(chars)
    if not n:
        return ""
    W, H, R = 640, 480, 160                           # H leaves room for the role label under the bottom node
    names = {c["id"]: c.get("name", "") for c in chars}
    cx, cy = W / 2, H / 2
    pos = {c["id"]: (cx + R * math.cos(2 * math.pi * i / n - math.pi / 2), cy + R * math.sin(2 * math.pi * i / n - math.pi / 2)) for i, c in enumerate(chars)}
    seen, edges = set(), []
    for c in chars:
        for r in c.get("relations", []):
            key = tuple(sorted((c["id"], r.get("to", ""))))
            if r.get("to") in pos and key not in seen:
                seen.add(key)
                (x1, y1), (x2, y2) = pos[c["id"]], pos[r["to"]]
                frac = 0.5 if n <= 3 else (0.36 if len(seen) % 2 else 0.64)   # edges crossing at the centre get labels apart
                lx, ly = x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac
                edges.append(f'<g><title>{esc(names[c["id"]])} → {esc(names[r["to"]])}: {esc(r.get("kind", ""))}</title>'
                             f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" class="edge"/>'
                             f'<text x="{lx:.0f}" y="{ly - 6:.0f}" class="edge-label">{esc(_short(r.get("kind", "")))}</text></g>')
    nodes = []
    for c in chars:
        x, y = pos[c["id"]]
        cls = "node main" if c.get("role") in ("protagonist", "antagonist", "main") else "node"
        lines, fs = _label(c.get("name", ""))
        first = y + 4 if len(lines) < 2 else y - 2
        tsp = "".join(f'<tspan x="{x:.0f}" y="{first + i * (fs + 2):.0f}">{esc(l)}</tspan>' for i, l in enumerate(lines))
        nodes.append(f'<g class="{cls}"><circle cx="{x:.0f}" cy="{y:.0f}" r="42"/>'
                     f'<text class="node-name" style="font-size:{fs}px">{tsp}</text>'
                     f'<text x="{x:.0f}" y="{y + 60:.0f}" class="node-role">{esc(c.get("role", ""))}</text></g>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Relationship map" class="relmap">'
            + "".join(edges) + "".join(nodes) + "</svg>")


def render(story, tokens_css="", max_open=5):
    errs, warns = check(story, max_open)
    world = story.get("world", {})
    chars = story.get("characters", [])
    ch_name = {c.get("id"): c.get("name") for c in chars}
    ev_title = {e.get("id"): e.get("title") for e in story.get("spine", [])}
    place = {p.get("id"): p.get("name") for p in world.get("places", [])}
    rules = "".join(f'<tr><td><span class="chip">{esc(r.get("id"))}</span></td><td>{esc(r.get("rule"))}</td><td>{esc(r.get("cost"))}</td></tr>' for r in world.get("rules", []))
    notallowed = "".join(f"<li>{esc(x)}</li>" for x in world.get("not_allowed", []))
    cast = "".join(
        f'<article class="card"><h3>{esc(c.get("name"))} <span class="tag">{esc(c.get("role", ""))}</span></h3>'
        f'<dl><dt>Wants</dt><dd>{esc(c.get("desire"))}</dd><dt>Fears</dt><dd>{esc(c.get("fear"))}</dd>'
        f'<dt>Hides</dt><dd>{esc(c.get("secret")) or "—"}</dd></dl></article>' for c in chars)
    spine = "".join(
        f'<li><div class="t mono">t{esc(e.get("t"))}</div><div class="ev"><h3>{esc(e.get("title"))}</h3>'
        f'<p class="what">{esc(e.get("what_happened"))}</p><p class="so">→ {esc(e.get("so_what_changed"))}</p>'
        f'<p class="meta mono">{esc(", ".join(ch_name.get(p, p) for p in e.get("participants", [])))}'
        f'{" · " + esc(place.get(e.get("place"), e.get("place"))) if e.get("place") else ""}'
        f'{" · caused by " + esc(", ".join(ev_title.get(c, c) for c in e.get("causes", []))) if e.get("causes") else ""}</p></div></li>'
        for e in sorted(story.get("spine", []), key=lambda e: (e.get("t") is None, e.get("t"))))
    acts = "".join(
        f'<div class="act"><h3>Act {esc(a.get("name"))}</h3><ul>' + "".join(
            f'<li><b>{esc(b.get("name"))}</b> — {esc(", ".join(ev_title.get(x, x) for x in b.get("events", [])))}</li>' for b in a.get("beats", [])) + "</ul></div>"
        for a in story.get("structure", {}).get("acts", []))
    clues = "".join(
        f'<tr class="{"open" if f.get("paid_off_in") is None else ""}"><td><span class="chip">{esc(f.get("id"))}</span></td><td>{esc(f.get("clue"))}</td>'
        f'<td class="mono">ch {esc(f.get("planted_in"))}</td><td class="mono">{("ch " + esc(f.get("paid_off_in"))) if f.get("paid_off_in") is not None else ("left open" if f.get("left_open_on_purpose") else "never")}</td></tr>'
        for f in story.get("foreshadowing", []))
    qs = "".join(
        f'<tr><td><span class="chip">{esc(q.get("id"))}</span></td><td>{esc(q.get("question"))}</td><td class="mono">ch {esc(q.get("opened_in"))}</td>'
        f'<td class="mono">{("ch " + esc(q.get("answered_in"))) if q.get("answered_in") is not None else "open"}</td></tr>' for q in story.get("questions", []))
    chapters = "".join(
        f'<li><span class="mono">{esc(c.get("n"))}</span> <b>{esc(c.get("title"))}</b>'
        f'{" · " + esc(ch_name.get(c.get("pov"), c.get("pov"))) if c.get("pov") else ""}'
        f' — {esc(", ".join(ev_title.get(x, x) for x in c.get("events", [])))}{(": " + esc(c.get("summary"))) if c.get("summary") else ""}</li>'
        for c in story.get("chapters", []))
    findings = "".join(f'<li class="err"><span class="mono">{esc(c)}</span> {esc(m)}</li>' for c, m in errs) + \
               "".join(f'<li class="warn"><span class="mono">{esc(c)}</span> {esc(m)}</li>' for c, m in warns)
    verdict = (f'<p class="verdict ok">0 errors, {len(warns)} warning(s)</p>' if not errs else f'<p class="verdict bad">{len(errs)} error(s), {len(warns)} warning(s)</p>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(story.get("title", "Story bible"))} — story bible</title>
<meta name="description" content="{esc(story.get("retelling", ""))}">
<meta name="theme-color" content="#faece9">
<script>
/* appearance contract (nl-theme / nl-scheme): Plaster and System are defaults and write no attribute */
(function () {{
  var d = document.documentElement, q = new URLSearchParams(location.search), t, s;
  try {{ t = q.get('theme') || localStorage.getItem('nl-theme'); s = q.get('scheme') || localStorage.getItem('nl-scheme'); }}
  catch (e) {{ t = q.get('theme'); s = q.get('scheme'); }}
  if (t === 'paper' || t === 'ink') d.setAttribute('data-theme', t);
  if (s === 'dark' || s === 'light') d.setAttribute('data-scheme', s);
}})();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;600&family=Space+Mono:wght@400;700&display=swap">
<style>{tokens_css}</style>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font:var(--text-md)/var(--leading-relaxed) var(--font-sans)}}
body::before{{content:"";position:fixed;inset:0;background-image:var(--grain);opacity:var(--grain-opacity);pointer-events:none;z-index:0}}
.topbar{{position:relative;z-index:2;background:var(--anchor);color:var(--on-anchor);display:flex;align-items:center;justify-content:space-between;gap:var(--space-3);padding:var(--space-2) var(--gutter)}}
.topbar .mark{{font:600 var(--text-sm)/1 var(--font-mono);letter-spacing:.02em}} .topbar .mark b,.topbar .mark svg{{color:var(--point)}} .topbar .mark svg{{vertical-align:-1px}}
.appearance{{position:relative}} .appearance summary{{cursor:pointer;list-style:none;font:500 var(--text-xs)/1 var(--font-mono);padding:8px 12px;border:1px solid var(--anchor-line);border-radius:999px;color:var(--on-anchor)}}
.appearance summary::-webkit-details-marker{{display:none}}
.appearance-panel{{position:absolute;right:0;top:calc(100% + 8px);background:var(--surface-raised);color:var(--text);border:1px solid var(--border);border-radius:var(--radius-md);box-shadow:var(--shadow-2);padding:var(--space-3);display:grid;gap:var(--space-3);min-width:min(300px,calc(100vw - 32px));z-index:3}}
.appearance fieldset{{border:0;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:var(--space-2)}} .appearance legend{{font-size:var(--text-2xs);color:var(--text-2);margin-bottom:6px;width:100%}}
.appearance p{{margin:0;font-size:var(--text-2xs);color:var(--text-3)}}
.pick,.seg{{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);cursor:pointer;font-size:var(--text-xs)}}
.pick:has(input:checked),.seg:has(input:checked){{border-color:var(--accent-text);background:var(--accent-tint)}}
.pick input,.seg input{{position:absolute;opacity:0;width:1px;height:1px}} .pick:has(input:focus-visible),.seg:has(input:focus-visible){{outline:2px solid var(--focus);outline-offset:2px}}
.swatch{{display:grid;grid-template-columns:repeat(3,1fr);width:36px;height:20px;border-radius:4px;overflow:hidden;border:1px solid var(--border)}}
.swatch i{{display:block}} .swatch i:nth-child(1){{background:var(--bg)}} .swatch i:nth-child(2){{background:var(--anchor)}} .swatch i:nth-child(3){{background:var(--point)}}
main{{position:relative;z-index:1;max-width:980px;margin:0 auto;padding:var(--space-8) var(--gutter)}}
h1,h2,h3{{font-family:var(--font-display);line-height:var(--leading-tight);margin:0}}
h1{{font-size:var(--text-3xl)}} h2{{font-size:var(--text-xl);margin:var(--space-8) 0 var(--space-3)}} h3{{font-size:var(--text-md)}}
.mono,.chip{{font-family:var(--font-mono);font-variant-numeric:tabular-nums}}
.idea{{color:var(--text-2);margin:var(--space-2) 0}} .retelling{{font-size:var(--text-lg);border-left:3px solid var(--accent);padding-left:var(--space-3);margin:var(--space-4) 0}}
table{{border-collapse:collapse;width:100%;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);overflow:hidden;font-size:var(--text-sm)}}
th,td{{text-align:left;padding:var(--space-2) var(--space-3);border-top:1px solid var(--border);vertical-align:top}}
th{{background:var(--surface-2);color:var(--text-2);font-size:var(--text-xs);border-top:0}}
tr.open td{{background:var(--warning-tint)}}
.chip{{display:inline-block;padding:0 6px;border:1px solid var(--border);border-radius:var(--radius-xs);background:var(--neutral-tint);font-size:var(--text-2xs)}}
.tag{{font:500 var(--text-2xs)/1 var(--font-mono);padding:3px 8px;border-radius:999px;background:var(--accent-tint);color:var(--accent-tint-text);vertical-align:middle}}
.cast{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:var(--space-3)}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:var(--space-3)}}
.card dl{{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px var(--space-3);margin:var(--space-2) 0 0;font-size:var(--text-sm)}}
.card dt{{color:var(--text-3)}} .card dd{{margin:0}}
.notallowed li{{margin:4px 0}}
.relmap{{width:100%;max-width:640px;height:auto;display:block;margin:0 auto;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md)}}
.relmap .edge{{stroke:var(--border-strong);stroke-width:1.5}} .relmap .edge-label{{font:11px var(--font-mono);fill:var(--text-2);text-anchor:middle;paint-order:stroke;stroke:var(--surface);stroke-width:5px;stroke-linejoin:round}}
.relations{{columns:2 260px;column-gap:var(--space-6);font-size:var(--text-sm);color:var(--text-2);padding-left:1.1em;margin:var(--space-3) 0 0}} .relations li{{break-inside:avoid;margin:2px 0}} .relations b{{color:var(--text);font-weight:600}}
.relmap circle{{fill:var(--surface-2);stroke:var(--border-strong);stroke-width:1.5}} .relmap .main circle{{fill:var(--accent-tint);stroke:var(--accent)}}
.relmap .node-name{{font:600 12px var(--font-sans);fill:var(--text);text-anchor:middle}} .relmap .node-role{{font:10px var(--font-mono);fill:var(--text-3);text-anchor:middle}}
.spine{{list-style:none;margin:0;padding:0;border-left:2px solid var(--border-strong);margin-left:var(--space-4)}}
.spine li{{display:grid;grid-template-columns:44px minmax(0,1fr);gap:var(--space-3);padding:var(--space-2) 0 var(--space-4)}}
.spine .t{{justify-self:start;width:max-content;height:max-content;transform:translateX(calc(-50% - 1px));color:var(--point-text);font-size:var(--text-2xs);line-height:1.4;background:var(--bg);padding:1px 7px;border:1px solid var(--point);border-radius:999px}}
.spine .what{{margin:4px 0}} .spine .so{{margin:0;color:var(--success-tint-text);font-weight:600}} .spine .meta{{margin:4px 0 0;font-size:var(--text-xs);color:var(--text-3)}}
.acts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:var(--space-3)}}
.act{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:var(--space-3)}} .act ul{{margin:var(--space-2) 0 0;padding-left:1.1em;font-size:var(--text-sm)}}
.chapters{{font-size:var(--text-sm);padding-left:0;list-style:none}} .chapters li{{padding:6px 0;border-top:1px solid var(--border)}} .chapters .mono{{color:var(--text-3);display:inline-block;width:2.2em}}
.verdict{{font-family:var(--font-mono);font-weight:700}} .verdict.ok{{color:var(--success)}} .verdict.bad{{color:var(--danger)}}
.verdict::before{{content:"";display:inline-block;width:.8em;height:.8em;margin-right:.4em;vertical-align:-.04em;background:currentColor;-webkit-mask:var(--glyph) center/contain no-repeat;mask:var(--glyph) center/contain no-repeat}}
.verdict.ok{{--glyph:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10'%3E%3Cpath d='M1.6 5.3 4 7.6 8.4 2.4' fill='none' stroke='black' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")}} .verdict.bad{{--glyph:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10'%3E%3Cpath d='M2.4 2.4 7.6 7.6M7.6 2.4 2.4 7.6' fill='none' stroke='black' stroke-width='1.7' stroke-linecap='round'/%3E%3C/svg%3E")}}
.findings{{font-size:var(--text-sm);padding-left:0;list-style:none}} .findings li{{padding:4px 0}} .findings .err{{color:var(--danger)}} .findings .warn{{color:var(--warning)}}
footer{{position:relative;z-index:1;background:var(--anchor);color:var(--on-anchor-2);padding:var(--space-5) var(--gutter) var(--space-8);font-size:var(--text-xs)}} footer p{{max-width:980px;margin:0 auto}}
.scroll{{overflow-x:auto}}
@media (prefers-reduced-motion: reduce){{*{{transition-duration:1ms!important}}}}
</style></head><body><header class="topbar"><span class="mark"><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg> story bible</span><details class="appearance"><summary>Theme</summary><div class="appearance-panel"><fieldset><legend>Palette</legend><label class="pick"><input type="radio" name="nl-theme" value="plaster" checked><span class="swatch" aria-hidden="true"><i></i><i></i><i></i></span>Water lilies</label><label class="pick"><input type="radio" name="nl-theme" value="paper"><span class="swatch" data-theme="paper" aria-hidden="true"><i></i><i></i><i></i></span>Morning light</label><label class="pick"><input type="radio" name="nl-theme" value="ink"><span class="swatch" data-theme="ink" aria-hidden="true"><i></i><i></i><i></i></span>Dusk</label></fieldset><fieldset><legend>Appearance</legend><label class="seg"><input type="radio" name="nl-scheme" value="system" checked>System</label><label class="seg"><input type="radio" name="nl-scheme" value="light">Light</label><label class="seg"><input type="radio" name="nl-scheme" value="dark">Dark</label></fieldset><p>Saved on this device only.</p></div></details></header><main>
<h1>{esc(story.get("title", "Untitled"))}</h1>
<p class="idea">Idea: {esc(story.get("idea", ""))}</p>
<p class="retelling">{esc(story.get("retelling", ""))}</p>
<h2>The world</h2>
<div class="scroll"><table><thead><tr><th>Rule</th><th>What holds</th><th>What it costs</th></tr></thead><tbody>{rules}</tbody></table></div>
<h3 style="margin-top:var(--space-4)">What this world does not allow</h3><ul class="notallowed">{notallowed}</ul>
<h2>Cast</h2><div class="cast">{cast}</div>
<h2>Relationships</h2>{relation_map(chars)}{relations_list(chars)}
<h2>Event spine</h2><p style="color:var(--text-2);margin-top:0">What happened, and so what changed.</p><ol class="spine">{spine}</ol>
<h2>Structure</h2><div class="acts">{acts}</div>
<h2>Clues: planted → paid off</h2><div class="scroll"><table><thead><tr><th>Clue</th><th>What the reader sees</th><th>Planted</th><th>Paid off</th></tr></thead><tbody>{clues}</tbody></table></div>
<h2>Open questions</h2><div class="scroll"><table><thead><tr><th>Id</th><th>Question</th><th>Opened</th><th>Answered</th></tr></thead><tbody>{qs}</tbody></table></div>
<h2>Chapters</h2><ol class="chapters">{chapters}</ol>
<h2>Consistency checks</h2>{verdict}<ul class="findings">{findings}</ul>
</main><footer><p>Generated from story.json. Checks: references, timeline, name collisions, clues never paid off, missing motivation, reader load, caps, a story built around a single rule. The checks read structure; whether the story is worth reading is still a reader's call.</p></footer>
<script>
(function () {{
  var html = document.documentElement;
  function get() {{
    var t = html.getAttribute('data-theme'), s = html.getAttribute('data-scheme');
    return {{ theme: (t === 'paper' || t === 'ink') ? t : 'plaster', scheme: (s === 'light' || s === 'dark') ? s : 'system' }};
  }}
  function syncMeta() {{
    var bg = getComputedStyle(html).getPropertyValue('--bg').trim(), m = document.querySelector('meta[name="theme-color"]');
    if (bg && m) m.setAttribute('content', bg);
  }}
  function set(next) {{
    var cur = get(), t = next.theme || cur.theme, s = next.scheme || cur.scheme;
    if (t === 'plaster') html.removeAttribute('data-theme'); else html.setAttribute('data-theme', t);
    if (s === 'system') html.removeAttribute('data-scheme'); else html.setAttribute('data-scheme', s);
    try {{ localStorage.setItem('nl-theme', t); localStorage.setItem('nl-scheme', s); }} catch (e) {{}}
    syncMeta();
  }}
  ['nl-theme', 'nl-scheme'].forEach(function (group) {{
    document.querySelectorAll('input[name="' + group + '"]').forEach(function (el) {{
      var key = group === 'nl-theme' ? 'theme' : 'scheme';
      if (el.value === get()[key]) el.checked = true;
      /* click as well as change: after a ?theme= link the shown radio can already be checked, and choosing it must still save */
      ['change', 'click'].forEach(function (type) {{
        el.addEventListener(type, function () {{ if (el.checked) {{ var o = {{}}; o[key] = el.value; set(o); }} }});
      }});
    }});
  }});
  syncMeta();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', syncMeta);
}})();
</script>
</body></html>
"""


def _section(page, start, end):
    i = page.find(start)
    if i < 0:
        return ""
    j = page.find(end, i + len(start))
    return page[i:j if j >= 0 else len(page)]


def selftest():
    import copy, re, subprocess
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")
    s = sample()
    page = render(s, ":root{--selftest-token:1}")
    head = _section(page, "<head>", "</head>")
    chk("<title>The Next-Year Light — story bible</title>" in head and "--selftest-token:1" in head, "T01 head: title and inline tokens")
    rules = _section(page, "<h2>The world</h2>", "</table>")
    chk(all(esc(r["rule"]) in rules and esc(r["cost"]) in rules for r in s["world"]["rules"]), "T02 world table: every rule with its cost")
    na = _section(page, '<ul class="notallowed">', "</ul>")
    chk(all(esc(x) in na for x in s["world"]["not_allowed"]) and na.count("<li>") == len(s["world"]["not_allowed"]), "T03 what the world does not allow")
    cast = _section(page, '<div class="cast">', "<h2>Relationships</h2>")
    chk(all(esc(c["desire"]) in cast and esc(c["fear"]) in cast for c in s["characters"]) and cast.count("<article") == 3, "T04 cast: desire and fear for all 3 characters")
    chk("<dd>—</dd>" in cast and esc(s["characters"][0]["secret"]) in cast, "T05 cast: a secret shows, an empty secret shows as a dash")
    svg = _section(page, '<svg viewBox', "</svg>")   # the map, not the header mark (a line SVG since 0.1.2)
    chk(svg.count("<line ") == 2 and svg.count("<circle") == 3, f"T06 relationship map: 3 nodes, 2 edges after merging the two-way sibling link ({svg.count('<line ')})")
    long_kind = "useful apprentice whom he tried to protect from the Guild"
    lk = copy.deepcopy(s); lk["characters"][2]["relations"][0]["kind"] = long_kind
    lkp = render(lk)
    shown = re.findall(r'class="edge-label">([^<]*)<', _section(lkp, '<svg viewBox', "</svg>"))
    chk(any(x.endswith("…") and len(x) <= 18 for x in shown) and long_kind not in shown and esc(long_kind) in _section(lkp, '<ul class="relations">', "</ul>"),
        f"T21 a long relation is shortened on the map and given in full in the relations list ({shown})")
    rev = copy.deepcopy(s); rev["spine"].reverse()
    spine = _section(render(rev), '<ol class="spine">', "</ol>")
    idx = [spine.find(esc(e["title"])) for e in s["spine"]]
    chk(all(i >= 0 for i in idx) and idx == sorted(idx), f"T07 event spine sorted by t even when the input is reversed ({idx})")
    chk(all(esc(e["so_what_changed"]) in spine for e in s["spine"]) and "caused by The warning, The list" in spine, "T08 spine: 'so what changed' and causes by title")
    acts = _section(page, '<div class="acts">', "<h2>Clues")
    chk("Act III" in acts and "<b>Midpoint</b> — The list" in acts, "T09 structure: acts, beats and beat events by title")
    clues = _section(page, "<h2>Clues", "<h2>Open questions")
    chk(esc(s["foreshadowing"][0]["clue"]) in clues and "ch 4" in clues and 'class="open"' not in clues, "T10 clues table: clue, payoff chapter, no open row when paid off")
    qs = _section(page, "<h2>Open questions", "<h2>Chapters")
    chk(esc(s["questions"][0]["question"]) in qs and "ch 3" in qs, "T11 open questions table")
    chs = _section(page, '<ol class="chapters">', "</ol>")
    chk(chs.count("<li>") == 4 and "<b>Liar</b> · Maren" in chs and "<b>The list</b> · Tobias" in chs, "T12 chapter outline: 4 chapters with point of view")
    checks = _section(page, "<h2>Consistency checks</h2>", "</main>")
    chk('<p class="verdict ok">0 errors, 0 warning(s)</p>' in checks and "<li" not in checks, "T13 clean sample: verdict ok, no findings listed")
    bad = sample(); bad["foreshadowing"][0]["paid_off_in"] = None
    p3 = render(bad)
    chk('<p class="verdict bad">1 error(s)' in p3 and '<li class="err"><span class="mono">S04</span>' in _section(p3, "<h2>Consistency checks</h2>", "</main>"), "T14 an unpaid clue: verdict red and the S04 finding listed")
    chk('<tr class="open">' in _section(p3, "<h2>Clues", "<h2>Open questions") and ">never<" in p3, "T15 an unpaid clue: highlighted row marked never")
    evil = sample(); evil["characters"][0]["name"] = "<script>alert(1)</script>"
    p2 = render(evil)
    chk("<script>alert" not in p2 and "&lt;script&gt;alert" in p2, "T16 story text is HTML-escaped")
    # an XML namespace inside a line icon drawn in CSS (xmlns='http://www.w3.org/2000/svg') is never fetched
    hosts = set(re.findall(r"https?://([^/\"'\s)]+)", re.sub(r"""xmlns(?::\w+)?\s*=\s*['"]https?://www\.w3\.org/[^'"]*['"]""", " ", page)))
    chk(hosts <= {"fonts.googleapis.com", "fonts.gstatic.com"}, f"T17 only font hosts are referenced ({sorted(hosts)})")
    head_boot = head.split("<style>")[0]
    chk(page.startswith('<!doctype html>\n<html lang="en">') and "data-theme" not in page.split("<head>")[0] and "nl-theme" in head_boot and "nl-scheme" in head_boot
        and "d.setAttribute('data-theme', t)" in head_boot and "d.setAttribute('data-scheme', s)" in head_boot,
        "T19 appearance: the theme is applied by a head script before the styles; the default page writes no theme attribute")
    radios = re.findall(r'<input type="radio" name="(nl-theme|nl-scheme)" value="(\w+)"( checked)?>', page)
    # the palettes are labelled with the paintings' names; the values and data-theme stay plaster / paper / ink
    chk(all(f"</span>{n}</label>" in page for n in ("Water lilies", "Morning light", "Dusk")), "T23 the palettes are shown as Water lilies / Morning light / Dusk")
    # no emoji on a public page — icons are line SVG; arrows are punctuation and may stay
    pict = re.findall("[\u2295-\u22a1\u2300-\u23ff\u25a0-\u25ff\u2600-\u27bf\u2b00-\u2bff\U0001f000-\U0001faff\ufe0f]", page)
    chk(not pict, f"T24 the page carries no emoji or icon symbols ({''.join(pict)})")
    chk([(g, v) for g, v, _ in radios] == [("nl-theme", "plaster"), ("nl-theme", "paper"), ("nl-theme", "ink"), ("nl-scheme", "system"), ("nl-scheme", "light"), ("nl-scheme", "dark")]
        and [v for g, v, c in radios if c] == ["plaster", "system"], "T20 picker: Plaster/Paper/Ink and System/Light/Dark, defaults Plaster and System")
    chk("['change', 'click'].forEach" in page, "T22 a theme choice is saved on click as well as change (a radio already checked by ?theme= fires no change)")
    tmp = tempfile.mkdtemp(prefix="bible_selftest_")
    sp, out = os.path.join(tmp, "story.json"), os.path.join(tmp, "bible.html")
    json.dump(s, open(sp, "w", encoding="utf-8"))
    r = subprocess.run([sys.executable, os.path.abspath(__file__), sp, "--out", out], capture_output=True, text=True)
    chk(r.returncode == 0 and os.path.isfile(out) and "The Next-Year Light" in open(out, encoding="utf-8").read() and "0 error(s)" in r.stdout, f"T18 command line writes the page (exit {r.returncode})")
    return ok, lines


def main(argv):
    if "--selftest" in argv:
        ok, lines = selftest(); print(f"bible selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines)); return 0 if ok else 2
    pos = [a for a in argv if not a.startswith("--") and (argv.index(a) == 0 or argv[argv.index(a) - 1] not in ("--out", "--tokens", "--max-open"))]
    if not pos or "--out" not in argv:
        print(__doc__); return 2
    tok = argv[argv.index("--tokens") + 1] if "--tokens" in argv else os.path.join(HERE, "..", "assets", "design-tokens.css")
    css = open(tok, encoding="utf-8").read() if os.path.isfile(tok) else ""
    story = json.load(open(pos[0], encoding="utf-8"))
    out = argv[argv.index("--out") + 1]
    max_open = int(argv[argv.index("--max-open") + 1]) if "--max-open" in argv else 5
    open(out, "w", encoding="utf-8").write(render(story, css, max_open))
    errs, warns = check(story, max_open)
    print(f"{out}: story bible written · {len(errs)} error(s), {len(warns)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

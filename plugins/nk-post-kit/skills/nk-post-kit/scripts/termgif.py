#!/usr/bin/env python3
"""termgif.py — render a scripted terminal session to an animated GIF (and a PNG of the last frame) without any
screen recording. For hero GIFs and gallery thumbnails.

    python3 termgif.py <cast.txt> --out demo.gif [--png last.png] [--cols 96] [--rows 22] [--font-size 15] [--title "…"] [--speed 1.0]
    python3 termgif.py --from-run <gif-run.txt> --out demo.gif [...]     # lines starting with "$ " are typed, the rest printed
    options: --replace OLD=NEW (repeatable, applied to every line) · --max-block N (longer output blocks are cut with "…") ·
             --type-chunk N (characters typed per frame, default 3) · --scale 1|2 (render scale; 1 = smaller GIF)
    python3 termgif.py --selftest

Cast format (one line = one event): "$ <command>" is typed character by character; "#title: <text>" sets the window
title; "#pause: <seconds>" holds the frame; "#clear" clears the screen; any other line is printed as output.
Colouring is automatic: lines containing ✘ / FAIL / RED / "exit=1" / "exit=2" are red, ✔ / PASS / GREEN / "exit=0"
are green, "$ " prompts are white on the prompt glyph, comments starting with "#" are grey.
Requires Pillow (the only dependency outside Python's standard library) and a monospace TrueType font (Menlo / DejaVu Sans Mono / Consolas).
"""
import os, re, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

BG, FG, DIM, GREEN, RED, YELLOW, BAR = (15, 17, 21), (231, 234, 240), (115, 125, 141), (95, 201, 138), (255, 107, 107), (240, 190, 90), (29, 33, 42)
FONTS = ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "C:/Windows/Fonts/consola.ttf", "/Library/Fonts/JetBrainsMono-Regular.ttf"]


def load_font(size):
    for p in FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


CODE_RE = re.compile(r"^\s*(def |class |if |elif |else|return |print\(|import |from |ok = |for |while |try|except)")


# Monospace terminal fonts have no colour-emoji glyphs; draw a text stand-in (colour is decided on the original line)
EMOJI_TEXT = {"🚨": "!!", "🔴": "●", "🟢": "●", "🟡": "●", "⛔": "×", "⚠️": "!", "⚠": "!", "✅": "✔", "❌": "✘", "📌": "»", "🛡️": "#", "\ufe0f": ""}


def glyphsafe(line):
    for k, v in EMOJI_TEXT.items():
        line = line.replace(k, v)
    return line


def colour(line):
    if line.startswith("$ ") or CODE_RE.match(line):
        return FG
    if line.startswith("#"):
        return DIM
    if re.search(r"✘|FAIL|\bRED\b|exit=[12]\b|🔴|Traceback|CRASH|UNCOVERED|deny|⛔|🚨", line):
        return RED
    if re.search(r"✔|PASS|GREEN|exit=0\b|🟢|CAUGHT|passed", line):
        return GREEN
    if re.search(r"⚠|warn|ask", line, re.I):
        return YELLOW
    return FG


def parse_cast(text, from_run=False, replace=(), max_block=0):
    events, block = [], 0
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        for old, new in replace:
            line = line.replace(old, new)
        if line.startswith("$ ") or line.startswith("#"):
            block = 0
        else:
            block += 1
            if max_block and block > max_block:
                if block == max_block + 1:
                    events.append(("print", "  …"))
                continue
        if not from_run and line.startswith("#title:"):
            events.append(("title", line.split(":", 1)[1].strip()))
        elif not from_run and line.startswith("#pause:"):
            events.append(("pause", float(line.split(":", 1)[1].strip() or 1)))
        elif not from_run and line.strip() == "#clear":
            events.append(("clear", None))
        elif line.startswith("$ "):
            events.append(("type", line))
        else:
            events.append(("print", line))
    return events


class Screen:
    def __init__(self, cols, rows, font_size, title, scale=1):
        self.cols, self.rows, self.scale = cols, rows, scale
        self.font = load_font(font_size * scale)
        bbox = self.font.getbbox("M")
        self.cw, self.ch = (bbox[2] - bbox[0]) or font_size * scale * 0.6, int((bbox[3] - bbox[1]) * 1.55) or font_size * scale * 2
        self.pad, self.bar = 12 * scale, 28 * scale
        self.w = int(self.cols * self.cw + 2 * self.pad); self.h = int(self.bar + self.rows * self.ch + 2 * self.pad)
        self.lines, self.title = [], title

    def push(self, line, col):
        line = glyphsafe(line.expandtabs(4))
        for chunk in [line[i:i + self.cols] for i in range(0, max(1, len(line)), self.cols)] or [""]:
            self.lines.append((chunk, col))
        self.lines = self.lines[-self.rows:]

    def render(self, partial=None):
        im = Image.new("RGB", (self.w, self.h), BG); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, self.w, self.bar], fill=BAR)
        for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
            x = self.pad + i * 18 * self.scale; d.ellipse([x, self.bar // 2 - 6 * self.scale, x + 12 * self.scale, self.bar // 2 + 6 * self.scale], fill=c)
        d.text((self.pad + 70 * self.scale, self.bar // 2 - self.font.size // 2), self.title, font=self.font, fill=DIM)
        y = self.bar + self.pad
        rows = self.lines + ([partial] if partial else [])
        for text, col in rows[-self.rows:]:
            d.text((self.pad, y), text, font=self.font, fill=col); y += self.ch
        return im.resize((self.w // self.scale, self.h // self.scale), Image.LANCZOS) if self.scale > 1 else im


def render(events, out, png=None, cols=96, rows=22, font_size=15, title="terminal", speed=1.0, type_chunk=3, scale=1):
    scr = Screen(cols, rows, font_size, title, scale)
    frames, durs = [], []

    def add(im, ms):
        frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=64)); durs.append(max(20, int(ms / speed)))
    # No blank opening frame: the first frame is a poster in every GIF viewer, and an empty terminal makes the
    # thumbnail look broken. The first event is rendered immediately instead.
    for kind, val in events:
        if kind == "title":
            scr.title = val
        elif kind == "pause":
            add(scr.render(), int(val * 1000))
        elif kind == "clear":
            scr.lines = []; add(scr.render(), 200)
        elif kind == "type":
            steps = list(range(type_chunk, len(val), type_chunk)) + [len(val)]
            for i in steps:
                add(scr.render(partial=(glyphsafe(val[:i]) + "▌", FG)), 60 if i < len(val) else 350)
            scr.push(val, FG)
        else:
            scr.push(val, colour(val)); add(scr.render(), 110)
    add(scr.render(), 2500)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=False, disposal=1)
    if png:
        scr.render().save(png)
    return len(frames), sum(durs)


def selftest():
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")
    with tempfile.TemporaryDirectory() as d:
        cast = "#title: demo\n$ python3 check.py\n  ✔ control green\n  ✘ rule B UNCOVERED\nexit=1\n#pause: 0.5\n"
        gif, png = os.path.join(d, "a.gif"), os.path.join(d, "a.png")
        n, total = render(parse_cast(cast), gif, png, cols=40, rows=8, font_size=12)
        chk(os.path.getsize(gif) > 1000 and n == len(list(range(3, len("$ python3 check.py"), 3))) + 1 + 3 + 1 + 1, f"frame count matches events, no blank opening frame ({n})")
        chk(2500 + 500 < total < 9000, f"total duration is plausible ({total} ms)")
        im = Image.open(gif); saved = 0
        for k in range(getattr(im, "n_frames", 1)):
            im.seek(k); saved += im.info.get("duration", 0)
        # Pillow merges identical consecutive frames (a pause repeats the screen), so count may shrink but time must not
        chk(getattr(im, "n_frames", 1) <= n and abs(saved - total) <= 10 * n, f"GIF keeps the total duration within GIF rounding ({saved} vs {total} ms over {getattr(im, 'n_frames', 1)} frames)")
        last = Image.open(png).convert("RGB"); px = last.getdata()
        chk(any(p[0] > 200 and p[1] < 140 for p in px) and any(p[1] > 170 and p[0] < 140 for p in px), "last frame contains both red and green pixels")
        ev = parse_cast("$ ls\nfoo\n#pause: 2\n", from_run=True)
        chk([e[0] for e in ev] == ["type", "print", "print"], "--from-run treats every non-$ line as output (no directives)")
        ev = parse_cast("$ run /home/me/x\n1\n2\n3\n4\n", replace=[("/home/me", "~")], max_block=2)
        chk(ev[0][1] == "$ run ~/x" and [e[1] for e in ev[1:]] == ["1", "2", "  …"], "--replace rewrites lines and --max-block cuts long output")
        chk(colour('    print("FAIL: x")') == FG, "code lines are not coloured as status")
        chk(colour("🚨 push deletes 25 files") == RED and glyphsafe("🚨 x 🔴 y\tz") == "!! x ● y\tz", "emoji keep their colour but are drawn as text stand-ins")
        chk(colour("exit=0") == GREEN and colour("✘ x") == RED and colour("$ cmd") == FG and colour("#c") == DIM, "auto colours")
    return ok, lines


def main(argv):
    if "--selftest" in argv:
        ok, lines = selftest(); print(f"termgif selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines)); return 0 if ok else 2
    if "-h" in argv or "--help" in argv or not argv:
        print(__doc__); return 2
    opt = {"--out": None, "--png": None, "--cols": "96", "--rows": "22", "--font-size": "15", "--title": "terminal", "--speed": "1.0", "--from-run": None,
           "--max-block": "0", "--type-chunk": "3", "--scale": "1"}
    pos, i, repl = [], 0, []
    while i < len(argv):
        if argv[i] == "--replace" and i + 1 < len(argv):
            old, _, new = argv[i + 1].partition("="); repl.append((old, new)); i += 2
        elif argv[i] in opt and i + 1 < len(argv):
            opt[argv[i]] = argv[i + 1]; i += 2
        else:
            pos.append(argv[i]); i += 1
    src = opt["--from-run"] or (pos[0] if pos else None)
    if not src or not opt["--out"]:
        print(__doc__); return 2
    events = parse_cast(open(src, encoding="utf-8", errors="replace").read(), from_run=bool(opt["--from-run"]), replace=repl, max_block=int(opt["--max-block"]))
    n, total = render(events, opt["--out"], opt["--png"], int(opt["--cols"]), int(opt["--rows"]), int(opt["--font-size"]), opt["--title"], float(opt["--speed"]), int(opt["--type-chunk"]), int(opt["--scale"]))
    print(f"{opt['--out']}: {n} frames, {total / 1000:.1f} s, {os.path.getsize(opt['--out']) // 1024} KB" + (f"; {opt['--png']}" if opt["--png"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

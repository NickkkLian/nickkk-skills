#!/usr/bin/env python3
"""preview_cards.py — render the X thread and the Chinese piece of a post kit as image cards, so a person sees
what a reader will see before anything is published. A kit that exists only as text files hides two things a
file cannot show: how much of the 280 characters the post really uses, and whether the cover line still fits
when it is drawn at the size a phone shows it.

    python3 preview_cards.py <project-dir> [--out DIR] [--scheme dark|light] [--scale 1|2]
                             [--font PATH] [--cjk-font PATH] [--for-posting]
        --for-posting: leave the character count off the cover card — it is there for checking, and an
        image that is going to be posted should carry the cover line and nothing else
    python3 preview_cards.py --selftest

Reads <project-dir>/post-kit/x-post.md and <project-dir>/post-kit/xiaohongshu.md, and writes into
<project-dir>/post-kit/preview/ (or --out):
    x-thread.png    the root post and the `## Reply 1` block, each with its own character count
    xhs-cover.png   the cover line on a 3:4 card
    xhs-body-N.png  the body, paginated over as many 3:4 cards as it needs

The leading block of `#` lines in a source file is the kit's own note to the person posting, not part of the
post; it is stripped, exactly as the gate strips it. Nothing is truncated: text over its budget is drawn in
full with the overrun marked, so the person can see how much has to go.

The cards use the "Monet" colours (dark: the dusk band; light: the water-lily canvas). Latin text, labels and
numbers are drawn with the fonts in ../assets/fonts (Inter, Space Mono, and Fraunces for Latin in the cover line),
so they look the same on every machine; Chinese comes from the machine: a sans for the body, a bold serif for the
cover line when one is installed (Songti SC on macOS), the body face when not.

Exit 0 clean · 1 findings (the cards are still written) · 2 usage, or a font that cannot draw the text.
Requires Pillow and a font that has the glyphs — on macOS the defaults are found automatically; elsewhere pass
--cjk-font (Noto Sans CJK, Source Han Sans, Microsoft YaHei) if the search finds nothing.
"""
import os, re, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True   # importing postkit_check would otherwise leave a __pycache__ beside a shipped script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from postkit_check import cover_of   # one definition of what the cover line is; the two ship together

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "assets", "fonts")   # see SOURCES.md there

# The "Monet" colours: dark is the dusk band, light is the water-lily canvas. Every text colour clears 4.5:1 on
# its card and the accent bar clears 3:1; the selftest measures both.
SCHEMES = {                                             # bg, fg, dim, rule, accent, red
    "dark":  ((0x16, 0x34, 0x37), (0xec, 0xe5, 0xde), (0xaf, 0xa6, 0x9d), (0x39, 0x54, 0x56), (0xf8, 0xa1, 0xb3), (0xeb, 0x8b, 0x75)),
    "light": ((0xf7, 0xe9, 0xe8), (0x1d, 0x1b, 0x24), (0x60, 0x5e, 0x67), (0xd6, 0xd4, 0xdf), (0x05, 0x33, 0x33), (0xa9, 0x39, 0x20)),
}
# A font entry is a path, or (path, index) for a collection whose first face is the wrong one.
UI_FONTS = [os.path.join(FONT_DIR, "Inter-latin-var.woff"), "/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/segoeui.ttf"]
MONO_FONTS = [os.path.join(FONT_DIR, "SpaceMono-latin-400.woff"), "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "C:/Windows/Fonts/consola.ttf"]
DISPLAY_FONTS = [os.path.join(FONT_DIR, "Fraunces-latin-var.woff")]      # Latin in the cover line
CJK_FONTS = ["/System/Library/Fonts/PingFang.ttc", ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
             ("/System/Library/Fonts/STHeiti Medium.ttc", 1), ("/System/Library/Fonts/STHeiti Light.ttc", 1),
             "/System/Library/Fonts/Supplemental/Songti.ttc",
             "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
             "/usr/share/fonts/truetype/arphic/uming.ttc", "C:/Windows/Fonts/msyh.ttc"]
# The cover line's Chinese: a bold serif when the machine has one, the body face when it has none.
CJK_DISPLAY_FONTS = [("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 2),
                     "/usr/share/fonts/opentype/noto/NotoSerifCJKsc-Bold.otf",
                     os.path.expanduser("~/Library/Fonts/NotoSerifSC-Bold.otf"),
                     ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),   # face 1 is Songti SC Bold
                     "C:/Windows/Fonts/simsun.ttc"]
PROBE = "我一字"            # if the CJK font cannot draw these, it is the wrong font and nothing is rendered
PUA = "\ue123"             # a private-use code point no real font fills: its glyph IS the .notdef box
CJK = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]")
X_LIMIT, COVER_LIMIT = 280, 16


# ---------------------------------------------------------------- reading the kit

def strip_notes(text):
    """Drop the leading run of `#` lines. They are the kit's note to the person posting (which file to attach,
    when it goes out); a reader never sees them, so neither does the card."""
    return re.sub(r"\A(?:#.*\n)+", "", text).strip()


def split_thread(x):
    """(root, reply) on the `## Reply 1` heading — the same split the gate makes."""
    parts = re.split(r"^##\s*Reply 1\s*$", x, maxsplit=1, flags=re.M)
    return strip_notes(parts[0]), (parts[1].strip() if len(parts) > 1 else "")


def split_zh(zh):
    """(cover, body). Which line is the cover is decided by postkit_check.cover_of, so the card and the gate can
    never disagree about it — they did until 2026-09-22, and the gate was the one that was wrong."""
    cover, line = cover_of(zh)
    if not line:
        return "", strip_notes(zh)
    return cover, zh.split(line, 1)[-1].strip()


STRUCTURAL = re.compile(r"^(\u6b63\u6587|\u6807\u7b7e|\u5c01\u9762.*|body|tags)$", re.I)


def plain_text(line):
    """What a reader will see. Neither X nor Xiaohongshu renders Markdown, so the markers a draft is written
    with would be posted literally; they come out here, and out of the paste file the same way, so the card and
    the post agree. The words inside them stay."""
    line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)   # a heading needs the space; without it the line is a
                                                   # hashtag (#\u72ec\u7acb\u5f00\u53d1), and eating that # loses a tag
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"(?<!\w)__(.+?)__(?!\w)", r"\1", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    return line.replace("`", "")   # a code span that runs over two lines leaves one backtick on each


def body_lines(body):
    """The body as it will be read: Markdown markers gone, and the draft's structural headings (正文, 标签)
    dropped — but only those. A heading that carries content keeps its words: dropping every `#` line would
    lose a paragraph without anything saying so."""
    out = []
    for raw in body.split("\n"):
        line = raw.strip()
        if re.match(r"^(-{3,}|={3,})$", line):
            continue
        text = plain_text(line)
        if line.startswith("#") and STRUCTURAL.match(text.strip()):
            continue
        out.append(text.strip())
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return out


# ---------------------------------------------------------------- fonts

def load_first(paths, size, label):
    for entry in paths:
        p, indexes = (entry[0], (entry[1],)) if isinstance(entry, tuple) else (entry, (0, 1))
        if os.path.exists(p):
            for index in indexes:
                try:
                    return ImageFont.truetype(p, size, index=index), p
                except OSError:
                    continue
    raise SystemExit(f"preview_cards: no {label} font found. Pass one with --font / --cjk-font. Looked in:\n  "
                     + "\n  ".join(e[0] if isinstance(e, tuple) else e for e in paths))


def contrast(a, b):
    """WCAG 2 contrast ratio of two sRGB colours."""
    def lum(c):
        v = [x / 255 for x in c]
        v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def missing(font, ch):
    """True when the font has no glyph for ch: freetype hands back the .notdef box, which is byte-for-byte the
    glyph it draws for an unassigned private-use code point. A font whose .notdef is blank gives an empty mask,
    so an empty mask for a visible character counts as missing too."""
    if not ch.strip():
        return False
    try:
        m, n = font.getmask(ch), font.getmask(PUA)
    except Exception:
        return True
    if m.size[0] == 0 or m.size[1] == 0:
        return True
    return m.size == n.size and bytes(m) == bytes(n)


class Pen:
    """Draws mixed Latin and Chinese by picking a font per character, which is also how it measures: the width
    the card is laid out with is the width the glyphs actually take. Three roles: body text ("ui"), labels and
    counts ("mono"), and the cover line ("display"). A character a role's face lacks is drawn with the body
    face, and Chinese with the Chinese face of that role."""

    CHAIN = {"ui": ("ui",), "mono": ("mono", "ui"), "display": ("display", "ui")}

    def __init__(self, ui_path, cjk_path, scheme, scale):
        self.ui_path, self.cjk_path, self.scale = ui_path, cjk_path, scale
        self.bg, self.fg, self.dim, self.rule, self.accent, self.red = SCHEMES[scheme]
        self._cache, self._picked = {}, {}
        cjk, self.cjk_file = self.font(28, "cjk")
        bad = [c for c in PROBE if missing(cjk, c)]
        if bad:
            raise SystemExit(f"preview_cards: the font used for Chinese cannot draw {''.join(bad)} "
                             f"({self.cjk_file}). It would render empty boxes, so nothing was written. "
                             f"Pass a CJK font with --cjk-font.")
        _, self.ui_file = self.font(28, "ui")
        _, self.mono_file = self.font(28, "mono")
        _, self.display_file = self.font(28, "display")
        _, self.cjk_display_file = self.font(28, "cjk-display")

    def font(self, size, role):
        key = (size, role)
        if key not in self._cache:
            own_cjk = [self.cjk_path] if self.cjk_path else []   # a --cjk-font the person chose wins, cover included
            paths = {"ui": ([self.ui_path] if self.ui_path else []) + UI_FONTS,
                     "mono": MONO_FONTS + UI_FONTS,
                     "display": DISPLAY_FONTS + UI_FONTS,
                     "cjk": own_cjk + CJK_FONTS,
                     "cjk-display": own_cjk + CJK_DISPLAY_FONTS + CJK_FONTS}[role]
            f, p = load_first(paths, int(size * self.scale), "CJK" if role.startswith("cjk") else role)
            if role == "cjk-display" and any(missing(f, c) for c in PROBE):
                f, p = self.font(size, "cjk")      # a serif that cannot draw Chinese is no use for the cover
            if os.path.basename(p) == "Fraunces-latin-var.woff":
                f.set_variation_by_axes([700])     # the file's default instance is 900; the cover is set in bold
            self._cache[key] = (f, p)
        return self._cache[key]

    def pick(self, ch, size, role="ui"):
        key = (ch, size, role)
        if key not in self._picked:
            cjk = "cjk-display" if role == "display" else "cjk"
            found = None if CJK.match(ch) else next(
                (f for f in (self.font(size, r)[0] for r in self.CHAIN[role]) if not missing(f, ch)), None)
            self._picked[key] = found if found is not None else self.font(size, cjk)[0]
        return self._picked[key]

    def width(self, text, size, role="ui"):
        return sum(self.pick(c, size, role).getlength(c) for c in text)

    def gaps(self, text, role="ui"):
        """Characters no available font can draw — emoji, mostly. Reported, and drawn as an empty box."""
        seen, out = set(), []
        for ch in text:
            if ch in seen or not ch.strip():
                continue
            seen.add(ch)
            if missing(self.pick(ch, 28, role), ch):
                out.append(ch)
        return out

    def draw(self, d, xy, text, size, fill, role="ui"):
        x, y = xy
        for ch in text:
            f = self.pick(ch, size, role)
            if missing(f, ch):
                w, h = f.getlength(ch) or size * self.scale * 0.9, size * self.scale * 0.72
                d.rectangle([x + 1, y + size * self.scale * 0.22, x + w - 2, y + size * self.scale * 0.94],
                            outline=fill, width=max(1, int(self.scale)))
                x += w
                continue
            d.text((x, y), ch, font=f, fill=fill)
            x += f.getlength(ch)
        return x

    def wrap(self, text, size, width, role="ui"):
        """Greedy wrap. A Chinese line may break before any character; a Latin word may not be split, so a run
        of Latin moves to the next line whole."""
        lines, cur = [], ""
        for token in re.findall(r"[^\s]+|\s+", text):
            if CJK.search(token) or self.width(token, size, role) > width:
                for ch in token:
                    if self.width(cur + ch, size, role) > width and cur.strip():
                        lines.append(cur.rstrip())
                        cur = "" if ch.isspace() else ch
                    else:
                        cur += ch
                continue
            if self.width(cur + token, size, role) > width and cur.strip():
                lines.append(cur.rstrip())
                cur = "" if token.isspace() else token
            else:
                cur += token
        if cur.strip():
            lines.append(cur.rstrip())
        return lines or [""]


# ---------------------------------------------------------------- cards

def new_card(pen, w, h):
    img = Image.new("RGB", (int(w * pen.scale), int(h * pen.scale)), pen.bg)
    return img, ImageDraw.Draw(img)


def render_thread(pen, root, reply, out_path):
    """One image, the two posts stacked. Height follows the text, so a long post looks long."""
    W, PAD, GAP, SIZE, LEAD = 900, 44, 26, 27, 40
    blocks = []
    for label, text in (("Root post", root), ("Reply 1", reply)):
        if not text:
            continue
        lines = []
        for para in [plain_text(l) for l in text.split("\n")]:
            lines += pen.wrap(para, SIZE, (W - PAD * 2 - 28) * pen.scale) if para.strip() else [""]
        blocks.append((label, text, lines))
    # drawn onto a generous canvas and cropped to the last line, so the space under the second post is the same
    # margin as above the first one whatever the text does
    img, d = new_card(pen, W, PAD * 2 + sum(34 + len(b[2]) * LEAD + 56 + GAP for b in blocks))
    y = PAD * pen.scale
    for label, text, lines in blocks:
        over = len(text) > X_LIMIT
        x0 = PAD * pen.scale
        box_h = (34 + len(lines) * LEAD + 30) * pen.scale
        d.rectangle([x0 - 14 * pen.scale, y - 10 * pen.scale, (W - PAD + 14) * pen.scale, y + box_h],
                    outline=pen.rule, width=max(1, int(pen.scale)))
        d.rectangle([x0 - 14 * pen.scale, y - 10 * pen.scale, x0 - 11 * pen.scale, y + box_h],
                    fill=pen.red if over else pen.accent)
        pen.draw(d, (x0, y), label.upper(), 14, pen.dim, role="mono")
        y += 34 * pen.scale
        for line in lines:
            pen.draw(d, (x0, y), line, SIZE, pen.fg)
            y += LEAD * pen.scale
        count = f"{len(text)} / {X_LIMIT}"
        pen.draw(d, ((W - PAD) * pen.scale - pen.width(count, 14, "mono"), y + 4 * pen.scale),
                 count, 14, pen.red if over else pen.dim, role="mono")
        y += (30 + GAP) * pen.scale
    img = img.crop((0, 0, img.width, int(y - (GAP - PAD) * pen.scale)))
    img.save(out_path)
    return img


def render_cover(pen, cover, out_path, posting=False):
    W, H, PAD, SIZE = 900, 1200, 72, 66
    img, d = new_card(pen, W, H)
    lines = pen.wrap(plain_text(cover), SIZE, (W - PAD * 2) * pen.scale, role="display")
    y = (H * pen.scale - len(lines) * SIZE * 1.34 * pen.scale) / 2
    over = len(cover) > COVER_LIMIT
    for line in lines:
        pen.draw(d, (PAD * pen.scale, y), line, SIZE, pen.red if over else pen.fg, role="display")
        y += SIZE * 1.34 * pen.scale
    if not posting:   # the count is for the person checking the cover; it does not belong on the image that is posted
        mark = f"{len(cover)} / {COVER_LIMIT}"
        pen.draw(d, (PAD * pen.scale, (H - PAD) * pen.scale), mark, 20, pen.red if over else pen.dim, role="mono")
    img.save(out_path)
    return img


def render_body(pen, lines, out_dir, stem="xhs-body"):
    """Paginate the body over 3:4 cards. Nothing is dropped: a paragraph that does not fit starts the next card,
    and a paragraph longer than a whole card is split across cards rather than cut."""
    W, H, PAD, SIZE, LEAD = 900, 1200, 72, 30, 48
    room = H - PAD * 2 - 40                      # the 40 keeps the page number clear of the text
    pages, cur, used = [], [], 0
    for para in lines:
        if not para.strip():                     # the source's own blank lines; the gap between paragraphs is added below
            continue
        wrapped = pen.wrap(para, SIZE, (W - PAD * 2) * pen.scale)
        if cur and used + len(wrapped) * LEAD > room >= len(wrapped) * LEAD:
            pages.append(cur)          # a paragraph that fits on a card of its own is not split across two
            cur, used = [], 0
        for line in wrapped:
            if used + LEAD > room and cur:
                pages.append(cur)
                cur, used = [], 0
            cur.append(line)
            used += LEAD                         # every line costs a line, blank ones included — counting a
        if used + LEAD <= room and cur:          # paragraph gap as half a line let the last line fall off the card
            cur.append("")
            used += LEAD
    while cur and not cur[-1]:
        cur.pop()
    if cur:
        pages.append(cur)
    paths = []
    for n, page in enumerate(pages, 1):
        img, d = new_card(pen, W, H)
        y = PAD * pen.scale
        for line in page:
            pen.draw(d, (PAD * pen.scale, y), line, SIZE, pen.fg)
            y += LEAD * pen.scale
        mark = f"{n} / {len(pages)}"
        pen.draw(d, ((W - PAD) * pen.scale - pen.width(mark, 20, "mono"), (H - PAD) * pen.scale), mark, 20, pen.dim, role="mono")
        p = os.path.join(out_dir, f"{stem}-{n}.png")
        img.save(p)
        paths.append(p)
    return paths, pages


# ---------------------------------------------------------------- driver

def run(project, out=None, scheme="dark", scale=1, font=None, cjk_font=None, quiet=False, posting=False):
    kit = os.path.join(project, "post-kit") if os.path.isdir(os.path.join(project, "post-kit")) else project
    out = out or os.path.join(kit, "preview")
    os.makedirs(out, exist_ok=True)
    findings, written = [], []

    def read(name):
        p = os.path.join(kit, name)
        return open(p, encoding="utf-8").read() if os.path.isfile(p) else None

    x, zh = read("x-post.md"), read("xiaohongshu.md")
    if x is None and zh is None:
        raise SystemExit(f"preview_cards: no x-post.md or xiaohongshu.md under {kit}")
    pen = Pen(font, cjk_font, scheme, scale)

    if x is not None:
        root, reply = split_thread(x)
        for label, text in (("root post", root), ("reply", reply)):
            if len(text) > X_LIMIT:
                findings.append(f"x-post.md: the {label} is {len(text)} characters, {len(text) - X_LIMIT} over {X_LIMIT}")
        if not reply:
            findings.append("x-post.md: no `## Reply 1` block, so the card shows the root post alone")
        gaps = pen.gaps(root + reply)
        if gaps:
            findings.append("x-post.md: no glyph for " + " ".join(gaps) + " — drawn as an empty box")
        p = os.path.join(out, "x-thread.png")
        render_thread(pen, root, reply, p)
        written.append(p)

    if zh is not None:
        cover, body = split_zh(zh)
        if not cover:
            findings.append("xiaohongshu.md: no cover line found, so no cover card was written")
        else:
            if len(cover) > COVER_LIMIT:
                findings.append(f"xiaohongshu.md: the cover line is {len(cover)} characters, over {COVER_LIMIT}")
            gaps = pen.gaps(cover, role="display")
            if gaps:
                findings.append("xiaohongshu.md: no glyph for " + " ".join(gaps) + " on the cover")
            p = os.path.join(out, "xhs-cover.png")
            render_cover(pen, cover, p, posting=posting)
            written.append(p)
        lines = body_lines(body)
        if lines:
            paths, _ = render_body(pen, lines, out)
            written += paths

    if not quiet:
        name = os.path.basename
        print(f"fonts: body {name(pen.ui_file)} + {name(pen.cjk_file)} · labels {name(pen.mono_file)} · "
              f"cover {name(pen.display_file)} + {name(pen.cjk_display_file)}")
        for p in written:
            with Image.open(p) as im:
                print(f"  wrote {os.path.relpath(p, project) if p.startswith(project) else p}  {im.width}x{im.height}")
        for f in findings:
            print("  " + f)
        print(f"{len(written)} card(s) · {len(findings)} finding(s)")
    return findings, written


# ---------------------------------------------------------------- selftest

ZH_SAMPLE = ("\u5c01\u9762\uff1a\u8ddf\u4e00\u904d\u5c31\u770b\u5f97\u89c1\n\n"
             "\u5b83\u628a\u7ea2\u7eff\u5224\u5b9a\u6446\u5728\u7b2c\u4e00\u5c4f\u3002\n"
             + "\u6b63\u6587" * 120 + "\n")


def write_kit(d, **files):
    kit = os.path.join(d, "post-kit")
    os.makedirs(kit, exist_ok=True)
    base = {"x-post.md": "# note: attach demo.gif\n# note: goes out Tuesday\nA short root post.\n\n## Reply 1\nMIT: github.com/x/y\n",
            "xiaohongshu.md": ZH_SAMPLE}
    base.update(files)
    for name, text in base.items():
        open(os.path.join(kit, name), "w", encoding="utf-8").write(text)
    return d


def ink(path, box=None):
    if not os.path.isfile(path):
        return -1          # a missing card is a finding for the check that looks for it, not a crash here
    with Image.open(path) as im:
        px = list((im.crop(box) if box else im).convert("L").getdata())
    return len(set(px))


def selftest():
    ok = []

    def check(name, cond, detail=""):
        """Printed as it runs, not collected for the end: a crash in a later check used to take every result
        with it, so a mutation that broke one thing looked like it broke nothing."""
        ok.append((name, bool(cond), detail))
        print(f"  {'PASS' if cond else 'FAIL'}  {name.ljust(52)}  {'' if cond else detail}".rstrip())

    with tempfile.TemporaryDirectory() as tmp:
        # 1 · the note block belongs to the person posting, not to the post
        root, reply = split_thread(open(os.path.join(write_kit(os.path.join(tmp, "a")), "post-kit", "x-post.md"),
                                       encoding="utf-8").read())
        check("note lines are not part of the root post", "note:" not in root and root == "A short root post.", root)
        check("the reply is read whole", reply.startswith("MIT:"), reply)

        # 2 · a clean kit: no findings, every card written, and there is ink where the text goes
        f, w = run(os.path.join(tmp, "a"), quiet=True)
        check("clean kit has no findings", not f, str(f))
        names = sorted(os.path.basename(p) for p in w)
        check("clean kit writes thread, cover and body",
              set(names) >= {"x-thread.png", "xhs-cover.png", "xhs-body-1.png"} and all(os.path.isfile(p) for p in w),
              str(names) + (" (a name is returned for a card that was never saved)" if not all(os.path.isfile(p) for p in w) else ""))
        thread = next(p for p in w if p.endswith("x-thread.png"))
        check("the thread card has drawn text", ink(thread, (44, 44, 860, 200)) > 2, str(ink(thread, (44, 44, 860, 200))))
        with Image.open(thread) as im:
            check("the thread card is as wide as the layout", im.width == 900, im.size)
            rows = [y for y in range(im.height) if len(set(im.crop((0, y, im.width, y + 1)).convert("L").getdata())) > 1]
            below = im.height - rows[-1]
        check("no slab of empty space under the last post", 20 <= below <= 70, f"{below}px below the last ink")

        # 3 · over budget is reported, and the text is still drawn in full
        long_root = "x" * 300
        d = write_kit(os.path.join(tmp, "b"), **{"x-post.md": long_root + "\n\n## Reply 1\nlink: github.com/x/y\n"})
        f, w = run(d, quiet=True)
        check("a 300-character root post is reported", any("300 characters, 20 over" in x for x in f), str(f))
        check("the card is written anyway", any(p.endswith("x-thread.png") for p in w), str(w))

        # 4 · a cover line over sixteen characters
        d = write_kit(os.path.join(tmp, "c"), **{"xiaohongshu.md": "\u5c01\u9762\uff1a" + "\u957f" * 20 + "\n\n" + "\u6b63\u6587" * 120})
        f, _ = run(d, quiet=True)
        check("a 20-character cover line is reported", any("cover line is 20" in x for x in f), str(f))

        # 5 · a character with no glyph is named, not silently boxed
        d = write_kit(os.path.join(tmp, "d"), **{"x-post.md": "ship it \U0001f680\n\n## Reply 1\nMIT: github.com/x/y\n"})
        f, _ = run(d, quiet=True)
        check("a missing glyph is named", any("no glyph for" in x and "\U0001f680" in x for x in f), str(f))

        # 6 · the wrong font for Chinese stops the run instead of drawing boxes
        try:
            run(os.path.join(tmp, "a"), cjk_font="/System/Library/Fonts/Menlo.ttc", quiet=True)
            check("a Latin font passed as --cjk-font is refused", False, "no SystemExit")
        except SystemExit as e:
            check("a Latin font passed as --cjk-font is refused", "cannot draw" in str(e) and "Menlo" in str(e), str(e))

        # 7 · wrapping stays inside the card, and pagination drops nothing
        pen = Pen(None, None, "dark", 1)
        # a body at the gate's 900-character ceiling, in the paragraphs a real post has: one long block of text
        # never exercises the gap between paragraphs, and the gap is where the accounting went wrong
        paras = "\n\n".join("\u6b63\u6587" * (12 + i % 9) for i in range(24))
        body = body_lines(split_zh("\u5c01\u9762\uff1a\u77ed\n\n" + paras)[1])
        paths, pages = render_body(pen, body, os.path.join(tmp, "a"))
        widest = max(pen.width(l, 30) for page in pages for l in page)
        check("no wrapped line is wider than the card", widest <= 900 - 72 * 2, f"{widest:.0f}px")
        source = re.sub(r"\s", "", "".join(body))
        drawn = re.sub(r"\s", "", "".join(l for page in pages for l in page))
        check("pagination keeps every character", drawn == source, f"{len(drawn)} drawn vs {len(source)} in the body")
        para = "\u957f\u6bb5" * 60                       # four lines' worth, dropped in after the card is nearly full
        whole = render_body(pen, ["\u77ed\u53e5\u3002"] * 10 + [para], os.path.join(tmp, "a"), stem="widow")[1]
        holding = [i for i, page in enumerate(whole) if para[:8] in "".join(page)]
        check("a paragraph that fits a card is not split across two",
              len(holding) == 1 and para in "".join(whole[holding[0]]),
              f"{len(whole)} pages, paragraph starts on {holding}")
        # one paragraph longer than a whole card: the only thing that exercises the break inside a paragraph
        long_one = "\u957f\u6bb5" * 350
        big, big_pages = render_body(pen, [long_one], os.path.join(tmp, "a"), stem="long")
        check("a paragraph longer than a card is split, not cut", len(big_pages) > 1 and
              re.sub(r"\s", "", "".join(l for pg in big_pages for l in pg)) == long_one,
              f"{len(big_pages)} pages, {sum(len(''.join(pg)) for pg in big_pages)} of {len(long_one)} characters")
        over = [os.path.basename(q) for q in big if ink(q, (0, 1200 - 40, 900, 1200)) > 1]
        check("the page number strip stays clear", not over, str(over))
        check("a 900-character body runs to more than one card", len(pages) > 1, f"{len(pages)} page(s)")
        short, _ = render_body(pen, body_lines(split_zh(ZH_SAMPLE)[1]), os.path.join(tmp, "a"), stem="short")
        check("a body that fits stays on one card", len(short) == 1, f"{len(short)} page(s)")
        check("every page is written", all(os.path.isfile(p) for p in paths), str(paths))
        check("the last page has ink", ink(paths[-1], (72, 72, 828, 400)) > 2, "")
        spills = [os.path.basename(p) for p in paths if ink(p, (0, 1200 - 40, 900, 1200)) > 1
                  or ink(p, (0, 0, 900, 40)) > 1]
        check("no page draws text outside its margins", not spills, str(spills))

        # 8 · Markdown markers are not posted, and only structural headings are dropped
        kept = body_lines("## \u6b63\u6587\n\n## \u8fd9\u4e00\u6bb5\u662f\u5185\u5bb9\n\n**\u52a0\u7c97**\u7684\u8bdd\u4e0e `code.py`\n")
        check("a structural heading is dropped", "\u6b63\u6587" not in kept, str(kept))
        check("a content heading keeps its words", "\u8fd9\u4e00\u6bb5\u662f\u5185\u5bb9" in kept, str(kept))
        span = body_lines("\u4e00\u884c\u5c0f\u5b57\uff1a`n 1,215 \u884c\n\u6309\u91d1\u989d\u6c42\u548c`\n")
        check("a code span over two lines leaves no backtick", not any("`" in l for l in span), str(span))
        tags = body_lines("#AI\u5de5\u5177 #ClaudeCode\n")
        check("a hashtag at the start of a line keeps its #", tags == ["#AI\u5de5\u5177 #ClaudeCode"], str(tags))
        check("Markdown markers are not drawn", not any("*" in l or "`" in l or "#" in l for l in kept), str(kept))

        # 10 · the cover count is for checking; the posting cover does not carry it
        run(os.path.join(tmp, "a"), out=os.path.join(tmp, "post"), posting=True, quiet=True)
        corner = (72, 1200 - 72 - 4, 300, 1200 - 40)
        check("the checking cover carries its count", ink(os.path.join(tmp, "a", "post-kit", "preview", "xhs-cover.png"), corner) > 1, "")
        check("the posting cover does not", ink(os.path.join(tmp, "post", "xhs-cover.png"), corner) <= 1, "")

        # 9 · light scheme renders too, and is not the dark one
        run(os.path.join(tmp, "a"), out=os.path.join(tmp, "light"), scheme="light", quiet=True)
        pair = [os.path.join(tmp, "light", "xhs-cover.png"), os.path.join(tmp, "a", "post-kit", "preview", "xhs-cover.png")]
        if not all(os.path.isfile(q) for q in pair):
            check("light and dark cards differ", False, "one of the two cover cards was never written")
        else:
            with Image.open(pair[0]) as a, Image.open(pair[1]) as b:
                check("light and dark cards differ", a.getpixel((5, 5)) != b.getpixel((5, 5)), f"{a.getpixel((5, 5))} vs {b.getpixel((5, 5))}")
                # written out here, not read from SCHEMES: a check that takes its answer from the table it checks
                # agrees with any change to that table
                check("the covers sit on the water-lily canvas and the dusk band",
                      a.getpixel((5, 5)) == (0xf7, 0xe9, 0xe8) and b.getpixel((5, 5)) == (0x16, 0x34, 0x37),
                      f"{a.getpixel((5, 5))} / {b.getpixel((5, 5))}")

        # 11 · every text colour clears 4.5:1 on its card, the accent bar 3:1
        for name, (bg, fg, dim, rule, accent, red) in sorted(SCHEMES.items()):
            worst = min(contrast(c, bg) for c in (fg, dim, red))
            check(f"{name} cards: text, muted text and over-budget text clear 4.5:1", worst >= 4.5, f"{worst:.2f}")
            check(f"{name} cards: the accent bar clears 3:1", contrast(accent, bg) >= 3, f"{contrast(accent, bg):.2f}")

        # 12 · the faces that ship with the skill are the ones that draw, and gaps in them fall through
        pen = Pen(None, None, "dark", 1)
        base = os.path.basename
        check("body text is drawn in the shipped Inter", base(pen.ui_file) == "Inter-latin-var.woff", pen.ui_file)
        check("labels and counts are drawn in the shipped Space Mono", base(pen.mono_file) == "SpaceMono-latin-400.woff", pen.mono_file)
        default = ImageFont.truetype(pen.display_file, 66).getlength("Hamburg")
        check("Latin in the cover line is Fraunces at weight 700, not the file's 900",
              base(pen.display_file) == "Fraunces-latin-var.woff" and pen.font(66, "display")[0].getlength("Hamburg") != default,
              f"{pen.display_file}, width {pen.font(66, 'display')[0].getlength('Hamburg'):.0f} vs {default:.0f} at 900")
        arrow = pen.pick("→", 20, "mono")        # Space Mono's Latin subset has no arrow
        check("a character the label face lacks is drawn by the next face", not missing(arrow, "→"), "drawn as a box")
        serif = next((e[0] if isinstance(e, tuple) else e for e in CJK_DISPLAY_FONTS
                      if os.path.exists(e[0] if isinstance(e, tuple) else e)), None)
        if serif is None:
            print("  SKIP  the cover's Chinese is a bold serif  (this machine has none of CJK_DISPLAY_FONTS)")
        else:
            one, other = pen.pick("\u5c01", 66, "display"), pen.pick("\u5c01", 66)
            check("the cover's Chinese is the machine's bold serif, not the body face",
                  pen.cjk_display_file == serif and bytes(one.getmask("\u5c01")) != bytes(other.getmask("\u5c01")),
                  f"cover {pen.cjk_display_file} · body {pen.cjk_file}")
        chosen = next((p for p in (e[0] if isinstance(e, tuple) else e for e in CJK_FONTS) if os.path.exists(p)), None)
        if chosen:
            own = Pen(None, chosen, "dark", 1)
            check("a --cjk-font the person passes draws the cover too", own.cjk_display_file == chosen, own.cjk_display_file)
        saved = CJK_DISPLAY_FONTS[:]
        CJK_DISPLAY_FONTS[:] = [os.path.join(FONT_DIR, "SpaceMono-latin-400.woff")]   # a "serif" with no Chinese in it
        try:
            latin = Pen(None, None, "dark", 1)
            check("a cover face that cannot draw Chinese gives way to the body face",
                  latin.cjk_display_file == latin.cjk_file, f"cover {latin.cjk_display_file} · body {latin.cjk_file}")
        finally:
            CJK_DISPLAY_FONTS[:] = saved

    bad = sum(1 for _, g, _ in ok if not g)
    print(f"selftest: {len(ok) - bad}/{len(ok)} passed")
    return 0 if not bad else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args, opts = [], {}
    it = iter([a for a in argv if a != "--for-posting"])   # the one flag that takes no value
    for a in it:
        if a.startswith("--"):
            opts[a[2:]] = next(it, "")
        else:
            args.append(a)
    if len(args) != 1:
        return print(__doc__.strip()) or 2
    findings, _ = run(args[0], out=opts.get("out"), scheme=opts.get("scheme", "dark"),
                      scale=int(opts.get("scale", 1)), font=opts.get("font"), cjk_font=opts.get("cjk-font"),
                      posting="--for-posting" in argv)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

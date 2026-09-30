#!/usr/bin/env python3
"""postkit_check.py — gate for a six-piece post kit before a person publishes it by hand.

    python3 postkit_check.py <project-dir> [<project-dir> ...] [--link REGEX] [--private-words FILE] [--x-only]
        --x-only: for a release that posts only the X thread and its media, the rules
        about pieces that stay unpublished — P3 build-log, P4 xiaohongshu, P7 video length, P9 story-source
        section — are printed as notes instead of findings. Everything else still blocks.
    python3 postkit_check.py --selftest

Checks: P1 the six pieces + story-source.md + gif-run.txt present · P2 x-post ≤ 280 characters, ≤ 2 hashtags, contains a
link matching --link (default: any http(s) or github.com link) · P3 long post 400–800 words · P4 the Chinese version
(xiaohongshu.md): cover line ≤ 16 characters; body 300–900 Chinese characters (900 is a ceiling, and the room
above 600 is for the things that must be said, not for narration); no WeChat/phone/
e-mail; something concrete — a bullet or a code span — within the first 300 characters, so a reader sees what it
does and what it looks like in ten seconds; and the must-say items (invented data, what was not tested, what the
checker cannot see, a run that stopped on a limit, no baseline) gathered into one section a reader can skip to · P5 red lines in any
piece: job-hunting words, marketing superlatives, local paths, and every word in --private-words (one per line; or
$POSTKIT_PRIVATE_WORDS; or ~/.config/post-kit/private-words.txt — keep that file out of every repository) · P6 gif-run.txt
ends with exit 0 · P7 video script's last timestamp between 5:00 and 10:00 · P8 none of these framings that read
as facts and are not: "thirteen of the fifteen" / "13 of 15" (two lists counted with different rulers stated as one
nested count), "四组"/"另有 N 行" beside a split that already accounts for every row, "machine checks" (a checker has
rules; an acceptance list has checks) · P9 story-source.md has a section recording what the kit does
not say — a heading like "Not claimed anywhere" or "Not used (could not be sourced, or not tested)" — and names
each of the six pieces.
Exit 0 clean · 1 findings · 2 selftest failed.
"""
import os, re, sys, tempfile

SIX = ["x-post.md", "build-log.md", "youtube-script.md", "vertical-cut.md", "gif-script.sh", "xiaohongshu.md"]
JOB = re.compile(r"(?i)\b(hiring|job hunt|job-hunt|looking for (a )?job|open to work|résumé|resume|recruit)\b|求职|找工作|招聘|简历")
SUPER = re.compile(r"(?i)\b(revolutionary|one-click|game[- ]changer|10x|magic(al)?|effortless|silver bullet)\b")
LOCAL = re.compile(r"\x2fUsers\x2f|~\x2fDesktop|[A-Za-z]:\x5cUsers\x5c")
# the phone half used to be \d[\d\s-]{8,}\d, which matched every ISO date ("2025-10-01 → 2025-12-31") and every
# long figure a data post prints; a gate that fires on dates gets ignored. A phone now needs 10-11 digits in
# 3-3/4-4 groups, with nothing that would make it a date or an amount on either side.
CONTACT = re.compile(r"(?i)微信|wechat|vx[:：]|(?<![\d.\-/])(?:\+\d{1,3}[ -]?)?\d{3}[ -]?\d{3,4}[ -]?\d{4}(?![\d.\-/])|[\w.]+@[\w.]+\.\w+")
CJK = re.compile(r"[一-鿿]")
# P4's shape rules: the length above 600 may only buy the things that must be said, and they have to sit in one
# section a reader can skip to — not scattered through the post.
ZH_BODY = ("\n它把红绿判定摆在第一屏。\n- 跑一次就看得见：`check.py` 直接给红或绿\n" + "正文" * 160 +
           "\n\n**两件实话**：数据是编的；有几处没测过；检查器只读文件、看不到屏幕。\n")
def is_caveat_head(line):
    """A heading for the must-say section, not a passing mention of it: the word sits inside the line's leading bold
    span (**三件实话**：…) or the line is a short label (边界：). Without this, a cross-reference like
    "…见文末实话①" was taken as the heading and the section swallowed most of the post."""
    bold = re.match(r"\s*\*\*(.{0,16}?)\*\*", line)
    if bold and CAVEAT_HEAD.search(bold.group(1)):
        return True
    return len(line.strip()) <= 20 and bool(CAVEAT_HEAD.search(line))


CAVEAT_HEAD = re.compile(r"(实话|没验证过|这些没测|没测过什么|边界|限制|说清楚)")
CAVEATS = [re.compile(r"编的|假的|合成|synthetic"),          # the data is invented
           re.compile(r"没测|没跑|从没|没有人在"),             # what was never tested
           re.compile(r"看不到屏幕|只读文件|读的是.{0,12}结构"),  # the checker cannot see the screen
           re.compile(r"上限|没跑完|轮"),                     # the run stopped on a limit
           re.compile(r"基线|对照")]                          # no baseline run
# Framings that read as facts and are not. Each was once written by me and caught by an audit.
BANNED = [("thirteen of the fifteen", "the checker's rules are not a subset of the acceptance list"),
          ("13 of 15", "same"),
          ("四组", "the rows with no amount live inside another group; a fourth count invites adding them twice"),
          ("另有 3 行", "same"),
          ("machine checks", "a checker has rules; an acceptance list has checks")]


LINK = re.compile(r"https?://\S+|github\.com/\S+")


def cover_of(xh):
    """(the cover sentence, the line the body starts after). Kits write the cover in two shapes: `封面：…` on one
    line, and a `## 封面…` heading with the sentence on the next non-empty line. Taking the first line that
    contains 封面 measured the heading — 封面一句话, eight characters, always under the limit — instead of the
    sentence: seven of the thirteen kits, two of them over the limit, and the gate said nothing until the cards
    were drawn on 2026-09-22. preview_cards.py imports this, so both read the same line."""
    lines = xh.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#") and re.sub(r"^#+\s*", "", line).startswith("封面"):
            for nxt in lines[i + 1:]:
                if nxt.strip():
                    return nxt.strip().strip("*").strip(" 「」*"), nxt
        if "封面" in line and re.search(r"[:：]", line):
            return re.sub(r"^.*?[:：]", "", line).strip(" 「」*"), line
    return "", ""


def private_words(path=None):
    for cand in (path, os.environ.get("POSTKIT_PRIVATE_WORDS"), os.path.expanduser("~/.config/post-kit/private-words.txt")):
        if cand and os.path.isfile(cand):
            words = [w.strip() for w in open(cand, encoding="utf-8") if w.strip() and not w.startswith("#")]
            return re.compile("|".join(re.escape(w) for w in words), re.I) if words else None
    return None


X_ONLY_SKIPPED = ("P3", "P4", "P7", "P9")   # build-log, xiaohongshu, video length, story-source section
QUIET = False                               # the selftest runs the same samples; its notes are noise


def check_kit(skill_dir, link=LINK, private=None, x_only=False):
    kit = os.path.join(skill_dir, "post-kit")
    out = []
    for f in SIX + ["story-source.md", "gif-run.txt"]:
        if not os.path.isfile(os.path.join(kit, f)):
            out.append(("P1", f, "missing"))
    def read(f):
        p = os.path.join(kit, f)
        return open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""
    x = read("x-post.md").strip()
    if x:
        # a root post with an external link gets no link preview and is carried
        # further by replies than by the post itself, so the link belongs in the first reply. The file now holds
        # both: the root post, then a `## Reply 1` heading, then the reply.
        parts = re.split(r"^##\s*Reply 1\s*$", x, maxsplit=1, flags=re.M)
        body = re.sub(r"\A(?:#.*\n)+", "", parts[0]).strip()   # the whole `#` note block at the top is ours,
                                                             # not the post: strip all of it, not just line 1
        reply = parts[1].strip() if len(parts) > 1 else ""
        if len(body) > 280:
            out.append(("P2", "x-post.md", f"root post {len(body)} chars > 280"))
        if body.count("#") - body.count("# ") > 2:
            out.append(("P2", "x-post.md", "more than 2 hashtags"))
        if link.search(body):
            out.append(("P2", "x-post.md", f"the root post carries a link ({link.search(body).group(0)[:40]}) — it belongs in Reply 1"))
        if not reply:
            out.append(("P2", "x-post.md", "no `## Reply 1` block: the reply carrying the link and the licence is part of the post"))
        else:
            if len(reply) > 280:
                out.append(("P2", "x-post.md", f"Reply 1 is {len(reply)} chars > 280"))
            if not link.search(reply):
                out.append(("P2", "x-post.md", "Reply 1 has no link"))
    bl = read("build-log.md")
    if bl:
        n = len(re.findall(r"[A-Za-z0-9'’-]+", bl))
        if not 400 <= n <= 800:
            out.append(("P3", "build-log.md", f"{n} words, want 400–800"))
    xh = read("xiaohongshu.md")
    if xh:
        cover_text, cover = cover_of(xh)
        if cover and len(cover_text) > 16:
            out.append(("P4", "xiaohongshu.md", f"cover line {len(cover_text)} chars > 16"))
        body_cjk = len(CJK.findall(xh)) - len(CJK.findall(cover))
        if not 300 <= body_cjk <= 900:                 # 900 is a hard ceiling
            out.append(("P4", "xiaohongshu.md", f"{body_cjk} Chinese chars in body, want 300–900"))
        if CONTACT.search(re.sub(r"github\.com/\S+", "", xh)):
            out.append(("P4", "xiaohongshu.md", "contact info (wechat/phone/e-mail) present"))
        body = xh.split(cover, 1)[-1] if cover else xh
        opener = re.search(r"^\s*[-*] |`", body, re.M)   # the first bullet or the first code span: the concrete part
        if opener is None or len(CJK.findall(body[:opener.start()])) > 300:
            n = "none" if opener is None else len(CJK.findall(body[:opener.start()]))
            out.append(("P4", "xiaohongshu.md", f"nothing concrete in the first 300 characters (first bullet or code span after {n})"))
        head = next((l for l in body.splitlines() if is_caveat_head(l)), None)
        if head is None:
            out.append(("P4", "xiaohongshu.md", "the things that must be said (invented data, what was not tested, …) have no section of their own"))
        else:
            section = head + body.split(head, 1)[1]   # the heading line often carries the first item itself
            found = sum(1 for rx in CAVEATS if rx.search(section))
            if found < 3:
                out.append(("P4", "xiaohongshu.md", f"only {found} of the must-say items are inside that section; they belong together, not scattered"))
    for f in SIX + ["story-source.md"]:
        t = read(f)
        for rx, tag in ((JOB, "job-hunting"), (SUPER, "superlative"), (LOCAL, "local path"), (private, "private word")):
            if rx is None:
                continue
            m = rx.search(t)
            if m:
                out.append(("P5", f, f"{tag}: {m.group(0)!r}"))
    gr = read("gif-run.txt").strip().splitlines()
    if gr and not re.search(r"exit(=| code:? )0\b", gr[-1]):
        out.append(("P6", "gif-run.txt", f"last line is not 'exit=0': {gr[-1][:60]!r}"))
    ys = read("youtube-script.md")
    if ys:
        secs = 0
        for m in re.finditer(r"\|\s*(\d{1,2}):(\d{2})\s*(?:[-–]\s*(\d{1,2}):(\d{2}))?\s*\|", ys):
            if m.group(3):
                secs = max(secs, int(m.group(3)) * 60 + int(m.group(4)))
        if secs and not 300 <= secs <= 600:
            out.append(("P7", "youtube-script.md", f"last timestamp {secs // 60}:{secs % 60:02d}, want 5:00–10:00"))
    joined = "\n".join(read(f) for f in SIX)
    for phrase, why in BANNED:
        if phrase in joined:
            out.append(("P8", "a public piece", f'"{phrase}": {why}'))
    ss = read("story-source.md")
    if ss:
        if not re.search(r"^#+ *(Not claimed|Not used|Not said|没说什么|没用到)", ss, re.M):
            out.append(("P9", "story-source.md", "no section recording what the kit does not say (a '## Not claimed anywhere' / '## Not used' heading)"))
        for f in SIX:
            if f.split(".")[0].split("-")[0] not in ss:
                out.append(("P9", "story-source.md", f"never says which claims {f} uses"))
    if x_only:
        # a release that posts only the X thread and its GIF: the rules about pieces that stay unpublished become
        # notes — the gate is not loosened: drop the flag and they go red again, which is what the selftest checks.
        for code, where, why in out:
            if code in X_ONLY_SKIPPED and not QUIET:
                print(f"    · not posted in this release, so not blocking: {code} {where}: {why}")
        return [r for r in out if r[0] not in X_ONLY_SKIPPED]
    return out


def _mk(d, files):
    kit = os.path.join(d, "post-kit"); os.makedirs(kit, exist_ok=True)
    for f, t in files.items():
        open(os.path.join(kit, f), "w", encoding="utf-8").write(t)
    return d


GOOD = {"x-post.md": "It caught a path in a .pyc.\nBefore: grep found nothing.\nAfter: red.\n\n## Reply 1\nStdlib only, MIT: github.com/example/demo-tool\nNot tested: Windows.",
        "build-log.md": "word " * 500, "youtube-script.md": "| 1 | 0:00–1:00 | terminal | x |\n| 2 | 1:00–6:30 | editor | y |\n",
        "vertical-cut.md": "1 | 0:00-0:10 | red", "gif-script.sh": "#!/bin/bash\necho hi\n", "xiaohongshu.md": "封面：装上前灰 装上后红\n\n它把红绿判定摆在第一屏。\n- 跑一次就看得见：`check.py` 直接给红或绿\n" + "正文" * 160 + "\n\n**两件实话**：数据是编的；有几处没测过；检查器只读文件、看不到屏幕。\n",
        "story-source.md": "x-post build-log youtube vertical gif xiaohongshu\n## Not claimed anywhere\n- nothing", "gif-run.txt": "$ bash gif-script.sh\nhi\nexit=0\n"}


def selftest():
    global QUIET
    QUIET = True
    ok, lines = True, []

    def chk(c, label):
        nonlocal ok
        ok &= bool(c); lines.append(f"  {'✔' if c else '✘'} {label}")
    with tempfile.TemporaryDirectory() as t:
        chk(check_kit(_mk(os.path.join(t, "good"), GOOD)) == [], "control kit → 0 findings")
        dates = dict(GOOD, **{"xiaohongshu.md": "封面：短\n" + ZH_BODY +
                              "\n2025-10-01 → 2025-12-31 · 12,200.39 + 3,506.09 = 15,706.48 · n 1,215 行"})
        chk(check_kit(_mk(os.path.join(t, "dates"), dates)) == [], "dates and long figures are not phone numbers")
        phone = dict(GOOD, **{"xiaohongshu.md": "封面：短\n\n" + "正文" * 200 + "\n打 604 555 0143 找我"})
        chk({c for c, _, _ in check_kit(_mk(os.path.join(t, "phone"), phone))} == {"P4"}, "a real phone number is still caught")
        xo = dict(GOOD, **{"xiaohongshu.md": "封面：短\n正文太短",
                           "story-source.md": "x-post build-log youtube vertical gif xiaohongshu"})
        d_xo = _mk(os.path.join(t, "x-only"), xo)
        chk({c for c, _, _ in check_kit(d_xo)} == {"P4", "P9"}, "without the flag, the unposted pieces still go red")
        chk(check_kit(d_xo, x_only=True) == [], "--x-only drops exactly those and nothing else")
        xo_bad = dict(xo, **{"x-post.md": "a hook with github.com/example/demo-tool in it\n\n## Reply 1\nMIT: github.com/example/demo-tool"})
        chk({c for c, _, _ in check_kit(_mk(os.path.join(t, "x-only-bad"), xo_bad), x_only=True)} == {"P2"},
            "--x-only still catches a bad X post")
        cases = [("P1", {"story-source.md": None}), ("P2 root too long", {"x-post.md": "x" * 281 + "\n\n## Reply 1\nMIT: github.com/example/demo-tool"}),
                 ("P2 a multi-line note block is not the post", {"x-post.md": "# note one\n# note two\n# note three\n"
                                                                + "a real hook line\n\n## Reply 1\nMIT: github.com/example/demo-tool"}, set()),
                 ("P2 no reply block", {"x-post.md": "a real hook line, no link in it"}),
                 ("P2 link in the root post", {"x-post.md": "a hook line with github.com/example/demo-tool in it\n\n## Reply 1\nMIT: github.com/example/demo-tool"}),
                 ("P2 reply without a link", {"x-post.md": "a real hook line\n\n## Reply 1\nStdlib only, MIT, and no link at all"}),
                 ("P2 reply too long", {"x-post.md": "a real hook line\n\n## Reply 1\n" + "y" * 281 + " github.com/example/demo-tool"}), ("P3", {"build-log.md": "word " * 100}),
                 ("P4 cover", {"xiaohongshu.md": "封面：这一句话实在是太长太长太长了超过十六个字\n" + ZH_BODY}),
                 ("P4 cover under a heading", {"xiaohongshu.md": "## 封面一句话\n\n**这一句话实在是太长太长太长了超过十六个字**\n" + ZH_BODY}),
 ("P4 contact", {"xiaohongshu.md": "封面：短\n" + ZH_BODY + "\n打 604 555 0143"}),
                 ("P4 too long", {"xiaohongshu.md": "封面：短\n" + ZH_BODY + "正文" * 300}),
                 ("P4 nothing concrete early", {"xiaohongshu.md": "封面：短\n\n" + "铺垫" * 320 + "\n- 这才给出第一个具体的东西\n" + ZH_BODY}),
                 ("P4 no must-say section", {"xiaohongshu.md": "封面：短\n\n- `check.py` 给红或绿\n" + "正文" * 160}),
                 ("P4 must-say items scattered", {"xiaohongshu.md": "封面：短\n\n- `check.py` 给红或绿\n" + "正文" * 160 + "\n\n**边界**：就这些。\n"}),
                 ("P5", {"build-log.md": "word " * 450 + " I am looking for a job"}), ("P5", {"x-post.md": "a revolutionary tool\n\n## Reply 1\nMIT: github.com/example/demo-tool"}),
                 ("P5", {"build-log.md": "word " * 450 + " built for project-nightjar"}),
                 ("P5", {"vertical-cut.md": "see \x2fUsers\x2fsomeone/x"}), ("P6", {"gif-run.txt": "$ bash gif-script.sh\nboom\nexit=1\n"}),
                 ("P7", {"youtube-script.md": "| 1 | 0:00–1:00 | t | x |\n| 2 | 1:00–2:00 | t | y |\n"}),
                 ("P8", {"build-log.md": "word " * 450 + " thirteen of the fifteen checks are machine-checkable"}),
                 ("P8", {"xiaohongshu.md": "封面：短\n" + ZH_BODY + "\n分成四组：19／10／11"}),
                 ("P9", {"story-source.md": "claim -> SKILL.md (no section that says what the kit refuses to say)"})]
        for case in cases:
            code, over, want = (case + (None,))[:3] if len(case) == 2 else case
            want = {code.split(' ')[0]} if want is None else want
            files = dict(GOOD)
            for k, v in over.items():
                if v is None:
                    files.pop(k)
                else:
                    files[k] = v
            pw = os.path.join(t, "private.txt"); open(pw, "w").write("# names that must not be published\nproject-nightjar\n")
            got = {c for c, _, _ in check_kit(_mk(os.path.join(t, code + "-" + str(abs(hash(str(sorted(over.items())))) % 10**8)), files), private=private_words(pw))}
            chk(got == want, f"{code} sample → {sorted(want) or 'no findings'} (got {sorted(got) or 'none'})")
    QUIET = False
    return ok, lines


def main(argv):
    ok, lines = selftest()
    if "--selftest" in argv or not ok:
        print(f"postkit_check selftest · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed"); print("\n".join(lines))
        return 0 if ok else 2
    skip = {argv[i + 1] for i, a in enumerate(argv[:-1]) if a in ("--link", "--private-words")}
    dirs = [a for a in argv if not a.startswith("-") and a not in skip]
    if not dirs:
        print(__doc__); return 2
    rc = 0
    for d in dirs:
        f = check_kit(d, re.compile(argv[argv.index("--link") + 1]) if "--link" in argv else LINK,
                      private_words(argv[argv.index("--private-words") + 1] if "--private-words" in argv else None),
                      x_only="--x-only" in argv); rc |= 1 if f else 0
        print(f"{'✘' if f else '✔'} {os.path.basename(os.path.abspath(d))}/post-kit: {len(f)} findings")
        for code, fn, msg in f:
            print(f"    {code} {fn}: {msg}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

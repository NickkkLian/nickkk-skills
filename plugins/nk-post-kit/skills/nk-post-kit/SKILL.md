---
name: nk-post-kit
description: "Turn a finished repository, tool or skill into a set of posts a person publishes by hand — a short X post, a 400–800 word build log, a 5–10 minute video script, a 60–90 second vertical cut, a GIF recording script, and a Chinese Xiaohongshu version — every claim traced to a file or a real run, with a gate that blocks invented numbers, superlatives, private names and contact details. Use when something is shipped and needs to be shown, when drafting a weekly build log, or when a demo GIF is needed without screen recording. scripts/termgif.py renders a scripted terminal session to a GIF, and scripts/preview_cards.py draws the thread and the Chinese post as image cards, so length, wrapping and the cover line are seen before anything goes out. Not an auto-poster: nothing is published by the skill."
license: MIT
compatibility: termgif.py and preview_cards.py need Pillow (pip install pillow); termgif needs a monospace TrueType font and preview_cards needs a font with Chinese glyphs (macOS has one; elsewhere pass --cjk-font); its Latin faces ship in assets/fonts (Inter, Space Mono, Fraunces; SIL OFL 1.1). postkit_check.py is stdlib only.
metadata:
  provenance: own practice (2026-09) writing launch material for a set of open-source skills; see Provenance
  version: 0.2.4
---
# Post kit

**A post about something you built is believed for the same reason the thing is: the claims can be checked.**
The failure mode is not bad writing; it is a number nobody measured, a "used by" nobody counted, or an
incident retold so smoothly that it no longer matches what happened. This skill writes six pieces from the
repository and its evidence, and a gate refuses the drafts that drift from it.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- A repository, tool or skill is finished and needs a post, a thread, a video or a GIF.
- A weekly build log is due and the material is scattered across commits and test output.
- A demo GIF is needed and screen recording is not practical (CI, remote machine, no GUI).

## Procedure

1. **Collect the sources first** into `post-kit/story-source.md`: one line per claim you intend to make, with
   the file or command output it comes from. A claim with no source line does not go in any piece.
2. **Record a real run** that shows before and after: write `post-kit/gif-script.sh` (prepare a sample in a
   temp dir → run the "before" where nothing is caught → run the tool → show the catch → clean up), run it,
   and save its raw output to `post-kit/gif-run.txt` ending with the real exit code.
3. **Write the six pieces** from `references/template.md`: `x-post.md` (root ≤ 280 with **no** link, plus a `## Reply 1` block ≤ 280 that carries the link and the licence),
   `build-log.md` (400–800 words: the incident, why the usual approach misses it, what the tool does, before
   and after with a real output excerpt, what it does not check, install), `youtube-script.md` (5–10 minutes,
   table of segment / duration / on screen / narration; cold open on the moment it goes red),
   `vertical-cut.md` (3–5 segments from the long script, 60–90 seconds, first second is the catch),
   `xiaohongshu.md` (Chinese: cover line ≤ 16 characters stating the before/after difference, 300–900
   characters of body, something concrete in the first 300, the things that must be said gathered into one
   section, no contact details).
4. **Render the GIF without recording**: turn the run into a cast (`$ command` lines are typed, other lines
   printed, `#pause: s`, `#title: …`) and run
   `python3 <skill-dir>/scripts/termgif.py demo.cast --out demo.gif --png poster.png --cols 88 --rows 18`.
   Or straight from the run: `--from-run post-kit/gif-run.txt --replace "/long/local/path=~/tool" --max-block 8`.
   Look at the PNG before publishing it.
5. **Look at the cards before the gate**:
   `python3 <skill-dir>/scripts/preview_cards.py . --out post-kit/preview`
   draws the root post and the reply with their character counts, the cover line at cover size, and the body
   paginated over 3:4 cards. Read them. A file cannot show that the cover line is too long to read at a glance,
   that a paragraph wraps into a wall, or that the last line falls off the card; the picture can. Neither
   platform renders Markdown, so the cards drop `**` and `##` — what you see is what a reader gets. The cover
   card shows its character count for checking; add `--for-posting` to draw the cards you will actually post,
   without it.
6. **Gate the kit**: `python3 <skill-dir>/scripts/postkit_check.py . --private-words ~/.config/post-kit/private-words.txt`
   (P1 all pieces present · P2 X length/hashtags/link · P3 word count · P4 Chinese cover/body/contacts ·
   P5 job-hunting words, superlatives, local paths, your private words · P6 the run exited 0 · P7 video length ·
   P8 framings that read as facts and are not · P9 story-source.md says what the kit does not claim).
   `--x-only` narrows it to the pieces a thread release actually publishes.
   Keep the private-words file outside every repository; it lists exactly what must not be published.
7. **A person publishes.** The skill drafts and checks; posting stays a human action.

## Rules that keep it honest

- Numbers come from evidence files or self-test output, quoted as they appear. "About 7,500" in a doc and
  "7,597" in a replay log are different claims; use the one you can point at.
- Incidents are told by their shape — the command, the output, what went wrong — not by which project.
- Describe a tool by what it solves, the before/after difference, and its boundaries. No "revolutionary",
  no "one-click", no adoption numbers without a source.
- The "before" in a demo must be a real run, not a strawman built to lose.

## Boundaries

- The gate checks shape and red-line words; it cannot tell whether a sentence is true. The story-source file
  and a reviewer are for that.
- termgif renders text frames; it does not capture real GUIs. For interface demos, record the screen and
  convert with ffmpeg.
- The Chinese checks count characters and look for contact patterns; they do not judge tone.
- A preview card is this skill's own drawing, not a screenshot of X or Xiaohongshu: the fonts and the
  line breaks are close, not identical. It answers how long and how dense, not how it will look pixel
  for pixel.

## Provenance

Own practice, 2026-09: writing launch material for a batch of open-source skills, where the first drafts
included a number from a design doc instead of the measured log, a before/after GIF whose "after" was an
echo of a verdict rather than the tool's output, and a private project name in a gate's own source. Each of
those is now a gate rule or a procedure step. The card step (5) came last and for the same reason: the gate
had been reading the wrong line as the cover — the heading above it, four words long and always inside the
limit — for seven of thirteen kits, and it went on saying nothing until the cards were drawn and two covers
turned out to be over it. A check that reads the file can be looking at the wrong part of it; a picture of the result cannot.
No external source.

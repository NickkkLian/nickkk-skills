# The six pieces

Red lines for all pieces: no job-hunting content; no private system details (project names, account
lists, local paths); no invented numbers; no superlatives; every piece is posted by a person.

## 1. x-post.md — X post (root ≤ 280 characters, **no link**) + a `## Reply 1` block
Line 1 is one of four hook shapes — the **result**, a **contradiction**, a **surprising number**, or a
**constraint** — never a label like "The idea:" or "Out:". Then the surprising middle, then the limit.
The link, the licence and one "what I did not test" line go in `## Reply 1` (also ≤ 280): a root post with an
external link gets no link preview and travels worse.
Check: `postkit_check.py` P2 — root ≤ 280 with no link, Reply 1 present, ≤ 280, carrying the link.

## 2. build-log.md — long post (400–800 words)
Sections: (1) the incident, concrete to the command and output shape; (2) why the usual approach misses
it; (3) what the tool does — criteria and script; (4) before and after, each with an actual output excerpt;
(5) boundaries — what it does not check; (6) install in two lines. End with a line listing the evidence
files the numbers came from.

## 3. youtube-script.md — 5–10 minute video
Table: segment | duration | on screen (terminal / editor / diagram) | narration points.
Skeleton: 0:00 cold open on the moment it goes red → incident replay → before → after → how it works →
boundaries → install (every install path the README teaches, including any GUI panel route) → one-line close.

## 4. vertical-cut.md — 60–90 second vertical cut
3–5 segments picked from the long script: segment number, start–end, one caption line each. The first
second is the red/caught moment.

## 5. gif-script.sh — demo recording script
Runs in a fresh temp directory: prepare a sample → run the "before" (nothing catches it) → use the tool →
run the "after" (it is caught) → clean up. `sleep 1.5` between steps if a human will screen-record it.
Asserts its own expected exit codes and exits non-zero if the catch does not happen. Its raw output is
saved as gif-run.txt.

## 6. xiaohongshu.md — Chinese version
Cover line ≤ 16 characters stating the before/after difference. Body 300–600 characters: one sentence of
scene → one sentence of incident → what the tool does → the difference after installing → one sentence of
boundaries → end by inviting questions in the comments. No WeChat, phone or e-mail.

## story-source.md
One line per factual claim used in any piece → the file and line, the self-test line, or the run it came from.

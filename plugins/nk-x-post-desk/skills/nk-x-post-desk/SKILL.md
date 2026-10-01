---
name: nk-x-post-desk
description: "Turn a folder of drafted X posts into one page of prefilled composer links that the user presses themselves. The agent writes each post as a folder (post.md: the root post, then each reply, separated by a line of =====; at most one picture; an optional picture description), and scripts/build_desk.py checks every part the way X counts it (280, any link or bare domain counts 23, wide characters count 2), refuses a link in the root post unless that is allowed, and a folder that does not keep the format, and writes one self-contained desk.html: a card per post with the picture, a button that opens X's composer with the text filled in, a field for the published post's link that turns the next part into a reply to it, copy buttons and a posted mark. Nothing is posted, no account is connected, no API key, and the page asks no other site for anything. Use when you have drafted posts or a thread for X and the user will publish by hand. Not a scheduler, and it cannot attach the picture."
license: MIT
metadata:
  provenance: the author's own page for publishing launch posts by hand (2026); the counting rule was read from X's open-source twitter-text library; see Provenance
---

# X Post Desk

Drafted posts become one page the user works through by hand: open the post in X with the words already typed, add
the picture, press Post, paste the new post's link, open the reply. The agent writes folders; the script checks them
and builds the page; the person does every action on X. Nothing here posts, schedules or signs in.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- You drafted one or more X posts, or a thread, and the user wants to publish them personally.
- The user does not want to connect their X account to a tool, or has no API access.
- Drafts sit in files and the user is copying them into X one part at a time.
- Not for scheduling, for posting on the user's behalf, or for any network other than X. If the user wants posts to go
  out by themselves, say that this skill does not do it and that a scheduler with a connected account does.

## Procedure

The format in full, with every refusal and its fix, is [references/format.md](references/format.md). A complete
example is `references/example-desk/` (three posts about an invented tool).

1. **Pick the desk folder.** One folder holds every post of this batch, for example `posts/` in the project. Ask
   where it should go only if the project gives no obvious place.
2. **Write one folder per post**, named `YYYY-MM-DD-name`: the day the user plans to post it, then a short name in
   lower-case letters, digits and hyphens (`2026-11-03-launch`). The date orders the cards. It schedules nothing.
3. **Write `post.md`.** The root post first, then each reply, separated by a line that holds only `=====`. Put links
   in a reply: by default the build refuses a root that carries one. A file name such as `notes.md` or `main.py` is
   a link on X (`.md` and `.py` are real top-level domains), so reword it in the root; in a reply the build prints a
   notice for it and goes on. If the user wants a link in the root post, build with `--allow-root-link` or set
   `"allowRootLink": true` in `desk.json`. Do not switch that on unless the user asked for it.
4. **Add at most one picture** to the folder (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, up to 5 MB), and `alt.txt`
   with one or two sentences that describe it. The page shows the picture so the user can save it; a link cannot
   attach it.
5. **Optionally write `desk.json`** next to the post folders: `{"title": "...", "note": "..."}`. The note is one
   line shown above the cards, for example the order to post in. A third key, `"allowRootLink": true`, lets root
   posts carry links (step 3).
6. **Check while drafting.** `python3 <skill-dir>/scripts/build_desk.py <desk-folder> --check` prints each
   part's length as X counts it and exits 1 on any problem, naming the folder, the part and the fix. To measure one
   text: `python3 <skill-dir>/scripts/build_desk.py --count "the text"`. Shorten the text yourself; never
   split a part to get under the limit without telling the user.
7. **Build.** `python3 <skill-dir>/scripts/build_desk.py <desk-folder>` writes `<desk-folder>/desk.html`
   (`--out FILE` puts it elsewhere). With any problem it writes nothing.
8. **Hand it over.** Tell the user the path of `desk.html` and to open it in a browser, and say what the page does
   not do: it does not post, it does not attach the picture, and it cannot know whether a post went out. Do not open
   x.com yourself and do not press the page's buttons for the user.

## What the script checks

| Code | What it refuses |
|---|---|
| F01 | no desk folder, or no post folder in it |
| F02 | a folder that is not named `YYYY-MM-DD-name`, or a date that does not exist |
| F03 | `post.md` missing, empty or not UTF-8 |
| F04 | an empty part: two separators in a row, or one at the start or the end |
| F05 | more than one picture, a picture type the page does not embed, or `alt.txt` with no picture |
| F06 | a picture that is empty, over 5 MB, or not the type its name says |
| F07 | a `desk.json` that is not valid JSON, has a key other than `title`, `note` and `allowRootLink`, or a value of the wrong type |
| P01 | a part over 280 as X counts it |
| P02 | a link in the root post, unless `--allow-root-link` is given or `desk.json` has `"allowRootLink": true` |
| P03 | a control character in a part |
| A01 | a built page that refers to anything outside itself: the build reads its own output back before writing |

One notice, which refuses nothing and leaves the exit code alone: a bare file name in a reply that X will turn into
a link (`notes.md`, `main.py`). The line starts with `·`. Tell the user about it, and reword the name if a live link
is not what they mean.

`python3 <skill-dir>/scripts/build_desk.py --selftest` plants each of these mistakes and expects the refusal.
Each guarded behaviour was also switched off on purpose, one at a time, and the self-test went red for it.

## What the page is

- One HTML file with the pictures inside it. It works from a local file and offline. Its Content-Security-Policy
  allows only its own script and style (named by sha256) and embedded pictures, so the browser itself refuses any
  request to another host.
- The buttons are plain links to X's documented web intent, `https://x.com/intent/tweet`, with `text` and, for a
  reply, `in_reply_to`. A reply button has no link until the user pastes the link of the post it answers, and only a
  link of the form `x.com/<name>/status/<digits>` is accepted.
- Posted marks and pasted links stay in that browser's local storage. The page says so. They do not follow the user
  to another browser or device, and a rebuilt page keeps them as long as the post folder keeps its name.
- Post text is written into the page as text. Markup inside a post is shown, not run.

## Boundaries

- It does not post, schedule, attach the picture, or check that a post went out. The user does each of these.
- The count follows X's published rule, with one known gap: an emoji sequence (a flag, a family, a skin tone) is
  counted per code point here and as 2 on X, so the number shown can be higher than X's, never lower.
- The reply link was tried by the author on a Mac browser. The X phone app has not been tried: if X opens a new post
  instead of a reply, the page tells the user to open the post, press Reply and paste the copied text.
- The page is a local file. To use it on a phone the user has to get the file there; nothing syncs.
- X can change or remove its web intent. The page then still shows every text with a copy button.
- Not affiliated with X.

## Provenance

The author's own page for publishing launch posts by hand (2026): the drafts were in folders, and each thread had a
root post, a reply with the link and one picture. This skill is that page with the personal parts taken out and the
folder format written down. The counting rule (280 weighted characters,
23 per link, the list of 1,419 top-level domains that make a bare name a link) was read from X's open-source
twitter-text library. The web intent and its `text` and `in_reply_to` parameters are from X's developer
documentation. The example posts and the picture in `references/example-desk/` are invented.

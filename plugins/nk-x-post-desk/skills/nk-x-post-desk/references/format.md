# The desk folder format

Everything `build_desk.py` reads, and every way it says no.

## Layout

```text
posts/                               the desk folder: any name, anywhere
  desk.json                          optional
  2026-11-03-launch/                 one folder per post
    post.md                          required
    poster.png                       optional: at most one picture
    alt.txt                          optional: the picture's description
  2026-11-06-how-it-works/
    post.md
  _drafts/                           a folder that starts with _ or . is skipped
  desk.html                          written by the build
```

Files at the top of the desk folder other than `desk.json` are left alone. Inside a post folder, files other than
`post.md`, `alt.txt` and one picture are not read; the build lists them so nothing is skipped silently.

## The post folder's name

`YYYY-MM-DD-name`.

- The date is the day you plan to post. It orders the cards and is shown on the card. Nothing is scheduled.
- The name is lower-case letters, digits and hyphens. It is the card's title, and the key under which the page
  remembers "posted" and the pasted links: rename the folder and that post starts as not posted.

## post.md

The root post, then each reply, with a line that holds only `=====` (five or more) between them.

```text
my phone has 400 recorded walks and i have never looked at one of them again.
so i built walkposter.
=====
it runs on your own machine, and the file never leaves it.
example.com/walkposter
```

- A root with no reply is fine. There is no upper limit on replies.
- Line breaks inside a part are kept as written. Blank lines around a part and spaces at the end of a line are
  dropped (X would count them).
- UTF-8. A byte-order mark at the start is ignored.
- There are no headings, comments or front matter: every line that is not a separator is posted.

## Links in the root post

By default the build refuses a root post that carries a link (P02): many people keep the link in a reply. The
message says which kind it found:

- `the root post carries a link ('https://example.org/x')` for an address written with `http://` or `https://`;
- `X turns 'CLAUDE.md' into a link` for a bare name that ends in a real top-level domain, which is a link on X
  whether or not you meant one (see the next section).

To let the root carry a link, either run the build or the check with `--allow-root-link`, or put
`"allowRootLink": true` in `desk.json`. Either one is enough. Nothing else changes: the link still counts 23.

A reply may always carry links. One thing is pointed out there, and in a root where links are allowed: a bare file
name that X will turn into a link. The build prints a line that starts with `·`, for example
`· 2026-11-03-launch/post.md reply 1: X turns 'notes.md' into a link (.md is a real top-level domain) and counts it as 23.`
This is a notice, not a problem: the page is built and the exit code stays 0. It is given for a name with no
`http(s)://` and no path that ends in one of: `md py sh rs pl pm ps cc mm ml mk tf zip mov java` (file endings that
are also real top-level domains). Other bare names that X links, such as `example.com`, are taken as meant.

## How a part is counted

The limit is 280, counted the way X counts:

- every link counts 23, whatever its length;
- a link is an `http(s)://` address **or a bare name that ends in a real top-level domain**: `example.com/page`,
  but also `CLAUDE.md`, `main.py` and `run.sh` (`.md`, `.py` and `.sh` are country domains). `report.html`,
  `x.txt` and `node.js` are not links;
- a character counts 1 in Latin, Greek, Cyrillic and other scripts up to U+10FF, and for curly quotes and dashes;
  it counts 2 everywhere else: Chinese, Japanese and Korean text, full-width punctuation, arrows, `…`, emoji;
- text is normalised to NFC first, so `e` followed by a combining accent counts 1.

Known gap: X counts a whole emoji sequence (a flag, a family, a skin-tone variant) as 2. Here each code point of the
sequence counts, so the number can be higher than X's. It is never lower.

`python3 scripts/build_desk.py --count "some text"` prints one text's count (`-` reads it from standard input).

## The picture

At most one per post: `.png`, `.jpg`, `.jpeg`, `.gif` or `.webp`, up to 5 MB, and the file's first bytes must match
its name. It is embedded in the page so the page stays one file. X's web intent has no parameter for media, so the
user saves the picture from the page (or takes it from the folder) and adds it in X.

`alt.txt` is the description to paste into X's ALT field. It is shown under the picture with a copy button and used
as the picture's alternative text on the page. Line breaks in it become spaces.

## desk.json

```json
{ "title": "walkposter launch week", "note": "One a day, top to bottom.", "allowRootLink": false }
```

All three keys are optional. `title` and `note` are plain text: `title` up to 80 characters (default "X Post Desk"),
`note` up to 400. `allowRootLink` is `true` or `false` (default `false`): `true` lets a root post carry a link, the
same as `--allow-root-link` on the command line. Any other key is refused, so a typo does not pass as a setting.

## Refusals

Any problem stops the build before anything is written, and every problem is listed, not only the first.

| Code | Message starts with | Fix |
|---|---|---|
| F01 | there is no such folder · there is no post folder in it | point at the desk folder; add a post folder |
| F02 | a post folder is named YYYY-MM-DD-name · is not a date that exists | rename the folder, or start its name with `_` to leave it out |
| F03 | there is no post.md in it · it is empty · it is not UTF-8 text | write `post.md` as UTF-8 |
| F04 | this part is empty | remove the extra `=====`, or write the part |
| F05 | N pictures · pictures are not embedded · a picture description with no picture | keep one picture; convert it to PNG, JPEG, GIF or WebP; remove `alt.txt` |
| F06 | the file is empty · N MB · the content is not image/… | export the picture again |
| F07 | it is not valid JSON · unknown key · must be plain text · "allowRootLink" must be true or false | fix `desk.json` |
| P01 | N as X counts it, the limit is 280 (N over) | shorten that part |
| P02 | the root post carries a link ('…') · X turns '…' into a link | move the link to a reply, or reword the name; or allow root links with `--allow-root-link` or `"allowRootLink": true` |
| P03 | it holds a control character (U+…) | remove it; a tab becomes spaces |
| A01 | the built page failed its own audit | a bug in the builder: report it; nothing was written |

Exit codes: 0 fine, 1 at least one problem (or a failed self-test), 2 the command line was not understood. A notice
(a line that starts with `·`: a skipped folder, a file that was not read, a file name X will link) never changes the
exit code.

## The page's own storage

`desk.html` keeps two things in the browser's local storage, under keys that start with `xpd:` followed by the post
folder's name: whether the post is marked as posted, and the link pasted into each reply field. Nothing else is
stored and nothing is sent anywhere. A browser may share this storage between all pages opened from local files
(not checked browser by browser), in which case two desks that both contain a folder with the same name share that
post's mark.

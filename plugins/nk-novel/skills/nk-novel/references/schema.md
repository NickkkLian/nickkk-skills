# story.json

One JSON object. Every field is optional to the parser; the checker reports what the plan needs (codes in
brackets). `assets/example-story.json` fills every field.

| Field | Type | Meaning | Checked by |
|---|---|---|---|
| `title` | string | working title | page only |
| `idea` | string | the idea as first stated | page only |
| `retelling` | string | the whole story in one sentence | S06 (missing or more than one sentence) |
| `caps.main_characters` | integer | most main characters the plan may have | S07 |
| `caps.places` | integer | most places the plan may have | S07 |
| `world.rules[]` | `{id, rule, cost}` | what holds in this world and what using it costs | S01, S08 |
| `world.not_allowed[]` | string | what this world does not allow | page only |
| `world.places[]` | `{id, name}` | places events can happen | S01, S07 |
| `characters[]` | see below | the cast | S01, S02, S03, S05, S07 |
| `spine[]` | see below | the events that make the story | S01, S02, S05, S08 |
| `structure.acts[]` | `{name, beats[]}`; beat `{name, events[]}` | acts and beats pointing at spine event ids | S01 |
| `foreshadowing[]` | `{id, clue, planted_in, paid_off_in, left_open_on_purpose}` | chapter numbers; `paid_off_in` null means not yet | S01, S04, S06 |
| `questions[]` | `{id, question, opened_in, answered_in}` | questions the reader carries; `answered_in` null means still open | S01, S06 |
| `chapters[]` | `{n, title, pov, events[], summary}` | `n` is the chapter number, `pov` a character id, `events` spine ids | S01, S02 |

## characters[]

| Field | Type | Meaning |
|---|---|---|
| `id` | string | unique id, e.g. `C1` |
| `name`, `aliases[]` | string | compared for identical or one-letter-apart names (S03) |
| `role` | string | `protagonist`, `antagonist`, `main` or your own; the first three count as main characters (S07) |
| `desire`, `fear`, `secret` | string | want and fear are required for anyone in two or more spine events (S05) |
| `relations[]` | `{to, kind}` | `to` is a character id |
| `introduced_in`, `exits_in` | integer | chapter numbers; nobody acts outside them (S02) |

## spine[]

| Field | Type | Meaning |
|---|---|---|
| `id` | string | unique id, e.g. `E1` |
| `t` | number | story time; causes must be earlier than effects (S02) |
| `title` | string | short name used on the page |
| `what_happened`, `so_what_changed` | string | two different sentences (S05) |
| `participants[]` | character ids | who was there |
| `place` | place id | where |
| `causes[]` | spine ids | earlier events this one follows from |
| `depends_on_rules[]` | rule ids | world rules the event needs (S08) |

## Command line

```
python3 scripts/story_check.py story.json [--max-open 5] [--strict] [--json OUT]
python3 scripts/bible.py story.json --out bible.html [--tokens design-tokens.css] [--max-open 5]
```

The page loads its design tokens from `assets/design-tokens.css` unless `--tokens` points elsewhere, and the
fonts from Google Fonts when online; it stays readable offline. Theme choice (Plaster, Paper or Ink; System,
Light or Dark) is saved in the browser under `nl-theme` and `nl-scheme`, or set with `?theme=` and `?scheme=`.

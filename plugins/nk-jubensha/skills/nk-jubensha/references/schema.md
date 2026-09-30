# game.json

One file holds the whole game. `assets/example/game.json` is a complete example; every field below appears in it.
Ids are short strings you choose (`C07`, `S5`, `WEN`); they must be unique across characters, NPCs, places, clues,
steps and red herrings. Text fields are plain text; line breaks (`\n`) are kept in the booklets.

```jsonc
{
  "schema": "nk-jubensha/1",
  "meta": {
    "title": "…", "players": 5,                 // players must equal the number of player characters
    "duration": "…", "difficulty": "…", "genre": "…",
    "premise": "…",                              // read aloud by the host; players see it
    "setting": "…", "warnings": ["…"],
    "lang": "zh"                                 // optional: "en" switches the booklet labels and the packet headings
  },
  "trick": {
    "family": "T3",                              // one of T1–T8 in trick-taxonomy.md
    "mechanism": "…",                            // free text; the taxonomy's letter (T3.b) is a good start
    "false_belief": "…", "how": "…", "why": "…", "trace": "…"   // all host-only
  },
  "places": [{"id": "P1", "name": "…", "desc": "…"}],        // players see names and descriptions
  "rounds": [{"n": 1, "title": "…", "say": "…"}],             // search and host clues name a round by n
  "characters": [{
    "id": "WEN", "name": "…", "player": true,
    "culprit": true,                             // exactly one player, the same as solution.culprit
    "intro": "…",                                // public, under sixty characters
    "sections": [{"act": 1, "share": "table" | "private", "title": "…", "text": "…"}],
    "goals": [{"id": "WEN-1", "kind": "find" | "hide" | "bond", "text": "…", "clues": ["C05"]}]
  }],
  "npcs": [{"id": "HE", "name": "…", "role": "victim", "note": "…"}],
  "clues": [{
    "id": "C07", "title": "…", "text": "…",
    "source": {"kind": "booklet", "holder": "SU", "act": 1}   // in that player's booklet, in that act
           // {"kind": "search", "place": "P2", "round": 1}   // a card found there in that round
           // {"kind": "host", "round": 2}                    // announced by the host
           // {"kind": "none"}                                // exists but nobody receives it (J02 will say so)
  }],
  "solution": {
    "culprit": "WEN", "victim": "HE",
    "summary": "…",                              // host-only; the detective prompt refuses to carry a run of it
    "steps": [{
      "id": "S7", "kind": "establish" | "explain" | "eliminate" | "break" | "implicate" | "motive" | "conclude",
      "claim": "…", "clues": ["C07", "C08"],
      "after": ["S1"],                           // steps this one needs first
      "target": "WEN",                           // for eliminate and implicate: who it is about
      "key": ["C07", "C08"]                      // optional: the clues that show a detective reached this step
    }],
    "alibi": {"holder": "WEN", "claim": "…", "step": "S7", "tokens": ["…"]},
    "herrings": [{"id": "H1", "points_to": "SU", "clues": ["C13"], "resolved_by": ["C28"], "note": "…"}],
    "secrets": ["…"]                             // phrases that give the answer away
  },
  "host": {
    "flow": [{"round": 1, "text": "…"}],
    "hints": [{"step": "S7", "text": "…"}],      // mild to strong
    "reveal": "…",
    "vote": [{"q": "…", "answer": "…"}],
    "endings": [{"when": "…", "text": "…"}]
  }
}
```

## What players see

| Field | Who sees it |
|---|---|
| `meta.title`, `premise`, `setting`, `warnings`, places, rounds | everyone |
| a character's `intro` | everyone |
| a character's `sections` with `share: "table"` | the character's player, who tells the table; the detective prompt carries them |
| a character's `sections` with `share: "private"` | only that player; never in the detective prompt |
| a character's `goals` | only that player |
| a clue with `source.kind: "booklet"` | its holder; the detective prompt carries it unless the holder is the culprit |
| a clue with `source.kind: "search"` or `"host"` | whoever finds it, or everyone; always in the detective prompt |
| `trick`, `solution`, `host` | the host only |

The culprit's `table` sections are the cover story: write them as what the culprit says, never as advice to the
culprit ("you can say it was about a raise" tells every reader that it is a lie). Put the advice in a private section.

## Steps, keys and the break

- `break` is the step where the culprit's cover gives way; `solution.alibi.step` names it. Its clues are the
  intended routes; give it at least two, held by different people.
- `alibi.tokens` are words that only the break clues carry. `chain_check.py` (J05) refuses them anywhere else a player
  reads, and requires each one in at least one break clue. Pick words specific to the observation, not common words.
- `implicate` and `conclude` steps that name the culprit must come after the break (J05): the answer should not be
  reachable around the trick.
- `key` is used only by `detective.py grade`: a step counts as reached when the detective cites one of its key clues
  (all of `clues` by default). Put the clues that show the step was understood, not the ones everyone cites.
- `eliminate` steps clear someone; if every innocent is cleared by steps that do not wait on a break or an implicate
  step, the game is solvable by elimination alone (J07). `explain` steps resolve a suspicious fact without clearing.

## Secrets

`solution.secrets` are phrases that state the answer or the trick: the culprit's name next to the deed, the name of
the method. `chain_check.py` (J06) refuses them in any page, card or announcement a player sees except the culprit's
private sections; `detective.py prompt` refuses a prompt that contains one. Declare several short ones in the words
the host would use.

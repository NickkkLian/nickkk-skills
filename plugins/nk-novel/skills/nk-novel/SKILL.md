---
name: nk-novel
description: Turn one story idea into a staged novel plan that holds together, plus a one-page visual story bible. Stages - premise and one-sentence retelling, world rules and what each costs, characters (want, fear, secret, relations), an event spine where every event says what happened and what changed because of it, acts and beats, clues planted and paid off, and a chapter outline. Ships a checker for timeline contradictions, confusable names, clues never paid off, missing motivation and reader load. Use when someone has an idea for a novel, serial, game story or screenplay and wants a plan instead of a blank page; when an outline keeps being rewritten and nobody can say what broke; or when an AI says a plot is clear and a human reader says they cannot follow it. Not for polishing prose.
license: MIT
metadata:
  provenance: the author's own reviews of AI-drafted story plans over dozens of rounds in 2026 (private project, not included); example story written for this skill
---

# Novel plan

An idea becomes a plan in eight stages, written into one `story.json`. Each stage ends on a question that has to
be answered before the next one starts, and the plan is checked by a script before anyone reads it: references,
timeline, names, clues, motivation, reader load. The last stage turns the plan into a single HTML page, the
story bible, that a collaborator can read in a few minutes.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## When this applies

- Someone has one sentence, a premise or a "what if", and wants to know whether it can carry a book.
- An outline has been rewritten several times and each version is safer and smaller than the last.
- An agent reports that a plot is clear, and a person who read it says they did not follow it.
- Not for line editing or prose style, and not for games whose players hold the clues (party mystery games).

## Procedure

Write each stage into `story.json` (field names in [references/schema.md](references/schema.md); a complete
example is `assets/example-story.json`). Do the stages in order; go back when a later stage breaks an earlier one.

1. **Premise and retelling.** Write the idea, the genre, and the whole story as one sentence a stranger could
   repeat. If the sentence needs words like "in the story within the story" or "the second timeline", the
   reader will be holding too many layers; simplify before building anything on it.
2. **World and its costs.** Every rule the story leans on gets a cost (what using it takes away) and the world
   gets a short list of what it does not allow. Write the caps too: how many main characters, how many places.
   A cap that is not written is no cap, and the plan will grow until it is unreadable.
3. **Characters.** Each gets a want, a fear, and a secret if they have one, plus relations and the chapter they
   enter and leave. Anyone who drives two or more events must have both a want and a fear.
4. **Event spine.** List the events that make the story. Each has "what happened" and "so what changed", two
   different sentences, plus who was there, where, what caused it and which world rule it needs. The core of a
   story is an event, not an object: objects are what events leave behind. Then run the removal test: imagine
   the world rule is gone and ask what is left. It **passes** when the people still want and fear the same
   things and what changes between them still matters; the rule only decided how it happens. It **fails** when
   nothing is left, because the events existed to show the rule off: that story is wrapping paper for a
   mechanic, and it gets rebuilt, not polished. Collapse is the failing result. A premise built on a rule
   ("the ships she guides in arrive from next year") still has to pass: the plot may need the rule, the story may not.
5. **Structure.** Group the events into acts and name the beats (inciting incident, midpoint, climax, or your
   own). Every beat points at spine events; a beat with nothing under it is a promise with no scene.
6. **Consequences.** Put a time on every event; causes come before effects; nobody acts before they enter or
   after they leave. Plant clues and pay them off, or mark one as left open on purpose. Open questions get the
   chapter that opens and the chapter that answers them.
7. **Chapters.** Each chapter tells one or more spine events from one point of view. Every spine event is told
   somewhere.
8. **Check and render.** Run the checker, fix every error, read every warning as a question rather than a rule,
   then render the story bible and read it the way a stranger would:
   `python3 <skill-dir>/scripts/story_check.py story.json`
   `python3 <skill-dir>/scripts/bible.py story.json --out bible.html`

## Iterating without shrinking the story

The judgments behind these stages, with the failures that produced them, are in
[references/method.md](references/method.md). Four of them decide how revision rounds go:

- **A correction belongs to the version it corrects.** Before the next round, go through last round's rules
  and retract them by default; keep one only with a reason. When a brief holds more than three to five
  "never / must / only", it describes a safe corner, not a story.
- **Two versions in a row got smaller:** remove rules, do not add one.
- **Every sentence in a brief to an agent is a design input.** Ask what the laziest way to satisfy it would
  be; "make the other side visible" is easiest to satisfy by adding a new character.
- **The objective is whether a reader wants to keep reading.** The checks run after that question, not
  instead of it. A person saying "I don't follow" overrides a clean report.

## The checks

| Code | Kind | What it catches |
|---|---|---|
| S01 | error | an id used twice; a reference to a character, place, event, rule or chapter that does not exist; a spine event no chapter tells |
| S02 | error | an effect before its cause; a character acting before they enter or after they leave |
| S03 | error | two characters with the same name or alias, or names one letter apart |
| S04 | error | a clue paid off before it is planted, or never paid off and not marked as left open |
| S05 | error | an event without "what happened" or "so what changed", or the two saying the same thing; a character in two or more events without a want or a fear |
| S06 | warning | more open questions and unpaid clues after a chapter than `--max-open` (5 by default, a starting value to tune); a missing or multi-sentence retelling |
| S07 | warning | no caps written for main characters and places, or caps exceeded |
| S08 | warning | every spine event depends on the same world rule: a hint that the story may fail the removal test |

Exit 0 clean (warnings allowed), 1 errors (or warnings with `--strict`), 2 unreadable file or failed self-test.
`--json OUT` writes the findings for another tool. The story bible page embeds the same findings.

## Boundaries

- The checks read structure, not quality: a plan with zero findings can still be dull, and a strange plan can
  be the right one.
- Reader load is approximated by counting open questions and unpaid clues; it is a prompt to reread, not a
  measurement of a reader.
- The retelling test catches meta-layers only if the retelling is honest; an agent can always write a
  sentence that sounds simple.
- The plan is the author's. The stages ask questions; they do not decide what the story is about.

## Provenance

- The stages and the four revision rules come from the author's own reviews of story plans drafted with AI
  agents in 2026, over dozens of rounds on one private project (not included). Each came from a round where
  every written criterion passed and a human still said the result did not work: a core built around an
  object with nothing happening; a plot hung on a game mechanic; a story an agent retold in three sentences
  and a person could not follow; rules added every round until each version was smaller than the last.
- Checks S01–S08 were written for this skill; each was broken on purpose to confirm its self-test goes red.
- The example story, "The Next-Year Light", was written for this skill.

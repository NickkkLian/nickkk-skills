# Method

The craft behind the nine stages in SKILL.md. A jubensha is not a novel cut into five parts: it is five incomplete
accounts, each worth reading alone, and a set of rules that makes them fit together at a table.

## The shape of an evening

| Phase | What happens | What the writer owes it |
|---|---|---|
| Read | Everyone reads act 1 of their own booklet, silently | Booklets that read in 15–25 minutes; a clear first-person evening |
| Introductions | Each player says who they are | A public intro and a table page per character |
| Search 1 | Each player searches alone, no talking | Cards that raise questions; nothing that closes the case |
| Act 2 | Everyone reads their act 2 | New memories that change what the cards mean |
| Search 2 | Private talks, trades, public reveals | Clues that only matter when combined, and secrets worth trading |
| Final talk and vote | The table argues and votes | A solvable chain, a vote that asks more than "who" |
| Reveal | The host reads the truth | A reveal that pays off every thread, including the innocents' lies |

Two search rounds of different kinds are the form's own rhythm: the first isolates people, the second makes them
negotiate. Write clues for each: round-1 cards should make people suspicious of each other; round-2 cards should reward
putting two things together.

## Roles

- Every role gets three kinds of goals: **find** (something to learn), **hide** (something to keep), **bond**
  (someone to protect, win over or settle with). A player who is bad at deduction still has an evening if they have
  a secret to protect and a person to fight for.
- Every innocent lies about something unrelated to the murder. A table where only the culprit lies is solved by
  finding the liar. The lies should collapse under a search card, so exposing them is play, not a dead end.
- The culprit's fun is not winning; it is almost getting away with it. Give the culprit concrete goals (what to steer
  people towards, what to keep people away from), a cover story written as what they will say, and a human reason
  the reveal can land on.
- Count what each role has to do: goals, clues they hold that the chain needs, suspicion pointing at them. The
  quietest role should have at least half of what the busiest has (`chain_check.py` J10 warns below that).

## Booklets

- Second person, present stakes, short paragraphs. Players read against a clock; long description is a cost.
- One act per round. Act 2 changes the meaning of something from act 1 rather than adding a new thread.
- Mark every page *table* or *private*. A table page is what the character will say, lies included; a private page is
  what only they know. The culprit's private page is the only place the whole truth appears.
- A clue held in a booklet is written as something the character saw or knows, in their words, without knowing what
  it means. The observation that breaks the cover belongs with an innocent who noticed it and shrugged.

## Clues

- A good clue does two jobs: it serves one step and misleads or informs another. A clue that only restates the
  setting is wasted table space.
- Surface and meaning differ: the card should look like it is about one thing and turn out to be about another.
- Every step of the solution cites its clues. If a step cannot name a clue, the step is the writer's knowledge, not
  the players'. `chain_check.py` J02 finds these.
- The clue that raises a suspicion and the clue that proves it should be different clues. Players are allowed to
  suspect early; the proof should need the trick.
- Give the key step two routes held by different players. People forget, people hide things, and a game that ends
  when one player stays quiet is fragile (J11 warns).
- Decide what you withhold on purpose and write down why. A fact that is simply missing is a hole; a fact withheld
  for a reason is design.

## Red herrings

- A red herring is an innocent person's real secret, not a false clue from nowhere. Its resolution must reach the
  table (J04): a card, a witness, or the person's own account backed by a card.
- Suspicion is something to do. The framed player gets material to defend themselves with.

## The trick

- Choose it from `trick-taxonomy.md` after the cast exists, so it solves a problem this culprit has.
- Write the false belief in one sentence, the trace in one sentence, and the principle that makes the trace mean
  something in the words of the character whose trade it is.
- Ask the blind detective, not yourself, whether the trick is load-bearing: remove the break clues and run it again.
  If the detective still convicts the culprit with evidence, the cover breaks another way, and the trick is
  decoration. Move or weaken the other route.

## Host handbook

- The truth in one paragraph, the trick, the flow per round (what to hand out and when), where every clue is, the
  solution chain, the herrings and their resolutions, hints from mild to strong, the reveal, the vote and endings.
- Hints point at questions, not answers: "ask everyone what they were doing when the lights dipped".
- The vote can ask more than "who": how it was done, and one question with no right answer that lets the evening end
  on the characters.

## Playtesting

- The blind detective tests sufficiency: is the information there, and does the cover break only where intended.
- People test everything else: pacing, whether the booklets are fun, whether anyone was idle. Test with at least one
  table of new players; experienced players find everything too easy.

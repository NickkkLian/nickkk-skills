# Method — why the stages ask what they ask

Each judgment below came from a revision round where a plan passed every written criterion and a person
still said it did not work. The examples use the sample story in `assets/example-story.json`, "The Next-Year
Light": a lighthouse keeper realises the ships she guides in arrive from next year.

## 1. The core is an event, not an object

Ask first: **what happened, and so what is different now?** If the answer is a thing (a letter, a map, a
lantern), the story has a prop and no core yet. Events leave objects behind; decide the object last.

- Weak: "The story is about a lighthouse lamp that shows the future."
- Holds: "A ship docks with next year's newspapers, so Maren knows the storm is coming."

That is why every spine event has two fields, `what_happened` and `so_what_changed`, and why the checker
flags them when they are missing or say the same thing (S05).

## 2. Remove the mechanic: does the story still stand?

A world rule, a game mechanic or a clever device is background. Take it away in your head: if a scene loses
its way of happening but the characters still want and fear the same things, the rule was serving the story.
If everything collapses, the story was built to show off the rule; it is wrapping paper. Collapse is the
failing result, never the passing one. A high-concept premise does not get an exemption: the plot may depend on
the rule, but who wants what, who fears what and what changes between them must survive without it.

In the sample, E1 and E4 depend on the fog-light rule, E2 and E3 do not: the town calling Maren a liar and
Tobias finding his name on a list would still be a story about trust and a brother. The checker warns only when
every event hangs on one rule (S08). It cannot tell a good dependency from a bad one; you can.

Finding the rule in your notes proves only that it is allowed, not that it deserves to carry the plot.

## 3. Readability is the number of layers a reader has to hold

An agent can retell almost anything; it reads the whole text at once with unlimited patience. A person reading
page by page cannot. Count the things a reader must keep in mind, each depending on the others, before they can
see what happened. More than two is a warning sign.

- Write the whole story as one sentence first (`retelling`). If the sentence cannot avoid words like "the
  story within the story", "the other timeline" or "who was playing whom", it has too many layers.
- Open questions and unpaid clues are layers too. The checker counts them after every chapter (S06). The
  default limit of five is a starting value to tune per genre, not a measured human limit.
- A person who says "I don't follow" overrides every report that says the plot is clear.

## 4. A cap that is not written is no cap

A plan grows by its easiest moves: a new character, a new place, a new kingdom. None of them is wrong alone;
together they bury the story. Write the caps (`caps.main_characters`, `caps.places`) before the world is built.
The checker warns when they are missing or exceeded (S07).

When you brief another agent, each sentence is an instruction it will satisfy the cheapest way. "Tobias should
feel more real" is cheapest to satisfy by giving him a new friend, a pet and a backstory. Ask of each sentence:
what is the laziest way to do this? If you do not want that, say so.

## 5. Rules accumulate into overfitting

Each round, a reviewer spots one flaw and adds a rule against it. Rules are never removed. After a dozen rounds
the plan satisfies every rule and nobody wants to read it: each version is more careful and smaller than the
last.

- A correction belongs to the version it corrects. Before the next round, retract last round's rules by
  default; keep a rule only with a reason written next to it.
- Separate the few things that really are fixed (the world's base rules, the protagonist, the red lines) from
  "what we currently think". Mark the second group as open to change.
- More than three to five "never / must / only" in a brief: stop and cut.
- Two versions in a row got smaller: the space was drawn too small. Remove rules; do not add one.
- There is one objective: does the reader want to keep reading. Checks run after that, never instead of it.

## 6. Build downward from the settled world, never re-found it

New concrete things are what planning is for: an object, a place, an event that follows from the world as it is.
Re-writing the world's base rules to make a scene work is different; that is starting another story. When
someone asks "why is there a new setting?", first check which one happened: a thing derived from the rules
(fine), or a changed rule (not fine).

## 7. Short questions are usually checks, not bans

"Why is there a new character?" often means "did you intend this?", not "never add characters". Answer the
question that was asked, then decide whether the plan changes. Turning every question into a permanent rule is
how rule piles start (5).

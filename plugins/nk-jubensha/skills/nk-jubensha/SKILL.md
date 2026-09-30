---
name: nk-jubensha
description: Build a playable jubensha (剧本杀, the Chinese murder-mystery party game) from a premise - a cast, a trick chosen from an abstract taxonomy, a clue chain in which every deduction stands on a clue some player actually receives, and printable HTML booklets (one per player, clue cards, a host handbook). Then a second model that never saw the solution plays detective on the players' material only, and the game is graded "solved in N steps", "right name, cover not broken", "wrong" or "unsolvable - clue X missing"; the chain is fixed and re-checked with a fresh detective until it is solved. chain_check.py catches unsupported steps, orphan clues, dead ends, a cover that breaks the wrong way, leaks into booklets, culprits found by elimination alone and roles with nothing to do. Use when someone wants a murder-mystery party game, a 剧本杀 or a whodunit for a group, when a mystery plot needs proof that players can solve it, or when a game's clue chain needs an outside test. Not for novels or escape rooms.
license: MIT
metadata:
  provenance: written for this skill (2026-09) from the author's notes on mystery and party-game design (private, not included); the trick taxonomy is abstract and reproduces no published script or novel; example game written for this skill and verified by the detective loop
  version: 0.1.0
---

# Jubensha builder

A premise becomes a game a group can sit down and play: five or six characters, each with a booklet that is fun to
read alone and incomplete on purpose; a trick; clue cards for two search rounds; a host handbook. Everything lives in
one `game.json`. A script checks the structure, a renderer prints the booklets, and then the part a writer cannot do
for themselves: **a second model that never saw the solution plays detective on exactly what the players get**, and
says whether it solved the case, and if not, which clue it was missing.

> **Paths.** Commands in this skill start with `<skill-dir>`: this skill's own folder, the one that contains this SKILL.md. Replace it with that folder's absolute path before you run the command.

## 中文快速上手

- 第一步，给一个前提：时代、地点、几个人、大概的气氛。例：「民国电台，五人本，一个晚上」。
- 第二步，按下面九步把剧本写进 `game.json`（字段见 [references/schema.md](references/schema.md)，完整样例是
  `assets/example/game.json`，《九点半的声音》）。诡计从 [references/trick-taxonomy.md](references/trick-taxonomy.md) 里挑。
- 第三步，跑检查：`python3 <skill-dir>/scripts/chain_check.py game.json`，错误清零。
- 第四步，出本子：`python3 <skill-dir>/scripts/booklets.py game.json --out booklets/`，每人一份人物本、线索卡、主持人手册。
- 第五步，盲测：`python3 <skill-dir>/scripts/detective.py prompt game.json --out prompt.md`，再用
  `detective.py run --engine claude`（或 `--engine codex`）开一个没看过答案的新会话当侦探，最后用 `detective.py grade` 打分。
  侦探的回答原样保存，不许代写、不许删改；跑不起新会话就停下来如实说明，不许报结果。没解开就按报告补线索，换一个新的侦探重测，直到 SOLVED。

样例游戏是中文的；游戏语言跟着前提走（`meta.lang` 设为 `en` 就出英文本子）。本 skill 的说明文档是英文。

## When this applies

- Someone wants a murder-mystery party game for a group: a 剧本杀, a whodunit night, a mystery for a club or a class.
- A mystery plot exists and nobody knows whether players can actually solve it from what they are given.
- A game has been playtested and a table got stuck, guessed, or accused the wrong person, and nobody can say why.
- Not for a novel (the reader does not hold clues), not for an escape room (puzzles, not suspects), not for a live
  roleplay with no fixed solution.

## Procedure

Write each stage into `game.json` (field names in [references/schema.md](references/schema.md); the complete example
is `assets/example/game.json`). Do the stages in order; go back when a later stage breaks an earlier one. The craft
behind the stages is in [references/method.md](references/method.md).

1. **Premise and scale.** Era, place, the one evening, player count (five or six is the common table), length (two
   to four hours), difficulty, content warnings. Write the premise as the two sentences the host will read aloud.
   Talk to the person in the language they wrote in; the game's text follows the premise.
2. **Cast.** Every player character gets a public intro under sixty characters, a secret, and goals of three kinds:
   *find* (something to learn), *hide* (something to keep), *bond* (someone to protect, win or settle with). The
   culprit is a player with a cover story and at least one *hide* goal; every innocent has a *find* goal. A victim and
   any witnesses are non-player characters.
3. **Trick.** Choose one family and mechanism from [references/trick-taxonomy.md](references/trick-taxonomy.md). Write
   the false belief it creates, how it is done, why this culprit needs it here, and the trace it cannot avoid leaving.
   If a simpler plan would have worked for the culprit, fix the story until it would not.
4. **Truth.** The minute-by-minute timeline of what really happened, for every character, including the innocents'
   own lies (a table where only the culprit lies is solved by spotting the liar).
5. **Clue chain.** Write the solution as steps: establish, explain, break (the step where the culprit's cover gives
   way), implicate, motive, conclude. Every step cites clue ids. Give the break two routes held by different people;
   put the observation that breaks the cover with an innocent who noticed it without understanding it, and the
   principle that makes it meaningful with someone else. Every red herring gets its own innocent truth and a clue
   that resolves it. Declare the break tokens (words only the break clues carry) and the solution secrets (phrases
   that would give the answer away) so the checks can find leaks.
6. **Booklets.** Split each character's pages into acts that match the rounds, and mark each page *table* (what they
   will say) or *private* (what only they know). Write in the second person. Place each booklet clue with its holder.
7. **Check.** `python3 <skill-dir>/scripts/chain_check.py game.json`. Fix every error; read warnings as
   questions. Exit 0 clean, 1 errors, 2 unreadable file.
8. **Render.** `python3 <skill-dir>/scripts/booklets.py game.json --out booklets/` writes `index.html`, one
   `<id>.html` per player, `clues.html` and `host.html`: single files, no outside requests, printable on A4.
9. **Play it blind.** Run the detective loop below until the grade is SOLVED. Then have people play it; a person
   saying "we were lost" overrides a clean grade.

## The blind detective

The detective sees what a table would have on it after both search rounds: every character's *table* pages (private
pages stay out, and the culprit contributes only the cover story), the search cards, the host's announcements, and
the clues innocent players hold. The culprit's clues and goals, the trick, the solution and the host text stay out.

1. Build the prompt: `python3 <skill-dir>/scripts/detective.py prompt game.json --out prompt.md`. It refuses
   (exit 1) if the prompt would contain a declared solution phrase, a run of the solution summary or of the trick's
   how, or a run of private text that no table page carries.
2. Hand it to a model that never saw the solution, in a fresh context, and keep the record.
   - **Recorded (use this first, from either agent):** `python3 <skill-dir>/scripts/detective.py run --engine claude --prompt prompt.md --out run-1`
     starts `claude -p` in an empty temporary folder with every tool switched off; `--engine codex` starts `codex exec`
     read-only, with no user config and no saved session (from inside Codex, this is the second session). `run`
     writes `transcript.jsonl`, `answer.txt` and `run.json` (command, version, seconds, tool calls or commands; it
     should say zero). Pass `--model` to choose the model. If the command line is not on your PATH (the Codex CLI
     that ships inside the ChatGPT app is not), set `CLAUDE_BIN` or `CODEX_BIN` to its full path; without it
     `run.json` says `"exit": "not started"`.
   - **Subagent (only when no command line can run):** in Claude Code, a subagent whose whole prompt is the text of
     `prompt.md` plus one line: "Answer from this message only; do not read files or run commands." Do not give it the
     path of `game.json`, and do not use a session that has seen the solution. Its answer has no run record, so its
     grade is marked UNVERIFIED; say so when you report it.
   - **Rules that do not bend.** Never write, shorten, translate or tidy the detective's answer: save it exactly as it
     came back, or let `run` save it. Never answer as the detective yourself, and never let the session that wrote the
     game do it: you know the solution. If no second session can run, stop and tell the person the blind test did not
     run and why; do not report a result, and do not change the game to fit the grader.
3. Grade: `python3 <skill-dir>/scripts/detective.py grade game.json run-1/answer.txt > run-1/grade.txt`. The first line is the verdict:
   - **SOLVED in N steps**: right culprit, and the chain cites at least one of the break step's key clues.
   - **RIGHT NAME, COVER NOT BROKEN**: right culprit reached by elimination or a guess. Treat as not solved.
   - **WRONG**: someone else accused. **UNSOLVABLE**: the detective said the material is not enough.
   Every verdict but SOLVED lists the solution steps nobody reached and the clues that carry them, with who holds
   each: "unsolvable: clue C07 missing". Citations of clue ids that are not on the table are flagged (a leak or an
   invention). The grade also says where the answer came from: it is verified only when `run.json` and
   `transcript.jsonl` from `run` sit beside it, the answer is the transcript's last message word for word, and the
   session made no tool calls; otherwise the first line starts with `UNVERIFIED (…) · as graded:`, and that word
   goes into whatever you report. Exit 0 means SOLVED and verified, 3 SOLVED but unverified, 1 any other verdict.
4. Fix, then re-check with a **new** detective (never the same session: it has learned). Typical fixes: move a fact
   from a private page or the culprit's hands into a clue an innocent receives; say plainly in a clue what the step
   needs; add a second route to the break; resolve the herring that took the detective the wrong way. Re-run
   `chain_check.py`, re-render, re-grade. After three failed rounds, stop and show the person the grades.
5. Keep every run folder. The example keeps its runs in `assets/example/detective/`.

## The checks

| Code | Kind | What it catches |
|---|---|---|
| J01 | error | duplicate ids, references to things that do not exist, not exactly one culprit, a culprit who is not a player, a wrong player count, steps waiting on each other in a circle |
| J02 | error | a step with no clue, or a step that needs a clue no player receives ("unsolvable: clue X missing") |
| J03 | error | an orphan clue that no step, red herring or goal uses |
| J04 | error | a dead end: a red herring nothing resolves, or resolved only by a clue nobody receives |
| J05 | error | the cover breaks another way: a break token outside the break clues, a token the break clues do not carry, a break clue only the culprit holds, a step naming the culprit that skips the break |
| J06 | error | a declared solution phrase in any page, card or announcement a player sees (the culprit's private pages excepted), or no phrase declared |
| J07 | error | solvable by elimination alone (every innocent cleared without the proof against the culprit), or no positive proof |
| J08 | error | a step that stands only on clues in the culprit's own booklet |
| J09 | error | a role with no goal, no secret, nothing to tell, a culprit with nothing to hide, an innocent with nothing to find, or a player the chain never needs |
| J10 | warning | the busiest role has more than twice the hooks of the quietest (a starting ratio to tune) |
| J11 | warning | a step every clue of which sits in one innocent's booklet |
| J12 | error | a trick family outside the taxonomy, or no false belief, how, why or trace written |
| J13 | warning | a run of host-only text (the solution summary, the trick's how) repeated word for word in player text |

`--json OUT` writes the findings for another tool; `host.html` embeds them. `booklets.py --runs run-1 run-2` adds each
run's verdict to the host handbook.

## Boundaries

- The checks read structure, not prose. A clue can be cited by the right step and still fail to say what the step
  needs; that is what the blind detective is for, and a clean check is not a good game.
- The detective is a model, not a table of people. It reads every page at once and never forgets; people talk over
  each other, hide things and get tired. SOLVED means the information is sufficient, not that a group will find it in
  three hours. Play it with people before calling it done.
- The grade matches clue ids, not reasoning. A detective can cite the right clue for the wrong reason; read its chain.
- Blindness is by construction and on record, not enforced: the Claude route runs with no tools, the Codex route runs
  read-only and its transcript lists every command. A subagent could still read files if told where they are, so do
  not tell it.
- `claude -p` loads your own user-level settings and CLAUDE.md. They know nothing about the game, but if they change
  how the detective answers, point `CLAUDE_CONFIG_DIR` at a clean, signed-in config, as the example's runs did
  (`--bare` would skip them too, but accepts only an API key).
- A nested `codex exec` does not start inside Codex's own sandbox: in testing it stopped with "failed to initialize
  in-process app-server client: Operation not permitted" even with network access on. From inside Codex, run the
  `run` command in a terminal, or approve running it outside the sandbox; a `claude -p` run needs a signed-in Claude
  Code. Without either, the only route left is a subagent, and its grade stays UNVERIFIED.
- The taxonomy is a map for choosing, not a source of finished tricks. It names mechanisms, not works.

## Provenance

- The stages, the checks and the detective loop were written for this skill in 2026-09, from the author's own notes
  on mystery and party-game design (private, not included). The fairness conditions restate the old fair-play rule of
  detective fiction (everything the solution needs is shown before the answer) for a table where every player is a
  suspect and the culprit holds cards of their own.
- The blind detective comes from the author's practice of having someone who did not do the work judge the evidence
  (see nk-evidence-audit): a writer who knows the answer cannot test whether the clues are enough.
- The rules about the detective's answer, and the grade's run-record check, came from testing this skill in clean
  sessions: one agent condensed its detectives' answers before grading them, and another, whose command-line session
  failed to start, wrote the answers into files itself and reported a blind result.
- The trick taxonomy is abstract and written for this skill. It contains no text, titles, plots or characters from
  any published script or novel, or from the material behind the author's notes.
- The example game, 《九点半的声音》, was written for this skill. Its detective runs, including a planted break with
  the key clues removed, are in `assets/example/detective/`.
- Checks J01–J13 each have a sample only they catch, and each rule line was broken on purpose to confirm the self-test
  goes red.

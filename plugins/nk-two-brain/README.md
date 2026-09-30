# nk-two-brain (Codex plugin)

Run a coding task through two different AI agents with proof at the end: Claude writes a handoff package (goal, boundaries as orders, what the builder cannot see, acceptance checks kept from the builder), OpenAI Codex builds it in a fresh clone, the acceptor re-runs its own checks (including one with the code broken on purpose), a separate model run that did no building judges each claim from the evidence alone with exactly three verdicts (supported, not supported, insufficient), and a post draft is written from the run's files.

Generated copy of [NickkkLian/nk-two-brain](https://github.com/NickkkLian/nk-two-brain) in the plugin layout OpenAI Codex reads (`skills/nk-two-brain/SKILL.md`). The skill's README, compatibility notes and history are in that repository. Install: `codex plugin marketplace add NickkkLian/nickkk-skills` then `codex plugin add nk-two-brain@nickkk-skills`.

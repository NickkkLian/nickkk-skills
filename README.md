# nickkk-skills

Skills for Claude Code that stop an AI coding agent's "done, tested, safe" from being taken on faith:
evidence bundles, breakable checks, guardrails, memory and handoff discipline.

Each skill lives in its own repository (one folder: `SKILL.md`, stdlib-only Python scripts with a
`--selftest`, references written from incidents that actually happened). This repository is the directory,
the plugin marketplace, and the home of the shared lint.

| Skill | What it does |
|---|---|
| [nk-evidence-audit](https://github.com/NickkkLian/nk-evidence-audit) | Turn "done, fixed, tested" into evidence a second agent judges. |
| [nk-git-guardrail-hook](https://github.com/NickkkLian/nk-git-guardrail-hook) | A PreToolUse hook for Claude Code that stops before the git and shell commands that have actually destroyed work — force push, git add -A in a shared checkout, making a repo public, pushing while behind the remote, a push that records a mass deletion, rm -rf on a project root, curl piped into a shell — and names the incident in the prompt. |
| [nk-publish-gate](https://github.com/NickkkLian/nk-publish-gate) | Privacy and secret gate to run before anything goes public — a repo, a release zip, a demo folder, a PDF. |
| [nk-indent-guard](https://github.com/NickkkLian/nk-indent-guard) | Stop a one-line edit to a JSON or YAML data file from re-indenting the whole file and burying the real change in a 400-line diff. |
| [nk-breakable-selftest](https://github.com/NickkkLian/nk-breakable-selftest) | Make a checker, validator, linter, gate or test suite prove it can fail. |
| [nk-memory-with-conditions](https://github.com/NickkkLian/nk-memory-with-conditions) | Write agent memories that say when they hold, and keep the memory directory honest. |
| [nk-rules-that-land](https://github.com/NickkkLian/nk-rules-that-land) | Write rules for an AI agent that actually change what it does. |
| [nk-regression-baseline](https://github.com/NickkkLian/nk-regression-baseline) | Freeze the byte-exact output of production code on its default inputs before you change it, and compare after. |
| [nk-rewrite-coverage](https://github.com/NickkkLian/nk-rewrite-coverage) | After rewriting a long document — a spec, a research report, a handbook — list what the old version had that the new one no longer mentions, and account for every item with a three-state verdict before the rewrite is accepted. |
| [nk-handoff-package](https://github.com/NickkkLian/nk-handoff-package) | Hand a line of work to an executor that has no context — another agent, a contractor, a future session — so that the work comes back checkable. |

## Install

**One skill** — clone its repository into your skills directory:

```bash
git clone https://github.com/NickkkLian/nk-evidence-audit ~/.claude/skills/nk-evidence-audit
```

(or into `.claude/skills/` inside a project). Each skill's README has the same two lines.

**As plugins** — add this repository as a marketplace, then install what you want:

```
/plugin marketplace add NickkkLian/nickkk-skills
/plugin install nk-evidence-audit@nickkk-skills
```

Installed plugins appear as `/nk-<skill>:nk-<skill>`. To try one for a session: `claude --plugin-dir ./nk-<skill>`.

## Tools

`tools/skill_lint.py <skill-dir>` checks a skill folder the way these were checked before publishing:
frontmatter, name = folder, description length and a "when to use" clause, body length, a Provenance section,
scripts referenced through `${CLAUDE_SKILL_DIR}`, every script with a `--selftest`, no local paths.
It has its own `--selftest`.

## How these were built

- Every rule cites an incident; nothing was added for an imagined risk.
- Every checker's self-test shares the production code path and was broken on purpose to prove it reacts.
- Detectors fail loud; the guardrail hook fails open.
- Every repository went through the publish-gate skill (tree and full history) before its first push.

## License

MIT.

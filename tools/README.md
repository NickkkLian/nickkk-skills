# tools

`skill_lint.py` — structural lint for a skill folder (`python3 skill_lint.py <dir>`; `--selftest`). Stdlib only.
For a skill under a Codex plugin's `skills/` directory, identified by the plugin's `.codex-plugin/plugin.json`,
L07 expects `<skill-dir>/scripts/`; for other layouts it expects `${CLAUDE_SKILL_DIR}/scripts/`. Both require
referenced scripts to exist and shipped scripts, including helpers, to be referenced. Claude variable uses also
require the L12 path note. Run `python3 tools/skill_lint.py plugins/*/skills/*` from the repository root to check
all plugin copies. CI runs that command and the lint self-test.

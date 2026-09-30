# Other agents

Where these skills stand outside Claude Code. A platform gets an install line in the README only after a real
install test in a throwaway home directory; the others are listed here with what their documentation says.

| Agent | Status | Install |
|---|---|---|
| OpenAI Codex CLI | Tested 2026-09-29 (codex-cli 0.159.0, macOS): marketplace add, install of all 17 plugins, and the skills appear in `codex debug prompt-input`. No model run was made for this route. | See "Install in OpenAI Codex (plugin marketplace)" in the [README](../README.md). |
| Grok CLI | Not tested: Grok CLI was not installed on the test machine. | xAI's documentation says Grok reads Claude Code marketplaces, plugins and skills with no extra setup, and discovers user-level skills in `~/.agents/skills/`. Neither was tried. |
| Gemini CLI | Not tested: Gemini CLI was not installed on the test machine. | The extension gallery lists public repositories that carry the `gemini-cli-extension` topic and a `gemini-extension.json` at the root. This repository has neither yet, because the extension has not been installed and run once. Each skill's README notes that Gemini CLI reads `~/.agents/skills`, the folder its Codex clone route uses; that was not tried either. |

`nk-git-guardrail-hook` is not in the Codex marketplace: it is a Claude Code PreToolUse hook and has not been
adapted to the Codex hook runtime.

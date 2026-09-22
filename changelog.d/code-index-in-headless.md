MINOR

**Every tool the factory gives a project now reaches a headless `/cruise` iteration, the code index included.**
A run in a fresh checkout kept `check-codegraph` green with `codegraph sync` and answered every *who calls this*
with grep, because the only thing that connected an agent to the index was the user-level config CodeGraph's own
installer writes on the one machine `./init` ran on — nothing a container, a CI runner or the runner's fresh session
ever sees. Three things change. `./init --extension codegraph` (and `slipwai migrate`, `make agents` or a later
`./init --integration <agent>`, for a project that adopted it earlier) names the server, started through `npx`
so the connection is true wherever Node is, in the project-scoped MCP file of every harness installed here and
commits it: `.mcp.json` for Claude Code, `.codex/config.toml` for Codex, `.gemini/settings.json` for Gemini CLI,
`.cursor/mcp.json` for Cursor, `opencode.json` for opencode, `.kiro/settings/mcp.json` for Kiro — the registry's
new `projectMcp` column, each read from the harness's own documentation and dated, null with a reason for the
thirty harnesses nobody has checked, which reach the index through the CLI from the shell. Every file is a merge
target, so a server a person added stays. Every project's `.claude/settings.json` approves that server and allows
its tools, inert until the file exists. And the runner passes each row's `headlessFlags` whenever the file exists —
`--mcp-config .mcp.json` on Claude Code, whose print session in a checkout nobody has trusted ignores the
project's settings and the servers they approve (its hooks still run); a one-run trust override on Codex, which
skips every project `.codex/` layer in an untrusted project — while the Claude Code row names every tool family
the ladder reaches for in `--allowedTools` — `Bash`, `Skill`, `Agent`, `WebFetch`, `WebSearch`,
`mcp__codegraph__*` — each tried from a print session first. What an iteration needs travels on its command line. The runner says before the first iteration how the index will be
reached, or that it cannot be, and `status` says afterwards in how many iterations it was asked, so an index kept
fresh and never queried is seen rather than suspected; an index call is one line of the feed like any command.

**Catch-up.** `slipwai migrate` writes each installed harness's project MCP file where `codegraph` was adopted,
the settings entries, the registry column and the runner; commit the new files.

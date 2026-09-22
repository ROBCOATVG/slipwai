MINOR

**Every tool the factory gives a project now reaches a headless `/cruise` iteration, the code index included.**
A run in a fresh checkout kept `check-codegraph` green with `codegraph sync` and answered every *who calls this*
with grep, because the only thing that connected an agent to the index was the user-level config CodeGraph's own
installer writes on the one machine `./init` ran on — nothing a container, a CI runner or the runner's fresh session
ever sees. Three things change. `./init --extension codegraph` (and `slipwai migrate` or `make agents`, for a
project that adopted it earlier) writes and commits `.mcp.json`, the project-scoped file Claude Code reads, with
the server started through `npx` so the connection is true wherever Node is; the file is a merge target, so a
server a person added stays. Every project's `.claude/settings.json` approves that server and allows its tools,
inert until the file exists. And the registry's Claude Code row passes the file with `--mcp-config` whenever it
exists and names every tool family the ladder reaches for in `--allowedTools` — `Bash`, `Skill`, `Agent`,
`WebFetch`, `WebSearch`, `mcp__codegraph__*` — each tried from a print session first: a checkout nobody has
trusted ignores the project's allow rules and the servers its settings approve (its hooks still run), so what an
iteration needs travels on its command line. The runner says before the first iteration how the index will be
reached, or that it cannot be, and `status` says afterwards in how many iterations it was asked, so an index kept
fresh and never queried is seen rather than suspected; an index call is one line of the feed like any command.

**Catch-up.** `slipwai migrate` writes `.mcp.json` where `codegraph` was adopted, the settings entries, the
registry row and the runner; commit the new file.

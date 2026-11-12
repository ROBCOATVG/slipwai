PATCH

**The board installs the coding agent's own command where the machine has none.** On a machine with nothing
but the board and the tools it installed, `./init --integration claude` ended *claude not found*: Spec Kit
looks for the harness's command before it installs an integration, and the agent the board fetches over
`npx` is an adapter in npm's cache that puts no command on any path. The project was left without Spec
Kit's commands and the draft went on without them. The registry now names, for fifteen harnesses, the npm
package that installs the command and the command's name. Where the machine has no such command and has
`npm`, the board installs it under `~/.slipwai/tools/` as the step before `./init`, and every child the
board starts finds it. A machine that has the command is left exactly as it is, and a person's own
terminal is not touched.

An agent the board installed from its archive that is the harness's own command — opencode, Goose, Kimi,
Kiro — is put on that same path, when it is installed and before `./init` for one installed earlier. The
board kept it under `~/.slipwai/agents/`, launched it by its whole path, and put it on no path, so on a
machine whose only opencode was the board's, `./init` could not find it.

**Catch-up:** none.

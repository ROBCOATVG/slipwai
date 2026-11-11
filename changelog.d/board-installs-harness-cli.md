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

**Catch-up:** none.

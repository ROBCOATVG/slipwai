MINOR

**What you choose in `slipwai generate` or `slipwai adopt` is installed for you: there is no follow-up install
to run.** Where the answers need a tool the machine lacks, slipwai installs it: Git, Make, uv and Python for the
setup; the toolchain of each language the project builds in (Node, Go, a JDK); a cloud's CLIs under `--target
aws|azure`. It uses the package manager the machine has — Homebrew or MacPorts; apt, dnf, pacman, zypper or apk
through `sudo`; winget, Scoop or Chocolatey — or the publisher's own download where a distribution's package is
too old to build with (Node, Go and the JDK on Linux, uv from its GitHub release). It does this wherever the
questions are answered at a terminal; `--install` asks for it from a script, `--no-install` turns it off, and
`SLIPWAI_NO_INSTALL=1` turns it off everywhere, naming each missing tool instead. The installer is one file,
`scripts/install-tools.py`, which every project now ships and slipwai itself loads, so `./init` on a
teammate's clone installs uv the same way instead of printing the line.

**`generate` and `adopt` ask which coding agent, with nothing preselected.** Spec Kit's own list highlights
GitHub Copilot, and Enter there chose it. `generate` asks among its questions (or uses the agent it runs
inside, or `--integration`); `adopt` (experimental) asks where the tree reads for more than one agent, and
records the answer in the adoption commit.

**Extensions install what they need.** CodeGraph runs its pinned CLI through `npx`, installing Node where it is
missing, and indexes only the project: it no longer runs `codegraph install`, which rewrote every agent's
global config (`~/.claude.json`, `~/.claude/CLAUDE.md`, Cursor's, Codex's, VS Code's). UI/UX Pro Max and the
UX gates, ticked before there is a browser app — an adopted repository whose frontend is still a candidate
(experimental), or a headless project — are recorded and wait, and install themselves once a browser app is
confirmed or added; before, they refused and asked for `slipwai add-frontend` and a second `./init`. The UX
gate installs Playwright's Chromium the first time it has Playwright and no browser. On Windows, where the
checkbox list cannot be drawn, `./init` asks for the extensions as a typed question in the console instead of
skipping the choice silently.

**`slipwai generate` in an empty folder makes that folder the project.** Its name is offered and nothing is nested
beneath it, so the agent started in the same folder finds the project's commands — the first real run made
`slipwai-test/test`, and Claude Code started in `slipwai-test` found none. Elsewhere a new folder is made, as
before, and the closing line says where to start the agent.

**What a Mac ships is accounted for.** A `python3` below 3.10 — Apple's 3.9 — counts as missing and is replaced
through Homebrew's `python`, the formula that links `python3`; Node below 22.13 likewise. `./init`, Spec Kit's
scripts and a generated project's `make verify` are checked under bash 3.2 and GNU Make 3.81, what macOS
ships. On Windows, slipwai's own output is UTF-8 wherever it is redirected: a piped or logged `generate` stopped
with `UnicodeEncodeError` on the first `—`.

**Smaller:** `slipwai adopt --next` (experimental) says `make verify` once the root Makefile includes the
delivery one, not `make -f delivery/Makefile verify`; `slipwai status` and `slipwai --next` answer the same
question instead of printing usage; the event-model check installs PyYAML with uv where pip is missing.

**Catch-up.** `slipwai migrate` brings `scripts/install-tools.py` and the new extension scripts. If CodeGraph was
adopted before this release, its old installer may have written global agent config: review `~/.claude/CLAUDE.md`
(which Claude Code loads in every project) and the MCP entries it added for tools you do not use.

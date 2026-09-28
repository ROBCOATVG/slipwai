MINOR

**`slipwai generate` runs the project's `./init` as its last step, and every missing tool is named with the
command that installs it on your machine.** Answering the questions at a terminal now ends the way
`slipwai adopt` does: `./init` runs from inside the new project, so Spec Kit and the agent's skills are in
place without a second command. `--integration <agent>` passes the agent through; `--init` asks for the run
from the argument form, which otherwise leaves it as the next step as before; `--no-init` skips it anywhere.

The machine is now detected — macOS, Linux, WSL or Windows, and which of Homebrew, MacPorts, apt, dnf,
pacman, zypper, apk, winget, Scoop or Chocolatey it has — so a production target's refusal says
`brew install opentofu` or `winget install --exact --id OpenTofu.Tofu` beside the install page, and
`./init` without uv or Python says the line that installs uv there. On native Windows, where a `/bin/sh`
script cannot run as it is, `generate` and `adopt` (experimental) run `./init` through Git for Windows' `sh`
when it is installed and otherwise say to use WSL or Git Bash; neither starts `./init` on a machine with no
`python3`, and both name the command that installs it.

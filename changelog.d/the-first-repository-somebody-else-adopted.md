PATCH

**A language somebody spoke brings its own toolchain.** The survey reads each directory once, by the first
ecosystem that recognises it, so a directory with a `package.json` beside a `requirements.txt` is Node. Saying
it is Python — with `--language`, or through the `--confirm` that `/ground` runs once it has read the code —
moved the language and left `kind: node` behind it, and a refresh then put the reading back over the answer.
The toolchain is what CI installs, so the record was describing a pipeline that cannot run. It now follows the
language where the tree has a build in that language to follow, is left alone where it has none rather than
invented, and a refresh holds what a person settled and says what the tree now reads instead.

**Claude Code's hooks find their scripts from any directory.** They were written as repository-relative paths
and run with whatever directory the session is in, so a session opened in a subdirectory ran
`python3 delivery/scripts/agents/cruise.py` against a path that is not there — and a hook that fails is silent.
They are written from `$CLAUDE_PROJECT_DIR` now, and the two other harnesses the factory writes hooks for —
Cursor's `.cursor/hooks.json` and Gemini CLI's `.gemini/settings.json` — change to the root Git names
(`cd "$(git rev-parse --show-toplevel)" && …`) before they run, since neither harness shares a variable
for it. `make agents` rewrites them; nothing else is asked of a repository already generated.

**A command that needs an application says that confirming one is the missing step.** Between `adopt` and the
first confirmed candidate there is nothing for a frontend to sit beside, and `slipwai add-frontend web` — which
is what `./init` had just said to run — answered "project.json names no deployables, so there is nothing to add
a service to". True, and the same sentence a manifest that names none gets. It now names the candidates and the
command that settles one.

**An extension tells a wrapped repository to run the script it actually has.** `./init --extension codegraph`
is advice nobody can follow where the adoption put `init` under `delivery/`. The three shipped extensions
derive the path from where they are, in all ten places they print it.

**`slipwai adopt --next` runs to the loop rather than stopping at a ready repository.** It ended at the
strategy ADR — wrapped, gated and asked to do nothing — and the first person to take it end to end had to be
told the rest in chat. It now names `/speckit-constitution` before the first spec, because `check-constitution`
fails the moment `specs/` exists over the template it installed, then `/speckit-specify`, `/drive` once by
hand, and `make cruise`. A constitution in a repository where `./init` has never run reports as pending, which
is what it is.

**`--command app:test=` records none, as `-` does.** An empty value is what a shell leaves when a variable is
unset, and recording `""` wrote a target that runs nothing and reads as one somebody chose. The report now
says what each target was vouched for with, so a written no is visible where it was decided.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it
gets wrong belongs on that issue.

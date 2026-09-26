MINOR

**`slipwai adopt` establishes which coding agent the material is for, instead of leaving it to a question
`./init` asks one step too late.** `./init` projects the canonical skills, commands and agent types into one
harness's native locations, and it has always asked which — after `adopt` had already finished. That ordering
makes the answer useless to the adoption itself, because the questions worth handing to a coding agent are the
ones asked before there is one. It was also mostly answerable without asking: a run started from inside a
harness is told so by its environment, and a repository whose team already uses one says so in the tree
(`.claude/skills`, `.gemini/commands`, `.github/copilot-instructions.md`). `adopt` now reads both and records
the answer in `project.json` under `agent`, with the evidence and `detected` provenance; `--integration <agent>`
names it outright, recorded `overridden`, and `./init` asks nothing where the record already says. What nothing
establishes stays `unrecorded` and is said out loud — a directory two harnesses read names neither, a tree that
reads for two records neither, and a thirty-six-row list is not a question a terminal can ask well — so `./init`
keeps its own question for exactly the case it is still needed in.

**Catch-up.** Nothing. A repository adopted by an earlier factory has no `agent` key, which reads as the
question still being open, and `./init --integration <agent>` answers it the way it always did. A re-survey
carries the key as recorded rather than re-reading it: which agent gets the material is not something the tree
says.

**`slipwai adopt --init` runs `./init` once the adoption is committed, so a terminal adoption can end in one
step rather than four.** Off unless asked for: `./init` reaches Spec Kit's source, and making every `--yes` in
a script or a test need the network to finish would be a poor trade for saving a line. It runs last and never
inside the commit, so an unreachable source costs the adoption nothing — the commit is already made, the
failure says so, and `slipwai adopt --next` keeps naming `./init` as the step you are on. What it writes is
left uncommitted and yours to read, exactly as in a project the factory generated. `--no-init` is the default
said out loud.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it gets wrong belongs on that issue.

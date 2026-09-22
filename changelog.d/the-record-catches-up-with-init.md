PATCH

**`slipwai adopt` no longer names `./init` as the next step and then runs it two lines later.** Where
`--init` is going to run it, the report says it is running now and what that leaves for you to commit; the
rest of the sequence is unchanged, since only the first line was ever about that step.

**And where `adopt` could not tell which coding agent the material was for, the record now catches up with
the answer `./init` collected.** Handing the question on was right — a tree that reads for three harnesses is
a decision and not a guess — but the answer then existed only in Spec Kit's own file while `project.json`
still said nobody had established one, and `slipwai adopt --next` went on offering `--integration` for a
question somebody had already answered. `harness.py` now reads `.specify/integration.json` as a source of its
own, and the strongest one: a person answered `./init`, so it is recorded `confirmed`, and it outranks both
the environment a run started in and what the tree reads, which are readings rather than answers. A record
that already names a harness is left alone, and one a person overrode is never moved by a later step.

Found by running the reshaped intro over PrestaShop, whose tree reads for Claude Code, GitHub Copilot and
Gemini CLI at once — which is the case the ambiguity rule was written for, and the first time it has been met
in the wild.

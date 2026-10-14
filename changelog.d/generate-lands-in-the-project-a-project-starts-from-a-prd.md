MINOR

**A project can be started from a product requirements document, and the board takes it to a specification
a person reads before anything is built.** The interview's last question is a file picker on the board and a
path in the terminal; `slipwai generate --prd <file>` copies it into the project as `docs/prd.md`, listed in
the docs index, before the first commit. After `./init`, the board runs `make draft`: one headless session of
the coding agent, with the new `commands/draft.md` as its rules, that ratifies the constitution and writes
the first `specs/<feature>/spec.md` from the document — every call the document does not settle recorded
under its own `## Assumptions` heading — and stops. The board then shows **Continue the build**, which runs
`make launch` (`commands/launch.md`): the chart and the split in a second session answering stops as
`/cruise` does, `/cruise` enabled, and the fleet cast off. Nothing runs unattended until a person has had
the specification in front of them and pressed the button. Both `make draft` and `make launch` are typeable
in a terminal, and `/draft` and `/launch` are commands in every installed harness.

**Catch-up:** `slipwai migrate` carries `commands/draft.md`, `commands/launch.md`,
`scripts/agents/draft.py`, `scripts/agents/launch.py` and the two Makefile targets into an existing project.
A project that already has a PRD puts it at `docs/prd.md` and runs `make draft`.

PATCH

**Agreeing to an extension's guard, or taking the agreement back, no longer leaves the gate red.** An
extension's block in `AGENTS.md` can say whether its guard is agreed to here, and
`python3 scripts/extensions/guards.py --elect <key>` and `--remove <key>` changed the agreement without
rewriting that block, so `make check-extensions` failed until somebody ran `make agents`. Answering *yes*
at the question `make agents` asks did the same. Both commands now bring what follows from the agreement up
to date before they return: the harness's row, the guidance of the extension named (its `project` hook is
fired for it alone), and the copy of that guidance a harness such as Gemini CLI reads. They print what
they brought up to date. A `project` hook that crashes or runs over its budget does not undo the agreement
or fail the command: it is named, and `make agents` runs it again.

**Catch-up:** `slipwai migrate` brings the scripts. If you agreed to a guard and `make check-extensions`
has been red since, run `make agents` once.

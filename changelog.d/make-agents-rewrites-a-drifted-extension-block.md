PATCH

**`make agents` rewrites a drifted extension block in `AGENTS.md` for every elected extension, so the fix
`check-extensions` names is one.** The gate said "run `make agents` or `slipwai migrate`", and for an
extension that attaches nothing to the `project` hook point neither rewrote the block — only running the
extension's whole `init` again did. `codegraph` 1.0.0 is one such. `scripts/extensions/project.py` still
fires the point first; then, where an elected extension's block still differs from the `GUIDANCE` its
`init.py` declares, it writes the block from that text, in place. The extension's set-up is not run again,
and nothing outside its own markers is touched. The gate's message now names the file the block is held
against.

**Catch-up:** `slipwai migrate` carries the new `scripts/extensions/project.py` and runs it; a project whose
gate is red on a drifted block before then runs `make agents` after migrating and commits `AGENTS.md`.

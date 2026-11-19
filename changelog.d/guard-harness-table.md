MINOR

**The contract page says which harness holds which guard, and an extension is told at `init` and
`project`.** Only Claude Code runs a guard before a tool call; Cursor and Gemini CLI hold `before-stop` and
nothing else, because the harness registry records no pre-tool hook for either whose shape was read, and
slipwai does not write a hook file from a guess. That was true before and nothing said it, so an
extension's guidance could promise a refusal that never came. `docs/extensions.md` now carries the table,
a hook at `init` or `project` receives `SLIPWAI_GUARDS_HELD` (a JSON object: each installed harness and
the moments that hold there), and `python3 scripts/extensions/guard_harness.py --held` prints the same.

**Catch-up:** `slipwai migrate` brings the scripts; nothing else for a project. An extension author whose
guidance mentions a guard reads `SLIPWAI_GUARDS_HELD` and says the rule is advice on a harness that is not
listed for that guard.

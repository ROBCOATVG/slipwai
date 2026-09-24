PATCH

**A `/cruise` run can no longer make a gate pass by changing the gate.** A run met `check-ux-gates` failing
because two of the kit's scripts crash where Chrome is not installed, and the bosun patched
`scripts/check-ux-gates.py` to report that as skipped, committed it, and went on. Its brief now forbids
touching anything under `scripts/`, the `Makefile`, anything under `tools/`, CI or a harness's hook settings,
and says what a gate the tree cannot satisfy becomes: a park with the gate's own words as the reason. The rule
is held in two places rather than said louder. `.claude/settings.json` runs `scripts/agents/cruise.py guard`
as Claude Code's `PreToolUse` hook on every editing tool, and in a session the runner started it refuses an
edit to any of those paths before it lands. And the runner takes the content of every gate and control before
each iteration and compares it after, on every harness: a file modified, deleted or added — a file installed
under `tools/` excepted — parks the run at once, names the files on the log entry as `controls_changed`, and
counts the iteration's last line for nothing. A person's own session meets neither.

**`check-ux-gates` runs on Playwright's own Chromium where Chrome is not installed, and never reports a
crash as a pass or a failure.** The gate now asks once which browser Playwright can open — Chrome, its bundled
Chromium, or neither — and where only the bundled one opens, starts every render gate with a Node preload that
retries the kit's `channel: 'chrome'` launch without the channel, so `verify_responsive.mjs` and
`verify_target_size.mjs` run there like the kit's other three. Where no browser opens, or Playwright is not
resolvable, the render gates are counted skipped without running one, and a gate that still fails on its launch
is reported skipped rather than as a finding; `UX_GATES_REQUIRE=1` still makes every skip a failure.

**Catch-up.** `slipwai migrate` brings the hook, the runner, the gate and the command text. A run that already
carries a patched gate is found by `git log -- scripts/` and reverted by hand; the runner parks on the next
change, not on the standing one.

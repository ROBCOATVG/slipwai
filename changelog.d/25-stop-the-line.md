MINOR

**A red trunk stops the line, and an agent is sent to fix it.** When trunk's CI goes red, every captain
holds at its next boundary and starts nothing new until trunk is green again. The harbourmaster sends the
new trunk mender (`agents/harbour-trunk-mender.md`) into a worktree of its own, with the red commit, the job
that failed and its log. The mender fixes forward, or reverts the merge that went red, and its branch lands
through the same `make verify` gate as a slice's. Before this, a red trunk only refused merges, and the
order to fix it could go missing: it went to the captain whose `merged` line named the commit, and that
line can arrive many minutes after the red. Each attempt shows on the board as `mend`, then `mended` or
`mend-failed`. After `attempts` failed tries the red parks for you, with the mender's last reason. To be
asked about every red straight away instead, set `"mender": "off"` in `harbour.json`.

**What the mender may change is checked, not trusted.** It may never edit a gate or what runs one:
`scripts/`, `tools/`, the hooks, the `Makefile`, the controlled files and the agents' own material are all
refused. In `.github/workflows/` it may only move an action's `uses:` to another ref of the same action, for
example `upload-artifact@v3` to `@v4` when GitHub refuses the old one at *Set up job*. A revert may touch
only what the reverted merge touched.

**It also lands what slices hand back.** While trunk is green, the mender takes one open need at a time:
the `.env.example` lines, a `docs/design.md` section or a `packages/` change that a slice may not make
itself. It takes needs written `by: fleet`, and under `/cruise` also needs written `by: person`, as long as
their check reads a shared file. The need's own check then ticks it on trunk, and the slice's park clears
without anybody being asked.

**Catch-up:** `slipwai migrate` brings in `scripts/agents/mender.py`, the new brief, and the updated
harbourmaster and captain. Restart the fleet afterwards.

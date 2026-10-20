PATCH

**A merge's answer says where its time went.** Every `granted` and `refused` line for a merge now carries
`waited_s` (how long the request sat before the harbourmaster took it up), `lock_s` (how long it waited on
`refs/slipwai/merge` for another machine's merge), `gate_s` (how long `make verify` ran on the rebased
branch) and `attempt` (which try at that slice this was). Integration that feels slow can now be read off the
harbour log: a long queue, a busy merge ref, a long gate, or a slice going round the berth again and again.
A refused merge also names its `slice`.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/harbourmaster.py`. Lines written before it carry
no timings, and nothing reads them as zero.

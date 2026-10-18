PATCH

**Uncommitted changes on trunk no longer stop a voyage.** In a harbour with no remote, a slice that had passed
its full gate was refused at the merge whenever the person's own checkout sat on trunk with any edit in it —
even an edit to a file the slice never touched. The refusal was not one a berth could fix, so the fairway
parked behind finished work and nothing told anyone. The harbourmaster now fast-forwards around the person's
changes, which git does whenever the merge does not touch the same files. Where it would, the checkout is
detached exactly where it stands, with its working tree and index untouched, and trunk moves on anyway. The
`granted` line's `note` says so, and how to get back: commit or stash, then `git switch main`.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/harbourmaster.py`. A fairway already parked
by this refusal is cleared with `python3 scripts/agents/harbourmaster.py --clear <fairway> --parked <timestamp>
--what 'merge again'`.

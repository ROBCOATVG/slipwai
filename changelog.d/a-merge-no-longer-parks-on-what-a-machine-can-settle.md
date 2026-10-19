PATCH

**A fairway parked because trunk was red now asks again once trunk is green.** The refusal said the queue
drains the moment trunk is green, but nothing drained it: the captain parked, and a parked fairway is never
relit, so every fairway that asked to merge during a red build waited for a person after the build was
fixed. A merge refused only because trunk was red now carries `waiting: "green-trunk"`. On any pass where
trunk is no longer red, the harbourmaster writes a `cleared` receipt for each park that refusal caused, and
the fairway asks for its merge again.

**A push that loses a race to trunk is gated again, not refused.** If someone else pushed to trunk between
the harbourmaster's fetch and its push, the forge refused the push, and the fairway parked behind a slice
that had passed its gate. The harbourmaster now fetches, rebases and gates the slice again on the new trunk,
up to three more times, all while it still holds the merge ref. A trunk that moves under every attempt is
refused as something a captain can ask for again, not as a park.

**The merge ref has a lease, so a dead machine no longer stops every merge.** `refs/slipwai/merge` had no
lease. A machine killed in the middle of a merge held it until the hour's wait ran out, and then the
fairway that asked was parked. The lease is half of `wait_bound`, which is half an hour by default. The
holder renews the ref while its gate runs, so a long `make verify` never lapses. A holder that has not
renewed within the lease is taken over, and the harbour log says so in a new `merge-taken-over` line naming
the machine it was taken from. Trunk is moved only if this machine still holds the ref once its gate is
over.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/harbourmaster.py`, `claims.py` and
`logs.py`. A fairway already parked by a red trunk is cleared on the harbourmaster's first pass after the
upgrade if the refusal it parked on was written by the new harbourmaster; one parked before that is cleared
with `python3 scripts/agents/harbourmaster.py --clear <fairway> --parked <timestamp> --what 'merge again'`.

PATCH

**The captain runs a capability's gates before it asks to merge the slice that makes it whole.** The
harbourmaster refuses that merge until the capability's `gates.md` says `Cleared:` on the slice's branch, and
the captain used to ask anyway, be refused, and only then send the slice back to run the gates — a refusal
that was certain every time, 23 of them on one run. The captain now asks the same predicate the
harbourmaster holds the merge on, which moved to `scripts/agents/capabilities.py` so there is one copy of
it, and where the gates are owed it dispatches them first and asks for the merge once it would be granted.
The harbourmaster still refuses an ungated last merge, whoever asks.

**Catch-up:** `slipwai migrate` carries `scripts/agents/captain.py`, `scripts/agents/capabilities.py` and
`scripts/agents/harbourmaster.py`. Nothing to change in a project; restart a running fleet to pick it up.

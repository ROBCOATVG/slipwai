PATCH

**The mender settles up to twelve stops of one merge's rebase, and a merge that outruns them says so.** A
slice far behind trunk stops on the same file once per replayed commit; at four stops the merge was refused
part-way with nothing in the refusal saying the mender had been sent.

**Catch-up:** `slipwai migrate` carries `scripts/agents/conflicts.py` and `harbourmaster.py`. Nothing to change.

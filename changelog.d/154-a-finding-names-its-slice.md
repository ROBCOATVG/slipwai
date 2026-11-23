PATCH

**`check-dispatch` lets a finding id through after the slice it belongs to.** The ids the review, gaps,
adversary and converge stages mint — `F1`, `G1`, `G-1`, `MS-1` — were refused as work no plan knows about
even in a subject that named its slice first, such as `S61 F1: …`, which blocked the push and sent the
mender round. A finding-shaped id that comes after a planned slice in the same subject, and does not open
with that slice's letters, now qualifies the slice rather than claiming work: the slice is still held to
the plan and the dispatch ledger. A subject whose only id is unknown, `UI3: …`, is refused as before, and a
range of slices such as `SB4-SB7` still has each end judged as a slice.

**Catch-up:** `slipwai migrate` carries `scripts/check-dispatch.py`. Nothing to change in a project; a
slice that wrote `S62 G-1:` to dodge the rule can go back to `S62 G1:`.

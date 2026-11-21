PATCH

**A slice is no longer parked in the second it asks for its merge, and a park about a merged slice clears
itself from the harbour's own answer.** A slice's merge requests are numbered from nought at every run, and
an answer already in the harbour log under that number is the earlier asking's. The guard for that compared
against the new request's time, which a request did not have until its line was written, so it never held:
the captain was handed an hours-old refusal at once, ran the slice again to resolve nothing, and parked it as
out of runs while the harbourmaster was gating and granting the merge it had just asked for. The request is
now stamped when it is made. And the
receipt that clears a park about a merged slice reads the harbourmaster's `granted` as well as the captain's
`merged`, so a slice that is on trunk never waits for a person to say so.

**A slice in flight takes every migration, not only the first.** The files an earlier take had put in a
slice's worktree counted as the slice's own changes from then on, so a second migration left them as they
were: a slice in flight through two migrations ran on the first one's scripts until it merged.

**Catch-up:** `slipwai migrate` carries `scripts/agents/captain.py`, `harbourmaster.py` and `moorings.py`. Nothing to change
in a project.

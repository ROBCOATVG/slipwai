PATCH

**A slice whose park is cleared no longer parks again because a sibling's berth was removed at that
moment.** Finding a slice's berth looks through every worktree git lists for one left mid-rebase, and git
lists a merged sibling's worktree until it is pruned. Where that sibling's folder was removed after its merge
while the look ran, starting git in it raised, and the cleared slice parked on "the captain met
FileNotFoundError" naming the sibling's berth. A folder that is gone is now stepped past: it holds no rebase
of anything. The captain abreast case that let two slices go at once now lets them go one at a time, so
`make parity` reads the same decks on every run (slipwai#154).

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/moorings.py`.

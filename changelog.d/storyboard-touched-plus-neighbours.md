PATCH

**The rule for how much of a large app a further feature's storyboard frames is written down exactly.** The
rule itself has not changed: the storyboard frames what the feature touches and its neighbours, and names
the rest of the flow as linked boxes. `commands/mockups.md` and the `storyboard` skill now say what a
neighbour is. It is a surface one step either side of a touched one, by one navigation in the app, or by
the slice before and after in the event model where a surface is not built. A neighbour's neighbour is not
framed. The drawing lists what it framed under `## Framed` in `research.md`, so that you can hold the
storyboard to the list. `python3 scripts/agents/existing.py <feature> --check` prints a note when a changed
surface has no original framed beside it. It refuses no storyboard for the number of frames, because no
file records which screen leads to which.

**Catch-up:** `slipwai migrate` carries the new `commands/mockups.md`, `skills/storyboard/SKILL.md` and
`scripts/agents/existing.py`. Storyboards on disk need no change.

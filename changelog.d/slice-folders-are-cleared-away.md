PATCH

**A merged slice no longer leaves its folder beside the project.** Each slice is worked in its own worktree,
`<project>-<slice>`, which was removed only in the moment the slice merged and only where git agreed: a
build's output or a screenshot lying in it kept it, and so did a captain stopped a moment early. Three
things change. On merge the worktree goes with whatever it holds that git does not track, and stays only
where tracked files were edited and never committed, saying which. Casting off clears away the worktrees of
slices that have merged, and git's record of ones somebody deleted by hand. And `make cruise-tidy`
(`python3 scripts/agents/fleet.py tidy`) does the same on request and lists every other slice worktree with
what it holds; a slice that has not merged is never removed for you.

**Catch-up:** `slipwai migrate` carries `scripts/agents/moorings.py`, `fleet.py` and the `cruise-tidy` target.
Run `make cruise-tidy` once to clear what earlier runs left.

PATCH

**Casting off pushes the plan first, so a slice finds itself in its own worktree.** The launch that charts
and splits a feature commits in the project's checkout and pushes nothing, and each slice's worktree is cut
from the remote trunk. A fleet cast off straight after a launch claimed three slices whose worktrees had no
model entry, no chart row, no storyboard and no split for them. `make cruise` now publishes before it lights
anything: a checkout on the trunk branch that is only ahead of the remote is pushed, and the line says how
many commits went. Where that cannot be done — the push is refused, or the checkout and the remote have both
moved and the commits only here change a chart or the model — nothing is cast off and the line says what to
do. A checkout that is merely behind the remote is left alone, as the fleet's own merges leave it.

**Catch-up:** `slipwai migrate` carries `scripts/agents/published.py`, `fleet.py` and `commands/launch.md`.
A project with a launch committed and not pushed: `git push`, or cast off again once migrated.

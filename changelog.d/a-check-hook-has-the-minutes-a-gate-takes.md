PATCH

**A `check` hook has the minutes a gate takes.** A hook that named no budget had 30 seconds at every point,
and ux-gates' `check` hook runs its render gates over every screen: in hr-test-2 they took minutes, and the
hook was ended every time though every shard passed. A `check` hook now defaults to 600 seconds; other points
keep 30, and a declared `budget` still wins.

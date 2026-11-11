PATCH

**A park you clear is carried on even where the fleet was stopped while it stood.** A captain that was
asked to stop wrote `stopped` after the slice's `parked` line, and the check that picks a cleared park up
mid-turn read only a park as the slice's last word. So a slice parked, stopped with the fleet and then
cleared was stepped past until the turn ended: a finished slice waited one merge request from trunk while
its captain started the next one.

**Catch-up:** `slipwai upgrade` carries the new `scripts/agents/captain.py` into the project.

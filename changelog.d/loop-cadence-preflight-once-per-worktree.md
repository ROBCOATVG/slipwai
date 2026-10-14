MINOR

**A worktree is checked once before anything is dispatched into it.** One run's delegates discovered the
same environment in series — Go's build cache not writable, then Staticcheck's, then a test refused a local
socket, then the browser harness was missing and a suite crashed while trying to skip, then several delegates
in unindexed checkouts tried the code index route that was not there — a dispatch, a return and a host repair
apiece, none of it about the product. `make preflight` (`scripts/agents/preflight.py`) asks those questions
once, read off `project.json` and the elected extensions: a Python the gate scripts can run on and PyYAML in
it, a localhost socket a test may bind, each deployable's toolchain on PATH and its caches writable, Node's
dependencies installed, the index present where one is elected. One line per check, the fix on a failing
one, a language nobody has a check for said as such rather than passed, and exit 1 on any failure. *Running
ready slices concurrently* runs it in every new worktree before the slice's delegate is dispatched.

**Catch-up:** `slipwai migrate` brings the script, the target and the paragraph.

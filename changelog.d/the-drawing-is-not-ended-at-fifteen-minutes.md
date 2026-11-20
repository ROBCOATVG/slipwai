PATCH

**A storyboard drawing has an hour, not fifteen minutes, and the board reads the same number the project
does.** A further feature with ten stories and twenty surfaces spent ten of its fifteen minutes on research,
was ended while its pages were still being written, and left twenty screens, no storyboard and no review,
reported as a drawing that stopped short. The ceiling is there to end a session that is lost, so it is now
sixty minutes for a first drawing and thirty for a redraw, scaled by the telegraph as before. A drawing the
board runs took none of this from `harbour.json`: it was ended at a fixed nine hundred seconds whatever the
file said, and was never told how long it had. It now reads the `surfaces` and `surfaces-redraw` rows as
`make surfaces` does, tells the session its minutes, and shows them on the stage's clock. A drawing that was
ended says that what it drew is kept and that saying what is left in the storyboard's conversation carries it
on; a drawing carried on that way has a first drawing's ceiling again.

**Catch-up:** `slipwai migrate` carries `scripts/agents/drawing_budget.py`, `surfaces.py` and
`commands/mockups.md`. A project that wants its old ceiling writes
`"surfaces": {"minutes": 15}` and `"surfaces-redraw": {"minutes": 10}` under `stages` in `harbour.json`.

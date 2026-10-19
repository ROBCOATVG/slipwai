PATCH

**A disapproved storyboard is drawn again, from your reason.** Disapproving used to start nothing, and the
Draw the surfaces button had gone with the first drawing, so a run stopped at a person's no with no way on.
Now Disapprove starts `make surfaces` for that feature at once. The session is told it is a redraw
(`SLIPWAI_REDRAW=1`), so it redraws every surface and the storyboard in place answering the reason, rather
than reviewing its own rejected drafts as if a person had handed them over. Once it lands, the old verdicts
move to `specs/<feature>/mockups/disapproved.md` and the new storyboard waits on a verdict of its own. A
disapproved storyboard also brings the Draw button back, to retry a redraw that failed.

**The board shows a drawing it did not start.** `make surfaces` writes `.slipwai/surfaces.pid` the way
`make model-next` writes its own, so a board restarted mid-draw, or a redraw run from the terminal, shows the
storyboard as working rather than waiting on buttons that are locked.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/surfaces.py` and `commands/mockups.md`.
A storyboard already disapproved shows the Draw button again once the board is restarted.

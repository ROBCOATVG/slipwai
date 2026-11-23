PATCH

**A further feature's storyboard waiting on your verdict now says so, everywhere the board speaks.** Once a
second or later feature had any drawing, the strip counted every feature's verdicts as this one's: a project
whose earlier storyboard was approved read "44 of 44 states approved", ticked the storyboard done, and its
*Now* line sent the person to cast off the fleet instead of to the one button that moved the project. The
strip now counts only the feature in hand, so the storyboard reads *drawn: waiting on your verdict* and the
*Now* line names the place: the Screens tab, under Storyboard, Approve storyboard or Disapprove.

Around it: the Voyage card carries a **Review the storyboard** button that opens that tab, and no longer shows
*Model it next* while the storyboard waits; the drawing's own card says **waiting on you** with a link,
rather than `done`, when the drawing ended well and stopped for the verdict. The drawing session ends every
turn that stops for the verdict with a fixed *Waiting on you* block, and no longer tells a person to mark
each state `approved`, `parked` or `n/a` — the board has one verdict for the whole storyboard, and a person
sent to look for per-state controls found nothing to press.

**Catch-up:** `slipwai migrate` brings the new `commands/mockups.md` into a project; the board's changes
need nothing beyond upgrading slipwai.

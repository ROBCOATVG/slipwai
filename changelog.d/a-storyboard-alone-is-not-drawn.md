PATCH

**A storyboard drawn with no page per surface is redrawn, not stuck.** The board approves a drawing one state
at a time from a page per surface, and the drawing stage and the board counted the storyboard page itself as a
surface. So a session that drew the surfaces inside `storyboard.html` reported `drawn`, the board offered Approve
and Disapprove and refused both, and with something "drawn" it never offered Draw the surfaces again. All three
now read the same thing: a surface page is any page but the storyboard and the contents page. A storyboard on its
own is nothing drawn — the stage says so and fails, and the board offers the drawing again — and `/mockups` says
what each surface page holds.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/surfaces.py` and `commands/mockups.md`. A project
stuck on a storyboard alone: the board now offers Draw the surfaces.

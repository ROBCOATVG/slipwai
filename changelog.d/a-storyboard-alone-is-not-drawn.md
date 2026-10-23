PATCH

**A storyboard of the mock-ups you handed over can be approved.** Where a person hands mock-ups over in
`docs/design/`, the drawing stage storyboards them rather than redrawing them, so its storyboard embeds pages that
are not beside it. The board read only the pages beside the storyboard as surfaces: it offered Approve, refused
it, and then sent the person round to Draw the surfaces for a drawing that was done. The surfaces are now the pages
beside the storyboard, or else the pages inside the project it embeds or links — one reading, shared by the
drawing stage, the board's strip and the verdict — and a storyboard with no page at all to show is nothing drawn:
the stage says so, the Storyboard card says there is nothing to approve instead of offering buttons, and the
board offers the drawing again. `/mockups` says what a surface page holds, and where the board finds one.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/surfaces.py` and `commands/mockups.md`.

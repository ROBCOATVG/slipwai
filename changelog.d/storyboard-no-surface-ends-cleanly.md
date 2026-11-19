MINOR

**A further feature that adds and changes no screen no longer stops the mock-up stage.** Such a feature
ended "nothing to approve" with a non-zero exit, and you wrote `surfaces: none` by hand before it could
move. The stage now writes `specs/<feature>/mockups/mock-states.md` as `surfaces: none` itself, with the
reason, and exits 0. It does this only on positive grounds: the drawing's `research.md` says `Surfaces:
none` with a reason, no requirement line of the specification asks for something that a person or another
system meets, no slice of the feature names a surface or carries a `ui` frame, and nothing is drawn or
judged. The file says that the stage recorded it and on which grounds. When one of the grounds is missing,
the stage stops as before and says which one. A drawing that drew nothing and said nothing is still a
failure. The reading of the specification is by word, so a requirement such as "the job reports failures
to the log" stops the stage; `/mockups <feature>` in the agent settles it.

**Catch-up:** `slipwai migrate` carries the new `commands/mockups.md`, `scripts/agents/surfaces.py` and
`scripts/agents/no_surface.py`. A feature that you already marked `surfaces: none` needs no change. To draw
a surface for a feature that the stage recorded as having none, delete its `mock-states.md` and run
`/mockups <feature>`.

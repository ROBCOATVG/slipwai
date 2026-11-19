MINOR

**The storyboard stage starts from the surfaces the hand-over conversation suggested.** When you hand over a
further feature on the board, the agent you talk to may name the existing surfaces it thinks the idea touches,
and the board keeps them with the idea as `docs/intake/<slug>/surfaces.json`. Until now nothing read that
file. The list of what exists that `/mockups` reads first (`specs/<feature>/mockups/existing.md`) now has a
*Suggested by the hand-over* section. Each suggested name that is a surface of the project is marked
`suggested, start here`, and each name no surface answers to is listed as `suggested, no such surface found`,
for the drawing to decide whether it is a new surface or a wrong name. A name is matched by the name alone,
ignoring case, punctuation and spacing, against what a surface is called or a route that reaches it. Nothing
is guessed. The page says it is a suggestion the drawing may change, and the file is read and never edited.

A feature is traced to its idea through the `feature` that `docs/intake/<slug>/specified.json` records. A
hint that is missing, malformed or larger than 64 KB is ignored with one line saying why. At most twelve
names of eighty characters are read, with control characters and backticks removed, and no name is used as a
path.

One verdict can change, and only towards stopping. Where the hand-over suggested surfaces and the drawing
says the feature has none (`Surfaces: none — <why>`), the stage no longer records `surfaces: none` on that
line alone. It stops and says the two disagree, unless `research.md` also says `Suggested surfaces: not
touched — <why>`; then the record names the suggestion and the answer. A feature with no hint ends as it
did before.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/surface_hint.py`, `existing.py`,
`surfaces.py`, `no_surface.py`, `commands/mockups.md` and `skills/storyboard/SKILL.md`. Ideas and
storyboards on disk need no change; run `python3 scripts/agents/existing.py <feature> --write` to see the
suggestion for a feature already handed over.

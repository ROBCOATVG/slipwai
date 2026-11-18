MINOR

**A further feature is drawn into the product's storyboard, in the app's own look, and you are asked only
about what is new.** The mock-up stage drew each feature alone: a second feature got a storyboard holding
only its own screens, in a look made up for it, and a project with a built app and no storyboard — one that
crossed from version 1 — had no storyboard of what exists at all. The stage now starts from a list of what
the project has (`python3 scripts/agents/existing.py <feature>`: earlier features' mock-ups, the browser
app's committed previews, routes and stylesheets, the event model's screens, `docs/design.md`), and the
storyboard shows the flow as it stands with the new feature in it. Built screens are framed from the real
thing, never redrawn. New and changed screens link the app's own stylesheet and sit in its shell;
`docs/design/` still wins where you handed a direction over, and a look is proposed only where a project
has neither. Every surface is marked built, changed or new: the board's Storyboard card shows the three
apart, **Approve storyboard** marks the changed and new states only, and `check-surfaces` asks nothing of a
built surface. The storyboard stays one per feature; the newest one is the whole flow.

**Catch-up:** `slipwai migrate` carries the new `commands/mockups.md`, `skills/storyboard/SKILL.md`,
`scripts/check-surfaces.py`, `scripts/agents/surfaces.py` and `scripts/agents/existing.py`. Storyboards
already approved are read as before: a storyboard that marks nothing has every page put up for a verdict,
as it always did. For a project with a built app and no storyboard, run `/mockups <feature>` on its next
feature.

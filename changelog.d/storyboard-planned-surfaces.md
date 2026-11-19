MINOR

**A screen you approved for an earlier feature and have not built yet is shown as planned, not as built.**
A further feature's storyboard framed such a screen as built, with a sentence in its cell saying that it
was not. It now has a word of its own: `data-surface="planned"`, beside `built`, `changed` and `new`. The
list the mock-up stage starts from (`python3 scripts/agents/existing.py <feature>`) says which word each
surface takes, under *What each surface is*: planned is a surface with a state that you approved and with
no preview, no implemented screen in the event model, no design-review photograph and no route. The board's
Storyboard card shows a **Planned** chip, **Approve storyboard** still marks the changed and new states
only, and `check-surfaces` refuses a slice that names a planned surface, because the earlier feature
delivers it. A storyboard that uses three words reads as it did.

**Catch-up:** `slipwai migrate` carries the new `commands/mockups.md`, `skills/storyboard/SKILL.md`,
`scripts/check-surfaces.py`, `scripts/agents/surfaces.py` and `scripts/agents/existing.py`. Storyboards on
disk need no change. To have an earlier feature's unbuilt screens marked planned in a storyboard that
frames them as built, run `/mockups <feature>` again on the newer feature.

MINOR

**A screen known only from a route is shown as built with no picture, and nothing is invented about how it
looks.** The mock-up stage takes a preview, an implemented screen in the event model, a design-review
photograph or a route as evidence that a surface is built, in that order. A route proves that the screen
exists and shows nothing of it. The list the stage starts from (`python3 scripts/agents/existing.py
<feature>`) now says *built, no picture* for such a surface, and the storyboard draws it as a plain box
that carries its route: `data-surface="built" data-picture="none"`. The board's Storyboard card counts it
with the built surfaces and marks it *(no picture)*. `python3 scripts/agents/existing.py <feature> --check`
refuses a box that frames a page or holds a drawn form, table, list or image, and the drawing stage runs
the same check when it ends. The check reads markup only; whether a box's label says more than is known is
left to the reader.

**Catch-up:** `slipwai migrate` carries the new `commands/mockups.md`, `skills/storyboard/SKILL.md`,
`scripts/agents/surfaces.py` and `scripts/agents/existing.py`. Storyboards on disk need no change. To give
a surface a picture, commit a preview of it under the browser app's `screens/` directory.

PATCH

**The first drawing of the surfaces is styled.** Plain unstyled wireframes were turned down for having no
style, on two projects out of two, and the redraw that bought cost ten times the drawing. Where
`docs/design/` hands over no direction, the drawing now sets a short one first — a few tokens, one shared
`mockups.css`, only the components the surfaces use — and `research.md` says it is a proposed look for
reviewing the flow, not a brand. Where `docs/design/` has a direction, it is followed as before.

**A storyboard is checked as a sketch, not as the product.** In the mock-up stage each surface is rendered
at most once per pass, in one theme, to catch a broken layout; there is no render-and-tweak loop, no light
and dark pair and no phone-width sweep unless the specification makes mobile primary. The storyboard embeds
or links the surfaces and makes no screenshots or thumbnails. Production-grade visual review still happens
where it always did, before a slice that builds the surface is demonstrated.

**The drawing has a budget, and is ended at it.** Fifteen minutes for a first drawing and ten for a redraw,
scaled by the telegraph's `stage_scale` (a `surfaces` or `surfaces-redraw` row in `harbour.json` overrides
either). The session is told its minutes and when they run out, so it plans to them; at the end of them
`make surfaces` ends it and every delegate it started, keeps what it drew, and says so in one line. Something
drawn is a storyboard to review, so that run exits 0; nothing drawn still exits 1. While it draws, the
board's Storyboard step says how far in it is: *drawing: 6 of about 15 min*.

**A redraw answers its reason and nothing else.** It reuses the design direction and stylesheet it has,
changes only what the reason concerns — a reason about the look is a change to the stylesheet — and is held
to the same checking and budget. A redraw that only restyles now counts as a redraw.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/surfaces.py`, `scripts/agents/harness.py`,
`commands/mockups.md` and `skills/storyboard/SKILL.md`. Nothing to change in `harbour.json`: the defaults
apply where it has no row for the drawing.

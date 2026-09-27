PATCH

**A slice with a screen now has its design decided before it is built and reviewed on the rendered screen
before the demo, as two `/drive` rungs, not as a sentence nothing asked anyone to act on.** Three new screens
reached a demo with every `check-ux-gates` gate green and still showed default-blue links, labels crammed
against their fields, a raw UUID and a diagram drawn as a bare rectangle: the design skills were installed and
`AGENTS.md` named them, but no stage of the ladder asked for them, so a delegate briefed from the plan styled
from the tokens, ran the gates and stopped. Where the project has a browser app:

- **Screen design**, between *Plan and tasks* and *Implementation*: `docs/design.md` holds the decision each
  screen needs, `skills/frontend-design`'s second pass has been over the plan, and `tasks.md` records a
  `Designed:` line per screen under `## Design review`.
- **Design review**, between *Implementation* and *Convergence*: each screen rendered, a screenshot per state,
  read against `skills/web-interface-guidelines`, every finding fixed or given its reason on a `Reviewed:`
  line. A green gate is evidence for this rung, never the rung.
- A slice with no screen says `No screen in this slice` once, and both rungs are done.

The ladder names only what every browser app ships with. The `uipro` extension's `AGENTS.md` block now puts its
search into *Screen design*, and the `ux-gates` block puts `make check-ux-gates` and the kit's `design-review.md`
and `wcag-checklist.md` into *Design review*, so a project that did not adopt them reads about neither. The
`drive-tasks` brief and the event-modelling tasks template carry the steps inside the styling task and leave the
`## Design review` heading. The demo stop checks the record. Under `/cruise`, `drive-hand` also looks at every
screen on its browser walk and writes what it sees as `design:` notes in the demo log's **Feedback**.

**Catch-up.** `slipwai migrate` brings the ladder, the brief and the template. A slice already past
*Implementation* whose `tasks.md` has no `## Design review` enters `/drive` at *Screen design*: write the
`Designed:` lines for the screens that were built, then run the review. In a project that adopted `uipro` or
`ux-gates`, run `make agents` once so its `AGENTS.md` block names the rung, and commit the result.

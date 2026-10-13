PATCH

**The hand reads the screens against what the project decided, and a design finding is now a verdict.** The
demo delegate looked at every screen already, but only for four named defects and only as a note: the brief
said a label, a colour or a layout was "never a reason to withhold acceptance". So the one rung that reads
`skills/web-interface-guidelines` was *Design review*, which is the session reviewing what it just built —
and under `/cruise` no person sees the screen before the next slice is built on it.

Where a slice has a screen and the hand reached it in a browser, it now puts each screen into every state it
can be in, screenshots each, and reads the screenshots against the approved mock state, `docs/design.md` and
the constitution's design notes, and `skills/web-interface-guidelines` — the project's own decisions winning
wherever they and a general rule disagree. A finding one of those covers is a `behaviour` verdict re-entering
at *Design review* with the screenshot. Two things are not: a finding the slice's `## Design review` record
already names with the reason it was left, which stands as recorded, and taste none of them speaks to, which
is still a `design:` note for the next slice. Where it could not drive a browser it says the screens were not
read, rather than letting the verdict imply they were.

Nothing else moved: the three verdict words, the demo log's shape and what `check-decisions` holds it to are
unchanged, and the hand still edits nothing.

**Catch-up:** regenerate to get the reworded brief — `slipwai upgrade`, or copy
`agents/sail-demo-hand.md`.

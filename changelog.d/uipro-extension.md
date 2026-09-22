MINOR

**`./init --extension uipro` installs UI/UX Pro Max as a skill in the project's own catalogue.** It is an
offline design-system generator — a Python search over local data that answers which pattern, style,
palette, type pairing, chart types and UX rules fit a product of this kind — and it lands in the root
`skills/` as one skill, so `make agents` projects it into every harness and `check-agents` holds the
projections to it, rather than as the fifteen per-harness copies its own installer would write. The copy is
ignored by Git and reproducible from the pinned CLI version. The `AGENTS.md` block says when to reach for it
(the first screen `docs/design.md` has no decision for), that the persisted `design-system/<slug>/MASTER.md`
is committed as the input `tokens.css` is filled from, and that the design page stays the one a slice reads
first and wins where the two disagree. A project with no browser app is refused with the command that would
change that.

**Catch-up.** Nothing arrives by merge. Adopt it with `./init --extension uipro` where a browser app exists;
a checkout that adopted it elsewhere sees the pointer and reinstalls with the same command.

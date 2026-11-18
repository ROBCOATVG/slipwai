MINOR

**Whether a slice opens a flag now follows from where the product is.** Before this change, every project
with a target opened a flag from its first slice, including one nobody used yet. lean-coffee-club's first
two slices both stalled on flags no user needed.

`project.json` now records `state`:

- **pre-launch**: no production yet, or one only the team sees. Merges are open: visible at once, and no
  flag is opened.
- **pilot**: known pilot users. Merges use keystone mode: each capability's entry point lands with its last
  slice, and no flag is opened.
- **live**: real users. Merges are flagged, as before.

The release stage, `/cruise`'s stops, `AGENTS.md` and `check-slice-scope` all read the state from
`scripts/agents/release_state.py`. A new project starts at `pre-launch`. A person moves the state, with an
ADR:

```
slipwai release-state <state> --why '<reason>'
```

The same move is available as `python3 scripts/agents/release_state.py --set <state> --why '<reason>'`. A
pilot product names each capability's entry in `specs/<feature>/keystones.yaml`, beside the chart.

**A project with no state recorded merges flagged, as it always has.** A migration never guesses the state.
The cruise setting `release: flagged | park` now applies only to a live product.

**Catch-up:** run `slipwai release-state` in the project. It prints `state: unrecorded` and the mode the
project now merges under. Record the real state with `slipwai release-state <state> --why '<reason>'`, and
commit `project.json` and the new ADR together. If the product is pre-launch, `slipwai release-state` lists
every flag that mode does not need. Strip each one in a change of its own, together with its reads and its
off-path tests. A slice still in flight that opened a flag drops it when it next merges `main`.

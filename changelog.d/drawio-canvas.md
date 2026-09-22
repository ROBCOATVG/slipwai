MINOR

**An event-profile project now commits a draw.io canvas of its model, and `make verify` proves it current.**
Everything `make model` draws — the slice diagrams, the README's segments, the whole-timeline SVG, the
browsable page — is rendered through a headless browser, which is why none of it could ever be committed or
checked on every commit: a picture nothing checks quietly stops matching `model.yaml`, and that is how a
model stops being trusted. `make model-drawio` writes `docs/event-model/model.drawio`, the whole timeline as
one editable draw.io page, from arithmetic and a string — no browser, no account, no network — and
`make check-drawio`, inside `verify`, regenerates it in memory and fails on a missing or stale file with the
fix in its message. The canvas advances in the same order as the Mermaid diagram, puts each box in the same
lane, draws the same arrows and uses the same colours, because the lane and the arrows are answered once in
`scripts/event-model/model.ts` and the palette is one table both renderers read. A read of an event modelled
far earlier detours below the bands rather than crossing every box in between, every reader of one event
shares that event's corridor, and a caption under each reader names every event it reads.
`make model-drawio-test` runs the planner's and serialiser's own tests. `make model` and `make check-model`
are unchanged.

**Catch-up.** After merging, run `make model-drawio` and commit `docs/event-model/model.drawio`; until then
`make verify` fails on the missing canvas, and says so. `make verify` now needs Node in every event-profile
project — it installs `scripts/event-model`'s three dependencies on first run — and the regenerated
`.github/workflows/verify.yml` sets a Node up where the project has none of its own.

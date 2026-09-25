MINOR

**The UX render gates are spread from the first screen: side by side, sharded across six CI jobs, and scoped
to what a pull request changed.** Each per-file render gate launches its own browser, four per preview, so
their cost is linear in `screens/`: a generated project with 225 previews spent 24 minutes of a 33-minute
`verify` in them. `check-ux-gates` now runs its gates concurrently (`UX_GATES_JOBS`, one per processor by
default); `UX_GATES_SHARD=k/n` runs every n-th gate from the k-th, so n jobs cover every gate exactly once;
and `UX_GATES_SINCE=<ref>` renders only the previews whose own file, or a local stylesheet they link or
`@import`, changed since the merge base with `<ref>` — every preview again when the gate, the extension, the
lockfile or `verify.yml` moved, or when Git cannot say. The file gate over `src/` always runs. And
`./init --extension ux-gates` now writes a `ux-gates` job into `verify.yml`, between markers: six shards, each
installing the pinned kit and Playwright's Chromium and setting `UX_GATES_REQUIRE=1`, scoped to the base commit
on a pull request and whole on `main`. Until now the generated CI never installed the kit, so its render gates
were reported skipped there on every run; they are now measured before a deploy, which waits on `verify`.

**Catch-up.** Run `./init --extension ux-gates` once in a project that adopted the gates, and commit the job it
adds to `.github/workflows/verify.yml`. A project that wrote its own UX-gate job should remove it first.

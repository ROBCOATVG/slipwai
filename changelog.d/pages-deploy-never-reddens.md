PATCH

**A Pages deploy that fails no longer turns trunk red.** The event-model workflow publishes the model's
page to GitHub Pages. In a repository where Pages is not turned on, that deploy gets a 404. The failed job
used to fail the whole run, so the harbourmaster read trunk as red and refused every merge, over a
repository setting that no agent may change. The deploy job now has `continue-on-error: true`: it still
runs, and still shows as failed, but the run is judged on the job that renders and checks the model.

**Catch-up:** `slipwai migrate` rewrites `.github/workflows/event-model.yml`. To publish the page, turn
Pages on: Settings > Pages > Source: GitHub Actions.

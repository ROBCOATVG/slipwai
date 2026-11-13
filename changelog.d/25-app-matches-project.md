MINOR

**The app checks that it is the same release as the project it opens.** A project records the newest
slipwai that wrote it, `generator.updatedWith` in `project.json`. 2.1 moved a run's state under
`.slipwai/run/`, so an older app opened on a migrated project would show an empty board and write your
answers where no captain reads them. Now:

- If the project is newer than the app, every page says so, and the app changes nothing until you update
  it.
- If the project is older than the app, the board works and suggests `slipwai migrate`.

From 2.1, the app also tells the scripts it starts which release it is. The project's own
`scripts/agents/fleet.py` then refuses `start`, `relight` and `tell` from an older app. Running it yourself
from a terminal is never refused. An app older than 2.1 cannot be held to this, so update the app at the
same time as you migrate.

**Catch-up:** `slipwai migrate` brings in the new `fleet.py`. Update the app in the same sitting.

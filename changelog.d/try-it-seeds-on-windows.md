PATCH

**Try it opens the seed door on Windows.** It handed `make` the given events' file as a Windows path, and the
shell `make` runs read each backslash as an escape, so the door was given a file that was not there and every
story with a `given` failed before its first step. And when a project has no door yet, Try it no longer promises
a TypeScript file whatever the service's language.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/try_it.py`.

PATCH

**`slipwai migrate` no longer writes anything under `infra/`.** Those files describe resources that
already exist — a Terraform resource address is state, not a name — and which of them are real is not
something a factory can know. Your stack now crosses exactly as it is, and what this version would have
changed there is listed in `.slipwai/catch-up.md` for you to take deliberately, `tofu plan` first.

This was learned from a crossing that re-added a factory Terraform file under its version 2 name, into a
project that had deleted it months earlier and written its own beside it. Nothing caught it: the rename
means the base and the offering share a path the project has never had, so "we deleted this" reads as
"the factory added a file". The next deploy stopped on a duplicate local value, which is the harmless end
of what that class of change can do — the same merge could as easily have proposed replacing a user pool.

**Catch-up:** nothing. A project already crossed keeps whatever the earlier crossing wrote; if that
included factory `infra/` files you had deleted, delete them again and the next crossing leaves them gone.

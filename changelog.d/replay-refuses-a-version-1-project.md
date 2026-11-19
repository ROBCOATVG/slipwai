PATCH

**`slipwai replay` refuses a project version 1 wrote, and points at `slipwai migrate --check`.** A replay
describes itself as `migrate` without the merge, to look at first, and for a version 1 project it was not:
`migrate` crosses such a project against a base that release rebuilds, and carries its `eventSourced` answer
into the write-model choice. A bare replay did neither, so it offered an event-sourced service back as
state-stored, with a repository, a states migration and the event store deleted — a deletion the migration
never makes, shown to exactly the person careful enough to look first. `replay` now says the upgrade is a
crossing and names `slipwai migrate --check`, which prepares the real one, lists its conflicts and changes
nothing. A project already on version 2 replays as before.

**Catch-up:** nothing; a version 1 project runs `slipwai migrate --check` to look, then `slipwai migrate`.

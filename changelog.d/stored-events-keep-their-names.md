PATCH

**`check-model` no longer fails an event that was already in the log when its naming rules arrived.**
`event-is-not-crud` and `event-is-not-negative` came with version 2 and were asked of every event in the
model. A project crossing from version 1 with `WorkspaceCreated` or `DocumentNotReceived` already written
could only comply by renaming a stored event, which nothing can do, so `make verify` stayed red.

The crossing now writes `.specify/event-names-from.json`, once: the events of the slices that are
`implemented` when it runs. Both checkers pass exactly those names on exactly those two rules, and hold
every event named afterwards to both. An event of a slice that is only modelled or planned is not listed,
because it has not been written and can still be renamed. A project made with version 2 has no such file
and no exemption. A file that is not a list of names fails the gate and says what it should hold. The
catch-up page lists the names kept.

**Catch-up:** `slipwai migrate`; a project crossing from version 1 gets the file with the crossing. A project
that already crossed runs `slipwai migrate` for the corrected gate, then writes the file once by hand and
commits it — `{"events": ["WorkspaceCreated", "DocumentNotReceived"]}`, naming only the events of
`implemented` slices that `make check-model` refuses — because the crossing that would have written it is
behind it.

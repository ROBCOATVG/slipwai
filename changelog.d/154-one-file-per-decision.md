MINOR

**A decision, and a slice's adversary rows, are each written as a file of their own, and the two logs are
rendered from them.** Every slice appended to one `specs/<feature>/decisions.md` and one `adversary-log.md`,
and when two slices running abreast merged, the union of their two endings dropped the lines the endings
shared — most often a record's `- **Status:** standing` — so `check-decisions` refused the next merge (six
repair commits on one project in three days). Now a decision is `specs/<feature>/decisions/D<n>.md` and a
slice's rows are `specs/<feature>/adversary-log/<slice>.md`; `make decisions` renders the two logs from them,
`make check-rendered` holds the logs to them, `check-decisions` holds each record to one decision named for its
id, and `check-slice-scope` lets a slice write its own. Two slices never write one file, and where both changed
the rendered log the harbourmaster renders it again at the merge instead of weaving it. An entry a page older
than this appends to the log is not lost: `make decisions` moves it into a record of its own.

**Catch-up:** `slipwai migrate` splits each feature's existing `decisions.md` and `adversary-log.md` into one
file per entry and renders both logs again, in its commit after the merge — the split loses no entry and keeps
every number. A branch in flight that still appends to a log is carried across at its merge; anyone resolving
a conflict in either log by hand takes either side and runs `make decisions`.

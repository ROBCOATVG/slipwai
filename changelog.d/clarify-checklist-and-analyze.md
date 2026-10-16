MINOR

**The specification is clarified and checked, and a slice is analysed before it is implemented.** After `/speckit-specify`, `/sail` runs `/speckit-clarify`. It then runs `/speckit-checklist` and the read-only find-gaps survey in parallel against the clarified specification; after both return, the host runs the find-gaps conversation and writes confirmed answers back. After tasks, and before implementation, it runs `/speckit-analyze`: a read of the spec, the plan and the tasks, writing nothing. A finding goes back to the plan or the tasks. `/speckit-taskstoissues` is not part of the loop.

**Catch-up:** `slipwai migrate` brings the command pages, the workflow page and `docs/intake/README.md`.

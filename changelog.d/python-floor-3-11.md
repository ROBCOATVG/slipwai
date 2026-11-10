PATCH

**A project's `make check-python` and the fleet's preflight now ask for Python 3.11, as the gate scripts do.**
Both said 3.10, so a machine whose `python3` was 3.10 passed the check and then failed inside the first gate
script that imports `datetime.UTC` or `tomllib`. It is now told up front to put a newer `python3` first on
`PATH`.

**Catch-up:** `slipwai migrate` in a generated project brings the new check; nothing else changes.

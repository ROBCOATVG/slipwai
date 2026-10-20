PATCH

**A slice the captain runs in its own berth can pass `check-dispatch`.** The captain wrote `claimed` before it
started the slice's session, so clearance read the slice as running, and `make dispatch` refused to write the
ledger line for it — every commit on the slice was then refused as work no dispatch accounts for. The captain now
writes the slice's line into its berth and commits it on `slice/<id>`, and `make dispatch` in a session the
captain started writes the line for that slice rather than refusing it. Request (`R3`) and question (`Q7`) ids in
a commit subject are no longer read as slices.

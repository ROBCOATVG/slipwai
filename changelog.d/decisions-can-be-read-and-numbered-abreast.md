PATCH

**A decision can be marked read from the board, and a person's own answer is never owed a read.** The
decision ceiling counts decisions with no `read` receipt, and nothing but a hand-written line could make
one: hr-test-2 parked over its ceiling with a board that showed every decision and could take none off.
*Waiting on you* now lists a stream's unread decisions with **Mark read** on each and one for all of them,
which writes the receipt the ceiling counts. A decision the captain recorded as `decided_by: human` —
a person's answer to a park, `decide for me` among them — no longer counts toward the ceiling.

**Slices worked abreast no longer mint the same decision number.** Each delegating session took the next
`D<n>` after the last entry it could see, so two slices came back with D28 to D30 apiece.
`scripts/agents/ids.py reserve decision <count> <slice>` hands out numbers under a lock shared by every
berth, past every number on trunk and on every `slice/*` branch, and `/cruise` now allocates with it.
`check-decisions.py` refuses a number used twice and no longer asks for contiguous, in-order numbering,
which slices merging in their own order could not meet.

**Catch-up:** `slipwai migrate` (or `slipwai replay` and a merge, on 2.x) brings the corrected
`scripts/agents/inbox.py`, `ids.py`, `check-decisions.py` and `commands/cruise.md`. A fairway parked over
the ceiling is let go by marking its decisions read on the board.

PATCH

**A slice's `demo` and `seeded` lines count at its branch's head, whichever run wrote them, and a missed
gate names everything still owed at once.** The captain counted only the lines the run that just ended had
written, and its refusal named the first missing line of an if/else chain. manda's S114 spent its three
attempts at one commit that way: run 1 demoed and was told it had not seeded, run 2 seeded and was told it
had not demoed, run 3 demoed again and was told it had not seeded, and it parked for a person with nothing
wrong with its code. The harbourmaster's own hold counted any `seeded` line ever written, so the two could
disagree about the same slice.

- One rule, in the new `scripts/agents/evidence.py`, read by the captain's gate and the harbourmaster's
  hold: a line counts while the code it was written against is the branch's. A later commit makes it stale
  where it changes the code or, for `seeded`, the slice's `try-it.json`; a commit that only adds records —
  under `specs/`, a fairway's careen, the captain's dispatch ledger under `.slipwai/` — does not.
- `deck_line.py demo` now writes the commit it was walked at, as `seeded` always has. A line that records
  no commit is read as before: the captain counts it only where this turn wrote it, the harbourmaster
  wherever it is.
- The refusal, and the park it becomes, lists the marks, the demo and the seed still owed in one message,
  says when a line is stale rather than missing, and tells the run to write what is owed after its last
  commit.
- A run that finishes with its evidence whole at the head, whichever runs wrote it, is through its gate and
  spends no further attempt.
- A fairway's careen can write its `demo` line: `deck_line.py demo --slice <fairway>-careen` was refused as
  a slice on no chart, so manda's `modelling-careen` parked seven times with every row done. It is accepted
  where `fairways/<fairway>/careen.md` exists, and a careen still sets no mark.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/evidence.py` and the changed `captain.py`,
`harbourmaster.py` and `deck_line.py`. Nothing else changes in a project.

```typescript
// The todo list is a table, folded from earlier slices' events by the checkpointed runner in
// `catch-up-checkpoint-transaction` and read here. It is still a projection — `PlaceClaimed` inserts the
// row, `SeatAllocated` removes it — so it rebuilds from position zero like any other. What it is not is a
// fold over what the current request happened to write: a standalone run has no request to ask.

/** One row of the todo list: a claim with no seat yet. */
export type OwedSeat = Readonly<{ registrationId: string; claimedAt: string }>;

export interface SeatsOwed {
  /** Up to `limit` rows no other runner is holding, for the life of this transaction. */
  claimBatch(limit: number): Promise<readonly OwedSeat[]>;
}
```

```sql
-- Claiming is what lets a second runner help rather than queue: SKIP LOCKED takes the next unlocked row
-- instead of blocking behind the first. Note what it is *not* doing — it is not what makes the work happen
-- once. Between issuing AllocateSeat and the projection applying SeatAllocated the row is still here, so a
-- run that overlaps its predecessor can re-issue the command; the Decider refuses it, because
-- `folds: [SeatAllocated, SeatReleased]` is its own stream's history and a seat already allocated is a
-- rejection. Correctness comes from that invariant. Claiming only stops two runners paying for the same
-- work twice.
SELECT registration_id, claimed_at
  FROM seats_owed
 ORDER BY claimed_at
 LIMIT $1
   FOR UPDATE SKIP LOCKED
```

```typescript
/**
 * Claim work, decide, issue the command — through the same use case a person would have driven.
 *
 * Invoked in-request for latency *and* runnable standalone: on a timer, at startup, after a crash. The
 * standalone run is the point of the pattern. It discovers work it did not create, and it recovers what a
 * request that died halfway abandoned — neither of which a per-request fold can do at all, because it only
 * knows the streams the request in front of it wrote.
 */
export async function allocateOwedSeats(
  owed: SeatsOwed,
  allocate: (command: AllocateSeat) => Promise<AllocationOutcome>,
  batch = 100,
): Promise<number> {
  let issued = 0;
  for (const claim of await owed.claimBatch(batch)) {
    const outcome = await allocate({ registrationId: claim.registrationId });
    // A refusal appends nothing, so nothing removes the row and the next run sees it again. That is the
    // compensation gap: decide whether the refusal becomes an event or the todo list detects the age of the
    // claim, and write the decision down — a processor that silently retries forever is neither.
    if (outcome.outcome === 'allocated') issued += 1;
  }
  return issued;
}
```

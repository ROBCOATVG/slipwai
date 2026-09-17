/**
 * The catch-up runner: how an `async` read model is maintained, and how it is rebuilt.
 *
 * Two verbs over the two ports, and no I/O of its own — which is why it is here beside the application
 * rather than under `adapters/`, and why its tests need no database.
 *
 * ```ts
 * await catchUp(store, checkpoints, view, { owner: 'worker-1', clock: () => new Date() });
 * await rebuild(store, checkpoints, view, { owner: 'worker-1', clock: () => new Date() });
 * ```
 *
 * `catchUp` is one pass: it reads the log from the projection's checkpoint, applies it in batches, and
 * advances the checkpoint **inside the same transaction as the rows it derived**. `catchUpEach` is that
 * pass over every projection at once, and what loops over *it* is the framework:
 * `projections-plugin.ts` is a Fastify plugin, whose `onClose` hook stops the timer with
 * the server. A project with only `live` and `inline` read models registers nothing and runs nothing
 * here.
 *
 * `rebuild` is the same pass from zero, with the view emptied first. It is what makes a read model
 * disposable: a projection with a bug is fixed by changing the fold and running this, not by patching
 * rows. It holds the lease across the empty *and* the re-fold, so a worker cannot catch up into a
 * half-empty view.
 *
 * ## Why exactly-once needs nothing else here
 *
 * The checkpoint moves in the view's own transaction, so the pair is atomic: a crash before the commit
 * leaves both untouched, and the next pass reads the same batch again. Nothing is applied twice and
 * nothing is skipped, and there is no idempotency key to get wrong.
 *
 * That guarantee is the transaction's, not this file's, and it is worth knowing exactly where it stops. A
 * projection whose rows are **not** in the same database as the checkpoint — an HTTP search index, a
 * cache, a file — cannot join that transaction, and for those the fold has to be idempotent on
 * `globalPosition` instead: record the position with the row and ignore an event at or below what the row
 * already holds. The lease reduces how often that matters; it never removes the need.
 *
 * ## Why a lease and not a lock
 *
 * Exactly one worker should advance a projection, and a lease with an expiry is how that survives the
 * worker dying. What it is *not* is the thing that makes the work happen once — the transaction above is.
 * A projection is a fold and folds are cheap; the lease is there to stop every replica burning the same
 * log, not to hold the system together.
 */

import type { CommittedEvent, EventStore } from './application/ports/events.js';
import type { CheckpointStore, Lease, Projection } from './application/ports/read-models.js';
import { FROM_THE_BEGINNING } from './application/ports/read-models.js';

/**
 * How long a claim is good for. Long enough that a slow batch does not lose it, short enough that a dead
 * worker's projection resumes within a stand-up rather than a support call.
 */
export const DEFAULT_LEASE_MS = 30_000;

/**
 * How many events one transaction applies. A batch is one transaction, so this trades how much work a
 * crash repeats against how long a single transaction holds its locks.
 */
export const DEFAULT_BATCH_SIZE = 500;

/**
 * The clock, as a function, because a pass long enough to need its lease renewed needs the time *again* —
 * which an instant passed in cannot give it. Everywhere else in this project an instant is a typed input;
 * here the input is the clock itself, and a test hands over a fixed one.
 */
export type Clock = () => Date;

export type RunnerOptions = Readonly<{
  owner: string;
  clock: Clock;
  ttlMs?: number;
  batchSize?: number;
}>;

/**
 * What one pass did.
 *
 * `leased` is separate from `applied` on purpose: "nothing to apply" and "somebody else is already
 * applying it" are both a quiet zero, and a caller that cannot tell them apart will read the first as an
 * empty log and the second as a finished rebuild.
 */
export type Advance = Readonly<{ applied: number; leased: boolean }>;

/**
 * Apply everything the log has that this projection has not, once.
 *
 * Returns without doing anything if another worker holds the lease — that is the ordinary case for every
 * replica but one, and not a failure.
 */
export async function catchUp(
  store: EventStore,
  checkpoints: CheckpointStore,
  projection: Projection,
  options: RunnerOptions,
): Promise<Advance> {
  const ttlMs = options.ttlMs ?? DEFAULT_LEASE_MS;
  const lease = await checkpoints.claim(projection.name, options.owner, options.clock(), ttlMs);
  if (lease === undefined) return { applied: 0, leased: false };
  try {
    return {
      applied: await applyFromTheCheckpoint(store, checkpoints, projection, lease, options),
      leased: true,
    };
  } finally {
    await checkpoints.release(lease);
  }
}

/**
 * One pass over every projection there is, which is what a scheduled worker calls.
 *
 * No projection's failure hides another's. Each is attempted, the advances come back by name, and a pass
 * with failures ends by throwing one `AggregateError` carrying all of them — so the caller's logger sees
 * every one, the next tick tries again, and a projection whose fold is broken does not quietly starve
 * every projection after it in the list.
 *
 * Sequential rather than `Promise.all`, and that is deliberate: passes are cheap, the point of the lease
 * is to keep one worker on one projection, and a fan-out here would put every projection's transaction in
 * flight against the same pool at once.
 */
export async function catchUpEach(
  store: EventStore,
  checkpoints: CheckpointStore,
  projections: readonly Projection[],
  options: RunnerOptions,
): Promise<Record<string, Advance>> {
  const advances: Record<string, Advance> = {};
  const failures: unknown[] = [];
  for (const projection of projections) {
    try {
      advances[projection.name] = await catchUp(store, checkpoints, projection, options);
    } catch (failure) {
      failures.push(failure);
    }
  }
  if (failures.length > 0) {
    throw new AggregateError(failures, `${failures.length} projection(s) failed to catch up`);
  }
  return advances;
}

/**
 * Empty the view, put its checkpoint back to zero, and fold the whole log into it again.
 *
 * The reset and the checkpoint go back together, in one transaction, because a view emptied without its
 * checkpoint is a permanently empty view and a checkpoint reset without its view is a doubled one.
 */
export async function rebuild(
  store: EventStore,
  checkpoints: CheckpointStore,
  projection: Projection,
  options: RunnerOptions,
): Promise<Advance> {
  const ttlMs = options.ttlMs ?? DEFAULT_LEASE_MS;
  const lease = await checkpoints.claim(projection.name, options.owner, options.clock(), ttlMs);
  if (lease === undefined) return { applied: 0, leased: false };
  try {
    await store.inUnitOfWork(async () => {
      await projection.reset();
      await checkpoints.record(projection.name, FROM_THE_BEGINNING);
    });
    return {
      applied: await applyFromTheCheckpoint(store, checkpoints, projection, lease, options),
      leased: true,
    };
  } finally {
    await checkpoints.release(lease);
  }
}

/**
 * Batch after batch until the log runs out, holding `lease` throughout.
 *
 * The checkpoint is re-read each time round rather than tracked in a local, so a batch that rolled back is
 * read again instead of being skipped by a variable the database never agreed with.
 */
async function applyFromTheCheckpoint(
  store: EventStore,
  checkpoints: CheckpointStore,
  projection: Projection,
  lease: Lease,
  options: RunnerOptions,
): Promise<number> {
  const ttlMs = options.ttlMs ?? DEFAULT_LEASE_MS;
  const batchSize = options.batchSize ?? DEFAULT_BATCH_SIZE;
  let applied = 0;

  for (;;) {
    const position = await checkpoints.positionOf(projection.name);
    const batch = await take(store.readAll(position), batchSize);
    const last = batch.at(-1);
    if (last === undefined) return applied;

    await store.inUnitOfWork(async () => {
      await projection.apply(batch);
      // The next position, not the last one applied: what `positionOf` promises is where to resume, and
      // an off-by-one here re-applies one event forever.
      await checkpoints.record(projection.name, last.globalPosition + 1);
    });
    applied += batch.length;

    if (batch.length < batchSize) return applied;
    if (
      (await checkpoints.claim(lease.projection, lease.owner, options.clock(), ttlMs)) === undefined
    ) {
      // The lease lapsed mid-pass and somebody else took it: stop where the checkpoint is, which the new
      // owner will read. Losing a lease is not an error — it is a slow pass.
      return applied;
    }
  }
}

/** The first `count` events of a replay, and no more of it read than that. */
async function take(
  events: AsyncIterable<CommittedEvent>,
  count: number,
): Promise<CommittedEvent[]> {
  const batch: CommittedEvent[] = [];
  for await (const event of events) {
    batch.push(event);
    if (batch.length === count) break;
  }
  return batch;
}

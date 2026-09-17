import type { CheckpointStore, Lease } from '../../application/ports/read-models.js';
import { FROM_THE_BEGINNING } from '../../application/ports/read-models.js';
import type { InMemoryDatabase, InMemoryEventStore } from './event-store-memory.js';

/**
 * In-memory checkpoint adapter, on the same "connection" as the in-memory event store.
 *
 * Built from the store rather than standing alone, which is the rule every checkpoint adapter here
 * follows: `record` has to land in the same transaction as the view write it accounts for, and an adapter
 * that does not share the store's unit of work cannot do that however carefully it is called.
 *
 * What it can prove: that a projection resumes from where it stopped, that one worker at a time advances
 * it, that a lease expires, and that a batch which fails leaves both the view and the checkpoint where
 * they were. What it cannot prove is a genuine race between two workers, because nothing here runs
 * concurrently — `make test-integration` is where two connections contend for one lease.
 */
export function createInMemoryCheckpointStore(store: InMemoryEventStore): CheckpointStore {
  const database: InMemoryDatabase = store.database;

  return {
    positionOf: async (projection: string): Promise<number> =>
      database.checkpoints.get(projection) ?? FROM_THE_BEGINNING,

    record: async (projection: string, position: number): Promise<void> => {
      database.checkpoints.set(projection, position);
    },

    claim: async (
      projection: string,
      owner: string,
      now: Date,
      ttlMs: number,
    ): Promise<Lease | undefined> => {
      const held = database.leases.get(projection);
      if (held !== undefined && held.owner !== owner && held.expiresAt > now) return undefined;
      const expiresAt = new Date(now.getTime() + ttlMs);
      database.leases.set(projection, { owner, expiresAt });
      return { projection, owner, expiresAt };
    },

    release: async (lease: Lease): Promise<void> => {
      const held = database.leases.get(lease.projection);
      if (held?.owner === lease.owner) database.leases.delete(lease.projection);
    },
  };
}

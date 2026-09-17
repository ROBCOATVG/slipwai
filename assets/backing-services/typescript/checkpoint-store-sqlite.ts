import type { CheckpointStore, Lease } from '../../application/ports/read-models.js';
import { FROM_THE_BEGINNING } from '../../application/ports/read-models.js';
import type { SqliteEventStore } from './event-store-sqlite.js';

/**
 * SQLite checkpoint adapter, on the event store's own connection.
 *
 * Built from the store rather than from a location, and that is the point: `record` has to commit in the
 * same transaction as the view rows it accounts for, so it has to be the same connection. Two adapters
 * opening the same file are two connections and two transactions, and a checkpoint in its own transaction
 * is a race with a number in it.
 *
 * The lease is claimed inside `BEGIN IMMEDIATE`, which takes SQLite's single write lock, so the
 * read-then-write is atomic without anything clever. What SQLite cannot do here is prove that two
 * *processes* contend correctly, because it serialises them; `make test-integration` proves that against
 * Postgres.
 */

const POSITION_OF = 'SELECT position FROM projection_checkpoints WHERE projection = ?';

/**
 * `updated_at` moves with the position, so "is this projection stuck" is answerable from the table rather
 * than from a log somewhere.
 */
const RECORD = `
  INSERT INTO projection_checkpoints (projection, position)
  VALUES (?, ?)
  ON CONFLICT (projection) DO UPDATE
    SET position = excluded.position,
        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
`;

/**
 * Take the lease when nobody holds it, when this owner already holds it (which is how a long catch-up
 * renews), or when the holder's lease has lapsed. Refuse otherwise — and the refusal is the `WHERE` on the
 * update, so the whole decision is one statement and cannot be split.
 */
const CLAIM = `
  INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
  VALUES (?, 0, ?, ?)
  ON CONFLICT (projection) DO UPDATE
    SET lease_owner = excluded.lease_owner,
        lease_expires_at = excluded.lease_expires_at
    WHERE projection_checkpoints.lease_owner IS NULL
       OR projection_checkpoints.lease_owner = excluded.lease_owner
       OR projection_checkpoints.lease_expires_at <= ?
`;

const RELEASE = `
  UPDATE projection_checkpoints
  SET lease_owner = NULL, lease_expires_at = NULL
  WHERE projection = ? AND lease_owner = ?
`;

/**
 * A fixed-width UTC instant, because SQLite compares these as strings.
 *
 * `toISOString()` is exactly that shape — same width, same zone, always — which is what makes
 * `lease_expires_at <= ?` a chronological comparison rather than an alphabetical one. Postgres has
 * `timestamptz` and needs none of this; the adapter is where the difference stops.
 */
const asText = (instant: Date): string => instant.toISOString();

export function createSqliteCheckpointStore(store: SqliteEventStore): CheckpointStore {
  const { database, inUnitOfWork } = store.session;

  return {
    positionOf: async (projection: string): Promise<number> => {
      const row = database.prepare(POSITION_OF).get(projection) as { position: number } | undefined;
      return row === undefined ? FROM_THE_BEGINNING : Number(row.position);
    },

    /**
     * No commit here. Call it inside the store's unit of work, with the writes it accounts for; outside
     * one, SQLite commits it on its own, which is the mistake this comment names.
     */
    record: async (projection: string, position: number): Promise<void> => {
      database.prepare(RECORD).run(projection, position);
    },

    claim: async (
      projection: string,
      owner: string,
      now: Date,
      ttlMs: number,
    ): Promise<Lease | undefined> => {
      const expiresAt = new Date(now.getTime() + ttlMs);
      const taken = await inUnitOfWork(async () => {
        const result = database
          .prepare(CLAIM)
          .run(projection, owner, asText(expiresAt), asText(now));
        return result.changes !== 0;
      });
      return taken ? { projection, owner, expiresAt } : undefined;
    },

    release: async (lease: Lease): Promise<void> => {
      await inUnitOfWork(async () => {
        database.prepare(RELEASE).run(lease.projection, lease.owner);
      });
    },
  };
}

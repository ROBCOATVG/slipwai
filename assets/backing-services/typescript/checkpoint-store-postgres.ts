import type { CheckpointStore, Lease } from '../../../application/ports/read-models.js';
import { FROM_THE_BEGINNING } from '../../../application/ports/read-models.js';
import type { PostgresEventStore } from './index.js';

/**
 * Postgres checkpoint adapter, on the event store's own session.
 *
 * Built from the store rather than from a pool, and that is the point: `record` has to commit in the same
 * transaction as the view rows it accounts for, so it has to be the same client. A second pool client is a
 * second transaction, and a checkpoint in its own transaction is a race with a number in it — either the
 * view is written and the checkpoint is lost, or the checkpoint moves past rows that were rolled back.
 *
 * The claim is **one statement**. An `INSERT ... ON CONFLICT DO UPDATE ... WHERE` decides whether the
 * lease is takeable and takes it in the same breath, so there is no window between reading who holds it
 * and writing that you do. `make test-integration` is where two connections race for it for real, which
 * is the one thing no single-writer store — an in-memory fake, a file-backed one — can prove.
 */

const POSITION_OF = 'SELECT position FROM projection_checkpoints WHERE projection = $1';

/**
 * `updated_at` moves with the position, so "is this projection stuck" is answerable from the table rather
 * than from a log somewhere.
 */
const RECORD = `
  INSERT INTO projection_checkpoints (projection, position)
  VALUES ($1, $2)
  ON CONFLICT (projection) DO UPDATE
    SET position = EXCLUDED.position, updated_at = now()
`;

/**
 * Take the lease when nobody holds it, when this owner already holds it (which is how a long catch-up
 * renews), or when the holder's has lapsed. Refuse otherwise — and the refusal is the `WHERE` on the
 * update, so the whole decision is one statement and cannot be split by another worker doing the same
 * thing a microsecond later.
 */
const CLAIM = `
  INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
  VALUES ($1, 0, $2, $3)
  ON CONFLICT (projection) DO UPDATE
    SET lease_owner = EXCLUDED.lease_owner,
        lease_expires_at = EXCLUDED.lease_expires_at
    WHERE projection_checkpoints.lease_owner IS NULL
       OR projection_checkpoints.lease_owner = EXCLUDED.lease_owner
       OR projection_checkpoints.lease_expires_at <= $4
  RETURNING position
`;

const RELEASE = `
  UPDATE projection_checkpoints
  SET lease_owner = NULL, lease_expires_at = NULL
  WHERE projection = $1 AND lease_owner = $2
`;

export function createPostgresCheckpointStore(store: PostgresEventStore): CheckpointStore {
  const { query, inUnitOfWork } = store.session;

  return {
    positionOf: async (projection: string): Promise<number> => {
      const result = await query<{ position: string }>(POSITION_OF, [projection]);
      const row = result.rows[0];
      return row === undefined ? FROM_THE_BEGINNING : Number(row.position);
    },

    /**
     * No commit here. Call it inside the store's unit of work, with the writes it accounts for; outside
     * one it runs on a pool client of its own and commits alone, which is the mistake this comment names.
     */
    record: async (projection: string, position: number): Promise<void> => {
      await query(RECORD, [projection, position]);
    },

    claim: async (
      projection: string,
      owner: string,
      now: Date,
      ttlMs: number,
    ): Promise<Lease | undefined> => {
      const expiresAt = new Date(now.getTime() + ttlMs);
      const taken = await inUnitOfWork(async () => {
        const result = await query(CLAIM, [projection, owner, expiresAt, now]);
        return (result.rowCount ?? 0) > 0;
      });
      return taken ? { projection, owner, expiresAt } : undefined;
    },

    release: async (lease: Lease): Promise<void> => {
      await inUnitOfWork(async () => {
        await query(RELEASE, [lease.projection, lease.owner]);
      });
    },
  };
}

import { Pool } from 'pg';
import { afterAll, describe, expect, it } from 'vitest';

import { createPostgresCheckpointStore } from '../../src/adapters/driven/event-store-postgres/checkpoint-store-postgres.js';
import { createPostgresEventStore } from '../../src/adapters/driven/event-store-postgres/index.js';
import { checkpointStoreContract, NOW } from '../contract/checkpoint-store-contract.js';

/**
 * The checkpoint store against real Postgres, plus the one thing only a real store can prove.
 *
 * Deliberately NOT part of `make verify`, like its sibling:
 *
 *   make services-up migrate test-integration
 *
 * The contract runs here as it does against the fakes. The test below it is the one that cannot run
 * anywhere else — two connections claiming one lease at the same instant, where exactly one must win. That
 * is the whole basis for running a projection on more than one replica.
 */

const connectionString = process.env.DATABASE_URL;
if (connectionString === undefined || connectionString.trim() === '') {
  throw new Error(
    'DATABASE_URL is unset, so there is no database to test against. Run `make test-integration`, which ' +
      'sets it, after `make services-up migrate`.',
  );
}

const pool = new Pool({ connectionString });

afterAll(async () => {
  await pool.end();
});

const pair = async () => {
  const store = createPostgresEventStore(pool);
  return { store, checkpoints: createPostgresCheckpointStore(store) };
};

checkpointStoreContract('the Postgres checkpoint store', pair);

describe('the Postgres checkpoint store under genuine contention', () => {
  /**
   * The assertion no infrastructure-free adapter can make.
   *
   * The claim is one statement — an upsert whose `WHERE` decides whether the lease is takeable — so there
   * is no window between reading who holds it and writing that you do. Being single-threaded, the
   * in-memory adapter would pass this while proving nothing; a file-backed store serialises its
   * writers, so it would too.
   */
  it('lets exactly one of many simultaneous claims win', async () => {
    const projection = `race-${crypto.randomUUID()}`;
    const now = new Date();

    const results = await Promise.all(
      Array.from({ length: 8 }, async (_unused, index) => {
        // One pool of its own per worker: two claims on one client cannot race, they queue.
        const own = new Pool({ connectionString });
        try {
          const checkpoints = createPostgresCheckpointStore(createPostgresEventStore(own));
          return await checkpoints.claim(projection, `worker-${index}`, now, 30_000);
        } finally {
          await own.end();
        }
      }),
    );

    expect(results.filter((lease) => lease !== undefined)).toHaveLength(1);
  });

  /**
   * A lease that only one process can see is not a lease. It is committed on its own, unlike a position,
   * because coordination has to be visible before the work it coordinates.
   */
  it('makes a lease visible to another connection at once', async () => {
    const projection = `visible-${crypto.randomUUID()}`;
    const other = new Pool({ connectionString });
    try {
      const first = (await pair()).checkpoints;
      const second = createPostgresCheckpointStore(createPostgresEventStore(other));

      expect(await first.claim(projection, 'worker-1', NOW, 30_000)).toBeDefined();
      expect(await second.claim(projection, 'worker-2', NOW, 30_000)).toBeUndefined();
    } finally {
      await other.end();
    }
  });
});

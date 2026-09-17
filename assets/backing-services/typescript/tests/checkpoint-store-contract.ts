import { randomUUID } from 'node:crypto';
import { beforeEach, describe, expect, it } from 'vitest';

import type { DomainEvent, EventStore } from '../../src/application/ports/events.js';
import { createCorrelationId, NO_STREAM } from '../../src/application/ports/events.js';
import type { CheckpointStore } from '../../src/application/ports/read-models.js';
import { FROM_THE_BEGINNING } from '../../src/application/ports/read-models.js';

/**
 * One contract, run against every checkpoint adapter this project has — the pairs a machine with no
 * server can build by `make test`, a real store by `make test-integration` where there is one. Two
 * adapters that pass different tests are two different ports
 * wearing one name, and with a checkpoint the day they diverge is the day a projection silently applies an
 * event twice.
 *
 * `createStores` returns the pair, not the checkpoint store alone: every adapter is built from the event
 * store it follows, because `record` has to land in the same transaction as the view write it accounts
 * for. A contract that let an adapter be constructed on its own would be a contract that permitted the one
 * mistake this port exists to prevent.
 *
 * Every case works in a freshly named projection, because the table is shared with everything else in the
 * database and a `DELETE` between tests would only prove that deletes work.
 */

/** A fixed instant, so expiry is tested by choosing the time rather than by sleeping through it. */
export const NOW = new Date('2026-09-10T12:00:00.000Z');

const A_WHILE_MS = 30_000;

const at = (offsetMs: number): Date => new Date(NOW.getTime() + offsetMs);

export function checkpointStoreContract(
  name: string,
  createStores: () => Promise<{ store: EventStore; checkpoints: CheckpointStore }>,
): void {
  describe(`${name} satisfies the checkpoint port`, () => {
    let store: EventStore;
    let checkpoints: CheckpointStore;
    let projection: string;

    beforeEach(async () => {
      ({ store, checkpoints } = await createStores());
      projection = `contract-${randomUUID()}`;
    });

    const event = (streamId: string, type: string): DomainEvent => ({
      type,
      schemaVersion: 1,
      streamId,
      payload: {},
      occurredAt: '2024-01-01T00:00:00.000Z',
      actor: { kind: 'test', id: 'checkpoints' },
      correlationId: createCorrelationId(randomUUID()),
    });

    /**
     * An unknown projection has consumed nothing, which is not an error — a rebuild has to be expressible
     * without a special case.
     */
    it('starts a projection nothing has recorded at the beginning', async () => {
      expect(await checkpoints.positionOf(projection)).toBe(FROM_THE_BEGINNING);
    });

    it('records a position and reads it back', async () => {
      await checkpoints.record(projection, 42);

      expect(await checkpoints.positionOf(projection)).toBe(42);
    });

    it('records the same projection twice without a second row', async () => {
      await checkpoints.record(projection, 7);
      await checkpoints.record(projection, 9);

      expect(await checkpoints.positionOf(projection)).toBe(9);
    });

    it('puts a position back to the beginning for a rebuild', async () => {
      await checkpoints.record(projection, 99);

      await checkpoints.record(projection, FROM_THE_BEGINNING);

      expect(await checkpoints.positionOf(projection)).toBe(FROM_THE_BEGINNING);
    });

    /**
     * The whole reason this port exists, and the reason its adapters are built from the event store: the
     * checkpoint moves in the same transaction as the rows it accounts for, so a crash before the commit
     * leaves both untouched and the next pass reads the same batch again. That is exactly-once, and there
     * is no idempotency key in it.
     */
    it('does not record a position written in a unit of work that fails', async () => {
      const stream = `checkpoint-${randomUUID()}`;

      await expect(
        store.inUnitOfWork(async () => {
          await store.append(stream, NO_STREAM, [event(stream, 'Started')]);
          await checkpoints.record(projection, 5);
          throw new Error('the view write failed');
        }),
      ).rejects.toThrow('the view write failed');

      expect(await checkpoints.positionOf(projection)).toBe(FROM_THE_BEGINNING);
      expect(await store.read(stream)).toEqual([]);
    });

    it('claims a projection for one owner', async () => {
      const lease = await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);

      expect(lease).toEqual({ projection, owner: 'worker-1', expiresAt: at(A_WHILE_MS) });
    });

    it('refuses a claim while somebody else holds an unexpired lease', async () => {
      await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);

      expect(await checkpoints.claim(projection, 'worker-2', at(1000), A_WHILE_MS)).toBeUndefined();
    });

    /** How a pass long enough to outlive its lease keeps it: the holder always succeeds. */
    it('lets the owner renew its own lease', async () => {
      await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);

      const renewed = await checkpoints.claim(projection, 'worker-1', at(10_000), A_WHILE_MS);

      expect(renewed?.expiresAt).toEqual(at(10_000 + A_WHILE_MS));
    });

    /**
     * An expiry rather than a lock, because the failure to survive is a worker that dies holding it. A
     * lock nothing releases is a projection that never advances again, and the first anybody hears of it
     * is a stale view.
     */
    it('lets another owner claim a lapsed lease', async () => {
      await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);

      const taken = await checkpoints.claim(
        projection,
        'worker-2',
        at(A_WHILE_MS + 1000),
        A_WHILE_MS,
      );

      expect(taken?.owner).toBe('worker-2');
    });

    it('makes a released lease claimable at once', async () => {
      const lease = await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);
      if (lease === undefined) throw new Error('the first claim should have been granted');

      await checkpoints.release(lease);

      expect(await checkpoints.claim(projection, 'worker-2', NOW, A_WHILE_MS)).toBeDefined();
    });

    it('does nothing when releasing a lease somebody else holds', async () => {
      await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);

      await checkpoints.release({ projection, owner: 'worker-2', expiresAt: NOW });

      expect(await checkpoints.claim(projection, 'worker-3', NOW, A_WHILE_MS)).toBeUndefined();
    });

    /**
     * The two live in one row, and moving one must not move the other: a claim that reset the position
     * would rebuild a projection every time a worker restarted.
     */
    it('does not disturb the position when the lease moves', async () => {
      await checkpoints.record(projection, 12);

      const lease = await checkpoints.claim(projection, 'worker-1', NOW, A_WHILE_MS);
      if (lease === undefined) throw new Error('the claim should have been granted');
      await checkpoints.release(lease);

      expect(await checkpoints.positionOf(projection)).toBe(12);
    });
  });
}

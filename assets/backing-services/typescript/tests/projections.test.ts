import { randomUUID } from 'node:crypto';
import { beforeEach, describe, expect, it } from 'vitest';

import { createInMemoryCheckpointStore } from '../../src/adapters/driven/checkpoint-store-memory.js';
import { createInMemoryEventStore } from '../../src/adapters/driven/event-store-memory.js';
import type {
  CommittedEvent,
  DomainEvent,
  EventStore,
} from '../../src/application/ports/events.js';
import { createCorrelationId, NO_STREAM } from '../../src/application/ports/events.js';
import type { CheckpointStore, Projection } from '../../src/application/ports/read-models.js';
import { FROM_THE_BEGINNING } from '../../src/application/ports/read-models.js';
import { catchUp, catchUpEach, rebuild } from '../../src/projections.js';

/**
 * The catch-up runner.
 *
 * Against the in-memory pair, and only that pair, because the runner has no I/O of its own: it is two
 * ports and a loop, and what these cases are about is the loop. That is also why it is here rather than
 * beside an adapter — a project that chose the in-memory store still gets every one of these.
 *
 * The guarantee the runner *rests* on — that a checkpoint recorded in a failed unit of work does not
 * move — is proved in `checkpoint-store-contract.ts`, which runs against every store adapter this
 * project has, where a rollback is the database's own rather than a restored copy. Split that way deliberately: the transaction
 * is the adapters' promise, and the loop is what this file holds to it.
 */

const NOW = new Date('2026-09-10T12:00:00.000Z');
const clockAt = (instant: Date) => () => instant;
const at = (offsetMs: number): Date => new Date(NOW.getTime() + offsetMs);

/**
 * A read model with somewhere to put the result, which is all a projection is.
 *
 * Its rows are **derived**: every one of them comes from an event, so `reset` plus a replay reproduces it
 * exactly. A column this class alone knew — a flag it set when it processed a row — could not survive
 * `reset`, and finding that out during an incident is how a rebuild becomes data loss.
 */
class Titles implements Projection {
  rows: string[] = [];
  batches = 0;

  // The name is a constructor argument rather than a literal so `Broken` below can be the same
  // projection under a different checkpoint: two suites' cases must not share one.
  constructor(readonly name: string = 'titles') {}

  async apply(events: readonly CommittedEvent[]): Promise<void> {
    this.batches += 1;
    this.rows.push(...events.map((event) => event.type));
  }

  async reset(): Promise<void> {
    this.rows = [];
  }
}

/** A projection whose write fails after it has changed something. */
class Broken extends Titles {
  constructor() {
    super('broken');
  }

  override async apply(events: readonly CommittedEvent[]): Promise<void> {
    await super.apply(events);
    throw new Error('the view write failed');
  }
}

describe('the catch-up runner', () => {
  let store: EventStore;
  let checkpoints: CheckpointStore;
  let view: Titles;

  beforeEach(() => {
    const memory = createInMemoryEventStore();
    store = memory;
    checkpoints = createInMemoryCheckpointStore(memory);
    view = new Titles();
  });

  const givenALogOf = async (...types: string[]): Promise<void> => {
    const stream = `projection-${randomUUID()}`;
    await store.append(
      stream,
      NO_STREAM,
      types.map(
        (type): DomainEvent => ({
          type,
          schemaVersion: 1,
          streamId: stream,
          payload: {},
          occurredAt: '2024-01-01T00:00:00.000Z',
          actor: { kind: 'test', id: 'projections' },
          correlationId: createCorrelationId(randomUUID()),
        }),
      ),
    );
  };

  it('applies the whole log and leaves the checkpoint past it', async () => {
    await givenALogOf('Placed', 'Paid');

    const done = await catchUp(store, checkpoints, view, {
      owner: 'worker-1',
      clock: clockAt(NOW),
    });

    expect(done).toEqual({ applied: 2, leased: true });
    expect(view.rows).toEqual(['Placed', 'Paid']);
    expect(await checkpoints.positionOf('titles')).toBe(3);
  });

  it('resumes from the checkpoint and applies nothing twice', async () => {
    await givenALogOf('Placed');
    await catchUp(store, checkpoints, view, { owner: 'worker-1', clock: clockAt(NOW) });

    await givenALogOf('Paid');
    const again = await catchUp(store, checkpoints, view, {
      owner: 'worker-1',
      clock: clockAt(NOW),
    });

    expect(again.applied).toBe(1);
    expect(view.rows).toEqual(['Placed', 'Paid']);
  });

  it('says a pass had nothing to do without touching the view', async () => {
    const done = await catchUp(store, checkpoints, view, {
      owner: 'worker-1',
      clock: clockAt(NOW),
    });

    expect(done).toEqual({ applied: 0, leased: true });
    expect(view.batches).toBe(0);
  });

  /**
   * Each batch is one transaction, so the size trades how much a crash repeats against how long one
   * transaction holds its locks. That it batches at all is what keeps a rebuild over a long log from
   * materialising the whole thing.
   */
  it('applies a long log in batches of the size it was given', async () => {
    await givenALogOf('One', 'Two', 'Three', 'Four', 'Five');

    const done = await catchUp(store, checkpoints, view, {
      owner: 'worker-1',
      clock: clockAt(NOW),
      batchSize: 2,
    });

    expect(done.applied).toBe(5);
    expect(view.batches).toBe(3);
  });

  /**
   * The ordinary case for every replica but one, and not a failure — which is why `leased` is reported
   * separately from `applied`.
   */
  it('does nothing in a second worker while the first holds the lease', async () => {
    await givenALogOf('Placed');
    await checkpoints.claim('titles', 'worker-1', NOW, 30_000);

    const blocked = await catchUp(store, checkpoints, view, {
      owner: 'worker-2',
      clock: clockAt(at(1000)),
    });

    expect(blocked).toEqual({ applied: 0, leased: false });
    expect(view.rows).toEqual([]);
  });

  it('takes over in another worker once the lease has lapsed', async () => {
    await givenALogOf('Placed');
    await checkpoints.claim('titles', 'worker-1', NOW, 30_000);

    const taken = await catchUp(store, checkpoints, view, {
      owner: 'worker-2',
      clock: clockAt(at(5 * 60_000)),
    });

    expect(taken).toEqual({ applied: 1, leased: true });
  });

  it('releases the lease when the pass is done', async () => {
    await givenALogOf('Placed');

    await catchUp(store, checkpoints, view, { owner: 'worker-1', clock: clockAt(NOW) });

    expect(await checkpoints.claim('titles', 'worker-2', NOW, 30_000)).toBeDefined();
  });

  /**
   * Exactly-once, and there is no idempotency key in it: the checkpoint moves in the same transaction as
   * the rows, so a crash before the commit leaves both untouched and the next pass reads the same batch
   * again.
   */
  it('moves neither the view nor the checkpoint when a batch fails', async () => {
    await givenALogOf('Placed');
    const broken = new Broken();

    await expect(
      catchUp(store, checkpoints, broken, { owner: 'worker-1', clock: clockAt(NOW) }),
    ).rejects.toThrow('the view write failed');

    expect(await checkpoints.positionOf('broken')).toBe(FROM_THE_BEGINNING);
  });

  /** Otherwise one bad batch costs a whole lease before anything tries again — every time. */
  it('releases the lease even when the pass fails', async () => {
    await givenALogOf('Placed');

    await expect(
      catchUp(store, checkpoints, new Broken(), { owner: 'worker-1', clock: clockAt(NOW) }),
    ).rejects.toThrow();

    expect(await checkpoints.claim('broken', 'worker-2', NOW, 30_000)).toBeDefined();
  });

  /**
   * What makes a read model disposable, and therefore what makes a projection bug fixable by changing the
   * fold rather than by patching rows.
   */
  it('catches up every projection in one pass', async () => {
    await givenALogOf('Placed', 'Paid');
    const other = new Titles('also-titles');

    const advances = await catchUpEach(store, checkpoints, [view, other], {
      owner: 'worker-1',
      clock: clockAt(NOW),
    });

    expect(advances).toEqual({
      titles: { applied: 2, leased: true },
      'also-titles': { applied: 2, leased: true },
    });
    expect(view.rows).toEqual(['Placed', 'Paid']);
    expect(other.rows).toEqual(['Placed', 'Paid']);
  });

  /**
   * One broken fold must not starve the projections after it in the list.
   *
   * The plugin runs this on a timer, so a projection that throws every pass would otherwise stop every
   * projection registered after it — permanently, and with nothing in the log to say which one was at
   * fault. Every projection is attempted, and the pass then fails loudly with all of it.
   */
  it('applies the other projections when one of them fails', async () => {
    await givenALogOf('Placed');
    const broken = new Broken();

    await expect(
      catchUpEach(store, checkpoints, [broken, view], { owner: 'worker-1', clock: clockAt(NOW) }),
    ).rejects.toThrow(AggregateError);

    expect(view.rows).toEqual(['Placed']);
  });

  it('empties the view and folds the whole log into it again on a rebuild', async () => {
    await givenALogOf('Placed', 'Paid');
    await catchUp(store, checkpoints, view, { owner: 'worker-1', clock: clockAt(NOW) });
    view.rows.push('something nothing derived');

    const rebuilt = await rebuild(store, checkpoints, view, {
      owner: 'worker-1',
      clock: clockAt(NOW),
    });

    expect(rebuilt).toEqual({ applied: 2, leased: true });
    expect(view.rows).toEqual(['Placed', 'Paid']);
  });

  /**
   * A rebuild is destructive, so "somebody else is advancing this" has to be distinguishable from "there
   * was nothing to apply". `leased` is that distinction.
   */
  it('leaves the view alone when a rebuild cannot take the lease', async () => {
    await givenALogOf('Placed');
    await catchUp(store, checkpoints, view, { owner: 'worker-1', clock: clockAt(NOW) });
    await checkpoints.claim('titles', 'worker-1', NOW, 30_000);

    const refused = await rebuild(store, checkpoints, view, {
      owner: 'worker-2',
      clock: clockAt(at(1000)),
    });

    expect(refused).toEqual({ applied: 0, leased: false });
    expect(view.rows).toHaveLength(1);
  });
});

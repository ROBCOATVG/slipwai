import { Pool } from 'pg';
import { afterAll, describe, expect, it } from 'vitest';

import { createPostgresEventStore } from '../../src/adapters/driven/event-store-postgres/index.js';
import type { DomainEvent, TagsOf } from '../../src/application/ports/events.js';
import {
  createCorrelationId,
  defaultTagsOf,
  NO_STREAM,
} from '../../src/application/ports/events.js';
import { eventStoreContract } from '../contract/event-store-contract.js';

/**
 * The event store against real Postgres. Deliberately NOT part of `make verify`: the repository gate stays
 * runnable with no infrastructure, and this target is the one that needs a database.
 *
 *   make services-up migrate test-integration
 *
 * It runs the same contract the in-memory fake passes, plus the four things only a real store can prove:
 * that two appends at one version produce exactly one winner, that two conditional appends against one
 * *boundary* do the same, that the log refuses to be rewritten, and that a replay never runs past a
 * position an earlier event could still commit behind.
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

/**
 * Turns "relation events does not exist" — or a refused connection — into the instruction that fixes it.
 * Without this the first failure is a driver error, and the reader has to know the schema is applied by a
 * separate target.
 */
let checked = false;
async function migratedStore(tagsOf: TagsOf = defaultTagsOf) {
  if (!checked) {
    try {
      await pool.query('SELECT 1 FROM events LIMIT 1');
    } catch (error) {
      throw new Error(
        `Cannot read the events table at ${connectionString}. ` +
          'Start the database and apply the schema first:  make services-up migrate',
        { cause: error },
      );
    }
    checked = true;
  }
  return createPostgresEventStore(pool, tagsOf);
}

eventStoreContract('the Postgres event store', migratedStore);

describe('the Postgres event store under genuine contention', () => {
  // One id for the whole file: these appends race each other inside one business transaction.
  const correlationId = createCorrelationId(crypto.randomUUID());

  const event = (
    streamId: string,
    type: string,
    payload: Record<string, unknown> = {},
  ): DomainEvent => ({
    type,
    schemaVersion: 1,
    streamId,
    payload,
    occurredAt: '2024-01-01T00:00:00.000Z',
    actor: { kind: 'test', id: 'contention' },
    correlationId,
  });

  /**
   * Tag an event by the seat it is claiming, which is what the boundary below is drawn out of. A real
   * project's tagging function is this shape: the identifying attributes, derived.
   */
  const seatTags: TagsOf = (candidate) => {
    const seat = candidate.payload.seatId;
    return typeof seat === 'string' ? [`seat:${seat}`] : [];
  };

  /**
   * The Dynamic Consistency Boundary, raced for real — and the case `expectedVersion` cannot express,
   * because each attempt writes to a *different* stream and the thing they contend for is a tag they
   * share.
   *
   * The boundary is read **once**, and all eight attempts are guarded by that one position: eight
   * callers who each decided, from the same facts, that the seat was free. Exactly one may record it.
   * Some lose because the winner's event is already there when they check; the rest lose to
   * `SERIALIZABLE` at commit, which is reported as the same conflict and needs the same next move from
   * the caller. No single-writer store can produce this situation at all, which is why the guarantee
   * is proved here and nowhere else.
   *
   * Reading the head separately inside each attempt would test something else entirely — whichever
   * attempt happened to read *after* the winner committed would be guarded from a position past the
   * winner's event, and would rightly be allowed to write. A caller that re-reads has re-decided, and
   * this test is about callers that have not.
   */
  it('lets exactly one of many simultaneous conditional appends win', async () => {
    const store = await migratedStore(seatTags);
    const seat = `seat-${crypto.randomUUID()}`;
    const query = { filters: [{ tags: [`seat:${seat}`] }] };
    const decidedAt = (await store.readTagged(query)).head;

    const results = await Promise.all(
      Array.from({ length: 8 }, (_unused, index) =>
        store.appendIf({ query, after: decidedAt }, [
          event(`claim-${seat}-${index}`, 'SeatClaimed', { seatId: seat }),
        ]),
      ),
    );

    expect(results.filter((result) => result.outcome === 'recorded')).toHaveLength(1);
    expect((await store.readTagged(query)).events).toHaveLength(1);
  });

  it('lets exactly one of many simultaneous first writes win', async () => {
    const store = await migratedStore();
    const stream = `race-${crypto.randomUUID()}`;

    const results = await Promise.all(
      Array.from({ length: 8 }, (_unused, index) =>
        store.append(stream, NO_STREAM, [event(stream, `Attempt${index}`)]),
      ),
    );

    // This is the assertion an in-memory store cannot make. Being single-threaded, the fake serialises
    // these calls and can never produce two winners, so it would pass this test while proving nothing.
    expect(results.filter((result) => result.outcome === 'appended')).toHaveLength(1);
    expect(await store.read(stream)).toHaveLength(1);
    for (const result of results) {
      if (result.outcome === 'version-conflict') expect(result.actualVersion).toBe(0);
    }
  });

  /**
   * The guarantee a projection's single-number checkpoint rests on, and the one bug in this design that
   * leaves no trace.
   *
   * A position is assigned when a row is inserted and becomes visible when its transaction commits, and
   * those are two different moments: two appends overlapping take 5 and 6, and 6 can commit first. A
   * replay that hands out 6 while 5 is still in flight makes the projection record "next is 7", and 5 then
   * arrives behind a checkpoint that has already passed it — a view missing a row, permanently, with a log
   * that is perfectly correct and nothing anywhere complaining.
   *
   * So `readAll` waits for the appends in flight and stops at the last settled position. The replay below
   * finishes only *after* the slow append commits, and then it holds both events in order. Without the
   * protocol it would finish at once, holding the second event and not the first.
   *
   * Only a real store can produce this at all: an in-memory fake is one lock and a file-backed store
   * serialises its writers, so in neither can a position be taken and committed out of order.
   */
  it('stops a replay short of a position an earlier event could still arrive behind', async () => {
    // A pool of its own per store, because these three have to be three connections: the slow append
    // holds its transaction open while the others work.
    const slow = createPostgresEventStore(new Pool({ connectionString }));
    const fast = createPostgresEventStore(new Pool({ connectionString }));
    const reader = createPostgresEventStore(new Pool({ connectionString }));
    const first = `slow-${crypto.randomUUID()}`;
    const second = `fast-${crypto.randomUUID()}`;
    // Where this case's own events begin: the log is shared with every other case and every previous
    // run, so a replay from zero would read all of them.
    const start = (await reader.readTagged({ filters: [] })).head + 1;

    const replayed: string[] = [];
    let finished = false;
    let replay: Promise<void> | undefined;

    await slow.inUnitOfWork(async () => {
      await slow.append(first, NO_STREAM, [event(first, 'Slow')]);
      // Its position is taken; its commit is not. This one takes the next position and commits.
      await fast.append(second, NO_STREAM, [event(second, 'Fast')]);

      // Started here, with one event visible and an earlier one still in flight — the moment the
      // protocol exists for. It blocks in the database, not on this event loop.
      replay = (async () => {
        for await (const replayedEvent of reader.readAll(start)) replayed.push(replayedEvent.type);
        finished = true;
      })();

      await new Promise((resolve) => setTimeout(resolve, 1000));
      expect(
        finished,
        `a replay finished while an append was in flight, and read ${replayed}`,
      ).toBe(false);
    });

    await replay;
    expect(replayed).toEqual(['Slow', 'Fast']);
  });

  /**
   * The same gap as the replay's, on the write path, where it breaks the constraint instead of a view —
   * and this is the case the whole tag boundary rests on.
   *
   * Two appends take 5 and 6; 6 commits first. A decision reading a head of 6 while 5 is still invisible
   * would be guarded from *after* 6 — and 5, the very event that should refuse it, sits below its own
   * boundary where the guard never looks. The append is allowed, the seat is claimed twice, and the log
   * looks perfectly correct afterwards.
   *
   * So a boundary is only ever a settled position: `head` waits for the appends in flight, which makes
   * the read that follows see the event as well. The claim below is therefore refused, and it is refused
   * by the *condition* rather than by chance.
   */
  it('refuses a conditional append against an event in flight when the boundary was read', async () => {
    const slow = createPostgresEventStore(new Pool({ connectionString }), seatTags);
    const fast = createPostgresEventStore(new Pool({ connectionString }), seatTags);
    const decider = createPostgresEventStore(new Pool({ connectionString }), seatTags);
    const seat = `seat-${crypto.randomUUID()}`;
    const query = { filters: [{ tags: [`seat:${seat}`] }] };

    let drawn: { boundary: number; types: string[] } | undefined;
    let decide: Promise<void> | undefined;

    await slow.inUnitOfWork(async () => {
      const claim = `claim-${seat}-1`;
      await slow.append(claim, NO_STREAM, [event(claim, 'SeatClaimed', { seatId: seat })]);
      // Its position is taken; its commit is not. This one takes the next position and commits.
      const other = `other-${crypto.randomUUID()}`;
      await fast.append(other, NO_STREAM, [event(other, 'Unrelated')]);

      // A decision, drawn the way every DCB caller draws one: pin the boundary, then read it.
      decide = (async () => {
        const boundary = await decider.head();
        const found = await decider.readTagged(query, 0, boundary);
        drawn = { boundary, types: found.events.map((found_) => found_.type) };
      })();

      await new Promise((resolve) => setTimeout(resolve, 1000));
      expect(
        drawn,
        `a boundary was drawn while an append was in flight: ${JSON.stringify(drawn)}`,
      ).toBe(undefined);
    });

    await decide;
    // The decision now knows about the claim, which is the whole point of waiting.
    expect(drawn?.types).toEqual(['SeatClaimed']);

    // And a caller that decided anyway is refused by the condition rather than by luck.
    const refused = await decider.appendIf({ query, after: 0 }, [
      event(`claim-${seat}-2`, 'SeatClaimed', { seatId: seat }),
    ]);
    expect(refused.outcome).toBe('condition-conflict');
  });

  it('refuses to let a committed event be rewritten or removed', async () => {
    const store = await migratedStore();
    const stream = `append-only-${crypto.randomUUID()}`;
    await store.append(stream, NO_STREAM, [event(stream, 'Recorded')]);

    await expect(
      pool.query('UPDATE events SET event_type = $1 WHERE stream_id = $2', ['Rewritten', stream]),
    ).rejects.toThrow(/append-only/);
    await expect(pool.query('DELETE FROM events WHERE stream_id = $1', [stream])).rejects.toThrow(
      /append-only/,
    );

    expect((await store.read(stream)).map((e) => e.type)).toEqual(['Recorded']);
  });
});

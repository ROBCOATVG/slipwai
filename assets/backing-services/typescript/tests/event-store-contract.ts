import { randomUUID } from 'node:crypto';
import { beforeEach, describe, expect, it } from 'vitest';

import type {
  CausationId,
  CommittedEvent,
  DomainEvent,
  EventStore,
  TagsOf,
} from '../../src/application/ports/events.js';
import {
  createCausationId,
  createCorrelationId,
  currentVersion,
  defaultTagsOf,
  NO_STREAM,
  streamTag,
} from '../../src/application/ports/events.js';

/**
 * A tagging function of the shape a real project writes: the stream, plus the identifying attributes of
 * the payload.
 *
 * Tags are derived from the event and nothing else, which is what makes the index rebuildable — so this
 * function is called on the way in *and* during a reindex, and the contract below proves the two agree.
 */
export const payloadTags: TagsOf = (event) => {
  const tags = [streamTag(event.streamId)];
  for (const [attribute, kind] of [
    ['courseId', 'course'],
    ['studentId', 'student'],
  ] as const) {
    const value = event.payload[attribute];
    if (typeof value === 'string') tags.push(`${kind}:${value}`);
  }
  return tags;
};

/**
 * What a project that has not adopted tags has: a log with no index over it. Every event already in a
 * running project's log was written by a store that behaved exactly like this, which is why it is worth a
 * named function rather than a comment.
 */
export const noTags: TagsOf = () => [];

/**
 * One contract, run against every event-store adapter — the in-memory fake by `make test` and Postgres by
 * `make test-integration`. Two adapters that pass different tests are two different ports wearing one name,
 * and the day they diverge is the day a slice that worked on the fake stops working in production.
 *
 * Nothing here truncates or deletes: the log is append-only, and migration 002 enforces that with a
 * trigger, so a shared table cannot be cleaned between tests. Every test therefore works in freshly named
 * streams and asserts only about those. That is not a workaround — it is what testing against a real
 * append-only log actually looks like.
 */
export function eventStoreContract(
  name: string,
  createStore: (tagsOf?: TagsOf) => Promise<EventStore>,
): void {
  describe(`${name} satisfies the event-store port`, () => {
    let store: EventStore;
    /**
     * A store whose events are findable by their payload's ids as well as their stream — which is the only
     * reason a Dynamic Consistency Boundary can be drawn at all.
     */
    let tagged: EventStore;
    let run: string;
    let counter = 0;

    beforeEach(async () => {
      store = await createStore(defaultTagsOf);
      tagged = await createStore(payloadTags);
      run = randomUUID();
      counter = 0;
    });

    const newStream = (): string => {
      counter += 1;
      return `contract-${run}-${counter}`;
    };

    const event = (
      streamId: string,
      type: string,
      payload: Record<string, unknown> = {},
      causationId?: CausationId,
    ): DomainEvent => ({
      type,
      schemaVersion: 1,
      streamId,
      payload,
      occurredAt: '2024-01-01T00:00:00.000Z',
      actor: { kind: 'test', id: run },
      correlationId: createCorrelationId(run),
      ...(causationId === undefined ? {} : { causationId }),
    });

    it('reads an unknown stream as empty rather than failing', async () => {
      expect(await store.read(newStream())).toEqual([]);
    });

    it('appends to a stream that does not exist yet and reports the new version', async () => {
      const stream = newStream();

      const result = await store.append(stream, NO_STREAM, [
        event(stream, 'Started'),
        event(stream, 'Continued'),
      ]);

      expect(result).toEqual({ outcome: 'appended', version: 1 });
    });

    it('returns the stream in version order, with the facts only the store knows', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started', { step: 1 })]);
      await store.append(stream, 0, [event(stream, 'Continued', { step: 2 })]);

      const events = await store.read(stream);

      expect(events.map((e) => [e.type, e.version])).toEqual([
        ['Started', 0],
        ['Continued', 1],
      ]);
      expect(events.map((e) => e.payload)).toEqual([{ step: 1 }, { step: 2 }]);
      const [first, second] = events as [CommittedEvent, CommittedEvent];
      expect(second.globalPosition).toBeGreaterThan(first.globalPosition);
      expect(Date.parse(first.recordedAt)).not.toBeNaN();
      expect(first.occurredAt).toBe('2024-01-01T00:00:00.000Z');
      expect(first.actor).toEqual({ kind: 'test', id: run });
    });

    /**
     * Every adapter stores these ids the way its database can and hands back the same UUIDs. Postgres has
     * a `uuid` column, SQLite has text, the in-memory store has neither. The difference stops at the
     * adapter, and it is provable here rather than by reading three implementations.
     */
    it('round-trips the correlation and causation ids as UUIDs', async () => {
      const stream = newStream();
      const cause = createCausationId(randomUUID());

      await store.append(stream, NO_STREAM, [
        event(stream, 'Started'),
        event(stream, 'Caused', {}, cause),
      ]);

      const [first, second] = (await store.read(stream)) as [CommittedEvent, CommittedEvent];
      expect(first.correlationId).toBe(createCorrelationId(run));
      // The first event of a transaction has no cause, and the store does not invent one.
      expect(first.causationId).toBeUndefined();
      expect(second.causationId).toBe(cause);
    });

    it('reports a stale expected version as a value, not a thrown error', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started')]);

      const result = await store.append(stream, NO_STREAM, [event(stream, 'Raced')]);

      expect(result).toEqual({ outcome: 'version-conflict', actualVersion: 0 });
    });

    it('writes nothing when the expected version is stale', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started')]);

      await store.append(stream, NO_STREAM, [
        event(stream, 'Rejected'),
        event(stream, 'AlsoRejected'),
      ]);

      expect((await store.read(stream)).map((e) => e.type)).toEqual(['Started']);
    });

    it('rejects a first write to a stream that already exists', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started')]);
      const history = await store.read(stream);

      expect(currentVersion(history)).toBe(0);
      expect(
        await store.append(stream, currentVersion(history), [event(stream, 'Continued')]),
      ).toEqual({
        outcome: 'appended',
        version: 1,
      });
    });

    it('treats an empty append as a no-op at the expected version', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started')]);

      expect(await store.append(stream, 0, [])).toEqual({ outcome: 'appended', version: 0 });
      expect((await store.read(stream)).length).toBe(1);
    });

    it('keeps streams apart', async () => {
      const one = newStream();
      const other = newStream();
      await store.append(one, NO_STREAM, [event(one, 'Mine')]);
      await store.append(other, NO_STREAM, [event(other, 'Theirs')]);

      expect((await store.read(one)).map((e) => e.type)).toEqual(['Mine']);
      expect((await store.read(other)).map((e) => e.type)).toEqual(['Theirs']);
    });

    it('replays across all streams in global-position order', async () => {
      const one = newStream();
      const other = newStream();
      await store.append(one, NO_STREAM, [event(one, 'First')]);
      await store.append(other, NO_STREAM, [event(other, 'Second')]);
      await store.append(one, 0, [event(one, 'Third')]);

      const replayed: CommittedEvent[] = [];
      for await (const committed of store.readAll(0)) {
        if (committed.streamId === one || committed.streamId === other) replayed.push(committed);
      }

      expect(replayed.map((e) => e.type)).toEqual(['First', 'Second', 'Third']);
      expect(replayed.map((e) => e.globalPosition)).toEqual(
        [...replayed.map((e) => e.globalPosition)].sort((a, b) => a - b),
      );
    });

    it('replays only from the requested position onward', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'First'), event(stream, 'Second')]);
      const [, second] = (await store.read(stream)) as [CommittedEvent, CommittedEvent];

      const replayed: CommittedEvent[] = [];
      for await (const committed of store.readAll(second.globalPosition)) {
        if (committed.streamId === stream) replayed.push(committed);
      }

      expect(replayed.map((e) => e.type)).toEqual(['Second']);
    });

    // ── The tag index, and the boundary drawn out of it ────────────────────────────────────────────
    //
    // Everything below is the Dynamic Consistency Boundary, and it runs against every adapter for the
    // same reason the rest of this file does: a fake that answers a tag query differently from Postgres
    // is a fake that proves nothing about production. The SQL adapters translate `matchesFilter` into
    // SQL, and these are the cases that hold the translation to the definition.

    it('indexes every event by its own stream without being asked', async () => {
      const stream = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started')]);

      const found = await store.readTagged({ filters: [{ tags: [streamTag(stream)] }] });

      expect(found.events.map((e) => e.type)).toEqual(['Started']);
    });

    it('reports the store head with what it read', async () => {
      const stream = newStream();
      const query = { filters: [{ tags: [streamTag(stream)] }] };
      const empty = await tagged.readTagged(query);
      await tagged.append(stream, NO_STREAM, [event(stream, 'Started')]);

      const after = await tagged.readTagged(query);

      expect(after.head).toBeGreaterThan(empty.head);
      expect(after.events.at(-1)?.globalPosition).toBe(after.head);
    });

    it('matches an event only when it carries every tag in a filter', async () => {
      const stream = newStream();
      await tagged.append(stream, NO_STREAM, [
        event(stream, 'Subscribed', { courseId: run, studentId: run }),
      ]);

      const both = await tagged.readTagged({
        filters: [{ tags: [`course:${run}`, `student:${run}`] }],
      });
      const oneWrong = await tagged.readTagged({
        filters: [{ tags: [`course:${run}`, `student:${run}-nobody`] }],
      });

      expect(both.events.map((e) => e.type)).toEqual(['Subscribed']);
      expect(oneWrong.events).toEqual([]);
    });

    it('matches any filter in the query', async () => {
      const courseStream = newStream();
      const studentStream = newStream();
      await tagged.append(courseStream, NO_STREAM, [
        event(courseStream, 'CourseCapacitySet', { courseId: run }),
      ]);
      await tagged.append(studentStream, NO_STREAM, [
        event(studentStream, 'StudentSubscribed', { studentId: run }),
      ]);

      const found = await tagged.readTagged({
        filters: [{ tags: [`course:${run}`] }, { tags: [`student:${run}`] }],
      });

      expect(found.events.map((e) => e.type)).toEqual(['CourseCapacitySet', 'StudentSubscribed']);
    });

    it('narrows a filter by event type', async () => {
      const stream = newStream();
      await tagged.append(stream, NO_STREAM, [
        event(stream, 'Subscribed', { courseId: run }),
        event(stream, 'Unsubscribed', { courseId: run }),
      ]);

      const found = await tagged.readTagged({
        filters: [{ tags: [`course:${run}`], types: ['Unsubscribed'] }],
      });

      expect(found.events.map((e) => e.type)).toEqual(['Unsubscribed']);
    });

    it('matches nothing for an empty query rather than everything', async () => {
      const stream = newStream();
      await tagged.append(stream, NO_STREAM, [event(stream, 'Started')]);

      expect((await tagged.readTagged({ filters: [] })).events).toEqual([]);
      expect((await tagged.readTagged({ filters: [{}] })).events).toEqual([]);
    });

    it('appends conditionally when nothing matching arrived since the read', async () => {
      const stream = newStream();
      const query = { filters: [{ tags: [`course:${run}`] }] };
      const decidedAt = (await tagged.readTagged(query)).head;

      const result = await tagged.appendIf({ query, after: decidedAt }, [
        event(stream, 'Subscribed', { courseId: run }),
      ]);

      expect(result.outcome).toBe('recorded');
      expect((await tagged.read(stream)).map((e) => e.type)).toEqual(['Subscribed']);
    });

    /**
     * The guard `expectedVersion` cannot express: the constraint spans two entities, and what invalidates
     * the decision is an event in a stream the decision never named.
     */
    it('refuses a conditional append when a matching event arrived since', async () => {
      const stream = newStream();
      const other = newStream();
      const query = { filters: [{ tags: [`course:${run}`] }] };
      const decidedAt = (await tagged.readTagged(query)).head;
      await tagged.append(other, NO_STREAM, [event(other, 'Subscribed', { courseId: run })]);

      const result = await tagged.appendIf({ query, after: decidedAt }, [
        event(stream, 'Subscribed', { courseId: run }),
      ]);

      expect(result.outcome).toBe('condition-conflict');
      expect(result.head).toBeGreaterThanOrEqual(decidedAt);
      expect(await tagged.read(stream)).toEqual([]);
    });

    /**
     * The compatibility that makes this additive rather than a fork. A conditional append still lands at
     * the next version of the stream it names, so every slice written against `read`, `append` and `folds`
     * goes on working unchanged.
     */
    it('leaves a conditionally appended event readable as part of its stream', async () => {
      const stream = newStream();
      const query = { filters: [{ tags: [`course:${run}`] }] };
      await tagged.append(stream, NO_STREAM, [event(stream, 'Opened', { courseId: run })]);
      await tagged.appendIf({ query, after: (await tagged.readTagged(query)).head }, [
        event(stream, 'Subscribed', { courseId: run }),
      ]);

      const events = await tagged.read(stream);

      expect(events.map((e) => [e.type, e.version])).toEqual([
        ['Opened', 0],
        ['Subscribed', 1],
      ]);
      expect(await tagged.append(stream, currentVersion(events), [])).toEqual({
        outcome: 'appended',
        version: 1,
      });
    });

    /**
     * What every project generated before tags existed is, and what it stays until it says otherwise: the
     * log, unchanged, with an index over nothing.
     */
    it('behaves exactly as it did before when it indexes nothing', async () => {
      const untagged = await createStore(noTags);
      const stream = newStream();

      expect(await untagged.append(stream, NO_STREAM, [event(stream, 'Started')])).toEqual({
        outcome: 'appended',
        version: 0,
      });
      expect((await untagged.read(stream)).map((e) => e.type)).toEqual(['Started']);
      expect(
        (await untagged.readTagged({ filters: [{ tags: [streamTag(stream)] }] })).events,
      ).toEqual([]);
    });

    /**
     * The adoption path, as a test rather than as a paragraph.
     *
     * A project already in production applies the migration, which creates an empty index, and runs this.
     * Nothing about the log changes — which is the only reason it is possible at all, since the log
     * refuses to be rewritten.
     *
     * `retag` rebuilds the whole index rather than one stream's share of it. Against a shared database
     * that is safe here because every tagging function in this suite returns the stream tag plus more, so
     * a rebuild under one of them satisfies every other case's assumptions as well.
     */
    it('indexes a log it did not index when the events were written', async () => {
      const unindexed = await createStore(noTags);
      const stream = newStream();
      await unindexed.append(stream, NO_STREAM, [
        event(stream, 'Enrolled', { courseId: run }),
        event(stream, 'Graduated', { courseId: run }),
      ]);
      const query = { filters: [{ tags: [`course:${run}`] }] };
      expect((await unindexed.readTagged(query)).events).toEqual([]);

      const indexed = await unindexed.retag(payloadTags);

      expect(indexed).toBeGreaterThanOrEqual(2);
      expect((await unindexed.readTagged(query)).events.map((e) => e.type)).toEqual([
        'Enrolled',
        'Graduated',
      ]);
      // Idempotent: a second run indexes nothing, so a reindex that died halfway is finished by running
      // it again rather than started over.
      expect(await unindexed.reindexTags()).toBe(0);
      expect((await unindexed.readTagged(query)).events).toHaveLength(2);
    });

    /**
     * What "indexed" means, which the adapters have to agree on or the number an adoption run reports is
     * a different number in every store.
     *
     * An event this project's tagging function returns nothing for is never findable by tag, so a
     * reindex that counted it would report work it did not do and would never settle at zero. Both
     * halves matter: the in-memory store must not record an empty index entry, which would make the
     * event look indexed to a later run under a real tagging function, and the SQL stores must not count
     * a row they wrote no tags for.
     */
    it('counts only the events a reindex made findable by tag', async () => {
      const store = await createStore(noTags);
      const stream = newStream();
      await store.append(stream, NO_STREAM, [
        event(stream, 'Enrolled', { courseId: run }),
        event(stream, 'Graduated', { courseId: run }),
      ]);

      expect(await store.reindexTags()).toBe(0);
    });

    /**
     * The reason `head` is a method of its own, and what stops a decision from being made against two
     * different moments.
     *
     * A command that needs two queries — a course's capacity and a student's own subscriptions — reads
     * twice. If each read hands back its own head and the caller guards with the second one, an event
     * matching the *first* query could have arrived between the two reads, before that head, and the
     * conditional append would never look for it: the guard says "nothing since here" about a position
     * the facts do not cover.
     *
     * Pinning the boundary first and passing it as `until` removes the gap. Both reads see the same log,
     * the head handed back is the boundary rather than whatever has happened since, and a condition built
     * from it covers exactly the facts it was decided on.
     */
    it('reads as of a boundary and nothing after it', async () => {
      const stream = newStream();
      const query = { filters: [{ tags: [`course:${run}`] }] };
      await tagged.append(stream, NO_STREAM, [event(stream, 'Enrolled', { courseId: run })]);

      const boundary = await tagged.head();
      // Somebody else's event, after the boundary this decision was drawn at.
      await tagged.append(stream, 0, [event(stream, 'Graduated', { courseId: run })]);

      const asOf = await tagged.readTagged(query, 0, boundary);
      expect(asOf.events.map((found) => found.type)).toEqual(['Enrolled']);
      expect(asOf.head).toBe(boundary);

      // Unbounded, the same query sees both — the ceiling is the caller's decision, not a filter the
      // store applies on its own.
      const current = await tagged.readTagged(query);
      expect(current.events.map((found) => found.type)).toEqual(['Enrolled', 'Graduated']);
      expect(current.head).toBeGreaterThanOrEqual(boundary);
    });

    /**
     * The one failure that would make the index worse than not having it: an event visible to `read`
     * whose tags are not yet visible to `readTagged` would let the next conditional append miss the very
     * event that should have refused it.
     */
    it('makes an append and its tags arrive together or not at all', async () => {
      const stream = newStream();
      const query = { filters: [{ tags: [`course:${run}`] }] };

      await tagged.append(stream, NO_STREAM, [event(stream, 'Subscribed', { courseId: run })]);

      expect(await tagged.read(stream)).toHaveLength(1);
      expect((await tagged.readTagged(query)).events).toHaveLength(1);
    });

    /**
     * What an `inline` read model and an `async` checkpoint are both built on: a write of somebody else's
     * that fails takes the append with it.
     */
    it('leaves the log as it was when a unit of work fails', async () => {
      const stream = newStream();

      await expect(
        store.inUnitOfWork(async () => {
          await store.append(stream, NO_STREAM, [event(stream, 'Started')]);
          throw new Error('the view write failed');
        }),
      ).rejects.toThrow('the view write failed');

      expect(await store.read(stream)).toEqual([]);
    });

    it('commits everything in a unit of work that completes, once', async () => {
      const one = newStream();
      const other = newStream();

      await store.inUnitOfWork(async () => {
        await store.append(one, NO_STREAM, [event(one, 'Mine')]);
        await store.append(other, NO_STREAM, [event(other, 'Theirs')]);
      });

      expect((await store.read(one)).map((e) => e.type)).toEqual(['Mine']);
      expect((await store.read(other)).map((e) => e.type)).toEqual(['Theirs']);
    });

    /**
     * A conflict is a value, so the caller's transaction survives it and goes on to commit what else it
     * was doing. Without a savepoint per nested block, a refused append would either poison the outer
     * transaction or leave its own half-written events inside it.
     */
    it('writes nothing and ends nothing when an append inside a unit of work is refused', async () => {
      const stream = newStream();
      const other = newStream();
      await store.append(stream, NO_STREAM, [event(stream, 'Started')]);

      const refused = await store.inUnitOfWork(async () => {
        const result = await store.append(stream, NO_STREAM, [
          event(stream, 'Rejected'),
          event(stream, 'AlsoRejected'),
        ]);
        await store.append(other, NO_STREAM, [event(other, 'Unaffected')]);
        return result;
      });

      expect(refused).toEqual({ outcome: 'version-conflict', actualVersion: 0 });
      expect((await store.read(stream)).map((e) => e.type)).toEqual(['Started']);
      expect((await store.read(other)).map((e) => e.type)).toEqual(['Unaffected']);
    });
  });
}

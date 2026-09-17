import type {
  AppendResult,
  CommittedEvent,
  Condition,
  ConditionalAppendResult,
  DomainEvent,
  EventStore,
  TaggedRead,
  TagQuery,
  TagsOf,
} from '../../application/ports/events.js';
import {
  appended,
  conditionConflict,
  defaultTagsOf,
  matchesQuery,
  NO_STREAM,
  recorded,
  versionConflict,
} from '../../application/ports/events.js';

/**
 * In-memory event-store adapter — for a quickstart with no infrastructure, and for tests that do not need
 * to prove concurrency. `make verify` runs the shared contract suite against this one, which is why the
 * repository gate needs no Docker.
 *
 * It satisfies the port's contract, but understand what it cannot do: being single-threaded, it cannot
 * genuinely race, so it CANNOT prove that two concurrent appends at the same version produce exactly one
 * winner — nor that two conditional appends against one boundary do. Those guarantees live in a real
 * store's unique constraint and isolation level, and `make test-integration` is where they are proved.
 * Ship on Postgres, demo on memory.
 *
 * Data is lost on restart, which for an event-sourced system means the entire truth is lost. Never
 * production.
 */

/**
 * What a connection is, when there is no database.
 *
 * It exists so the in-memory adapters can do the one thing the real ones do that matters most to the read
 * side: put an append, a view write and a checkpoint in **one transaction**. Build the event store and the
 * checkpoint store from the same instance — which is what `createInMemoryCheckpointStore(store)` does —
 * and `inUnitOfWork` covers all of it.
 *
 * Rollback is a restore from a shallow copy taken on entry. That is honest for what this is for: it proves
 * the *semantics* a test needs (a failed batch changes nothing) without pretending to be a transaction
 * manager. Events are frozen, so copying the list is enough.
 */
export type InMemoryDatabase = {
  log: CommittedEvent[];
  /**
   * Global position to the tags it was indexed by — the derived index, kept beside the log rather than on
   * the event, exactly as the SQL adapters keep it in a table of its own.
   */
  tags: Map<number, readonly string[]>;
  checkpoints: Map<string, number>;
  leases: Map<string, { owner: string; expiresAt: Date }>;
  head(): number;
  inUnitOfWork<T>(work: () => Promise<T>): Promise<T>;
};

export function createInMemoryDatabase(): InMemoryDatabase {
  const database: InMemoryDatabase = {
    log: [],
    tags: new Map(),
    checkpoints: new Map(),
    leases: new Map(),
    head: () => database.log.at(-1)?.globalPosition ?? 0,
    // Nesting needs no counter: the mutation happens in place, so a rollback is a restore, and an inner
    // block restoring its own snapshot leaves the outer one's intact.
    inUnitOfWork: async <T>(work: () => Promise<T>): Promise<T> => {
      const log = database.log.slice();
      const tags = new Map(database.tags);
      const checkpoints = new Map(database.checkpoints);
      const leases = new Map(database.leases);
      try {
        return await work();
      } catch (error) {
        database.log = log;
        database.tags = tags;
        database.checkpoints = checkpoints;
        database.leases = leases;
        throw error;
      }
    },
  };
  return database;
}

export type InMemoryEventStore = EventStore & { readonly database: InMemoryDatabase };

export function createInMemoryEventStore(
  tagsOf: TagsOf = defaultTagsOf,
  database: InMemoryDatabase = createInMemoryDatabase(),
): InMemoryEventStore {
  let tagging = tagsOf;

  const streamEvents = (streamId: string): CommittedEvent[] =>
    database.log.filter((event) => event.streamId === streamId);

  const versionOf = (streamId: string): number =>
    streamEvents(streamId).at(-1)?.version ?? NO_STREAM;

  const record = (event: DomainEvent, streamId: string, version: number): void => {
    const globalPosition = database.head() + 1;
    database.log.push({
      ...event,
      streamId,
      version,
      globalPosition,
      recordedAt: new Date().toISOString(),
    });
    // No entry at all when the tagging function returns nothing, rather than an empty one: the SQL
    // adapters give such an event no rows, and "indexed" has to mean the same thing in every adapter
    // or reindexTags answers differently depending on the store.
    const tags = tagging(event);
    if (tags.length > 0) database.tags.set(globalPosition, [...tags]);
  };

  const readTagged = async (query: TagQuery, after = 0, until = 0): Promise<TaggedRead> => {
    const ceiling = until === 0 ? database.head() : until;
    return {
      events: database.log.filter(
        (event) =>
          event.globalPosition > after &&
          event.globalPosition <= ceiling &&
          matchesQuery(query, event, database.tags.get(event.globalPosition) ?? []),
      ),
      head: ceiling,
    };
  };

  const reindexTags = async (fromPosition = 0): Promise<number> =>
    database.inUnitOfWork(async () => {
      let indexed = 0;
      for (const event of database.log) {
        if (event.globalPosition < fromPosition) continue;
        if (database.tags.has(event.globalPosition)) continue;
        const tags = tagging(event);
        if (tags.length === 0) continue;
        database.tags.set(event.globalPosition, [...tags]);
        indexed += 1;
      }
      return indexed;
    });

  return {
    database,

    read: async (streamId: string): Promise<readonly CommittedEvent[]> =>
      streamEvents(streamId).slice(),

    append: async (
      streamId: string,
      expectedVersion: number,
      events: readonly DomainEvent[],
    ): Promise<AppendResult> => {
      const actualVersion = versionOf(streamId);
      if (actualVersion !== expectedVersion) return versionConflict(actualVersion);

      let version = actualVersion;
      await database.inUnitOfWork(async () => {
        for (const event of events) {
          version += 1;
          record(event, streamId, version);
        }
      });
      return appended(version);
    },

    readAll: async function* (fromPosition: number): AsyncIterable<CommittedEvent> {
      for (const event of database.log.filter((entry) => entry.globalPosition >= fromPosition))
        yield event;
    },

    inUnitOfWork: database.inUnitOfWork,

    head: async () => database.head(),
    readTagged,

    appendIf: async (
      condition: Condition,
      events: readonly DomainEvent[],
    ): Promise<ConditionalAppendResult> => {
      const matching = await readTagged(condition.query, condition.after);
      if (matching.events.length > 0) return conditionConflict(database.head());

      await database.inUnitOfWork(async () => {
        for (const event of events) {
          // Each event still lands at the next version of the stream it names, so a conditionally
          // appended event is readable by everything written against `read` and `append`. The boundary
          // changed; the log did not.
          record(event, event.streamId, versionOf(event.streamId) + 1);
        }
      });
      return recorded(database.head());
    },

    reindexTags,

    retag: async (next: TagsOf): Promise<number> =>
      database.inUnitOfWork(async () => {
        tagging = next;
        database.tags.clear();
        return reindexTags();
      }),
  };
}

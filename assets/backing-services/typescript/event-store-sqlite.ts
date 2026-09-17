import { DatabaseSync } from 'node:sqlite';

import type {
  Actor,
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
  createCausationId,
  createCorrelationId,
  defaultTagsOf,
  recorded,
  versionConflict,
} from '../../application/ports/events.js';

/**
 * SQLite event-store adapter — a real append-only log in one file, with no container to run.
 *
 * Chosen when durability matters and infrastructure does not: a single-process service, a CLI, a
 * long-running worker, or a demo that must survive a restart. Understand the one thing it cannot do
 * before adopting it: **SQLite serialises writers**. It proves durability and it proves the append-only
 * rule, but it CANNOT prove concurrent behaviour, because it never genuinely races. If the
 * never-write-the-same-version-twice guarantee matters to your product, prove it on Postgres —
 * `make test-integration` there races two appends at one version and requires exactly one winner.
 *
 * `node:sqlite` is the standard library, so this adapter adds no dependency and no build step — the
 * deliberate trade being that Node still prints an ExperimentalWarning for it. Swapping to `better-sqlite3`
 * is a change to this file's first two lines and nothing else, which is the point of a driven adapter.
 *
 * Unlike Postgres, the schema ships with the adapter rather than as a migration: an embedded database is
 * created by the process that opens it, so there is no separate `make migrate` step and nothing to run
 * before the first test. The first schema change you make in anger is the moment to add a real migration
 * tool — see `migrations/` in a Postgres-backed project for the shape. The three tables below are the same
 * three the Postgres migrations create — the log, the projection checkpoints, and the derived tag index —
 * because two spellings of one schema drift and nothing notices.
 */

/** SQLite's constraint-violation result code, raised as `err.code` by node:sqlite. */
const CONSTRAINT_VIOLATION = 'ERR_SQLITE_ERROR';

/**
 * `global_position` is INTEGER PRIMARY KEY, which in SQLite aliases the monotonic rowid — the readAll
 * ordering the port promises. The append-only guarantee is enforced in the database rather than in this
 * file, because a rule the application enforces is a rule the next process to open the file will not.
 */
const SCHEMA = `
  CREATE TABLE IF NOT EXISTS events (
    global_position INTEGER PRIMARY KEY,
    stream_id       TEXT    NOT NULL,
    version         INTEGER NOT NULL,
    event_type      TEXT    NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload         TEXT    NOT NULL,
    actor           TEXT    NOT NULL,
    -- SQLite has no UUID type, so the canonical text form is what is stored. Postgres uses a real
    -- \`uuid\` column; both round-trip through the same branded type, and the adapter is where that
    -- difference stops.
    correlation_id  TEXT    NOT NULL,
    causation_id    TEXT,
    occurred_at     TEXT    NOT NULL,
    recorded_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version),
    CONSTRAINT events_version_not_negative CHECK (version >= 0)
  );

  CREATE INDEX IF NOT EXISTS events_stream_id_version ON events (stream_id, version);

  CREATE TRIGGER IF NOT EXISTS events_reject_update
  BEFORE UPDATE ON events
  BEGIN
    SELECT RAISE(ABORT, 'events is append-only: UPDATE is rejected');
  END;

  CREATE TRIGGER IF NOT EXISTS events_reject_delete
  BEFORE DELETE ON events
  BEGIN
    SELECT RAISE(ABORT, 'events is append-only: DELETE is rejected');
  END;

  -- Where each projection has got to. Mutable by design, and deliberately with no trigger: a checkpoint
  -- is a position that moves, and everything derived from the log can be thrown away and rebuilt. The
  -- lease columns are how exactly one worker advances it, with an expiry so that survives the worker
  -- dying.
  CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection        TEXT    PRIMARY KEY,
    position          INTEGER NOT NULL DEFAULT 0,
    lease_owner       TEXT,
    lease_expires_at  TEXT,
    updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CONSTRAINT projection_checkpoints_position_not_negative CHECK (position >= 0),
    CONSTRAINT projection_checkpoints_lease_is_whole CHECK (
      (lease_owner IS NULL) = (lease_expires_at IS NULL)
    )
  );

  -- The tag index — the Dynamic Consistency Boundary's half of the log. Derived from the events by this
  -- project's tagging function, written inside the append's own transaction, and rebuildable at any time,
  -- which is what lets a running project adopt tags without rewriting a log it is forbidden to rewrite.
  CREATE TABLE IF NOT EXISTS event_tags (
    tag             TEXT    NOT NULL,
    global_position INTEGER NOT NULL REFERENCES events (global_position),
    PRIMARY KEY (tag, global_position)
  );

  CREATE INDEX IF NOT EXISTS event_tags_global_position ON event_tags (global_position);
`;

const INSERT_GUARDED = `
  INSERT INTO events (
    stream_id, version, event_type, schema_version, payload, actor,
    correlation_id, causation_id, occurred_at
  )
  SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
  WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?) = ?
`;

const EVENT_COLUMNS = `
  global_position, stream_id, version, event_type, schema_version, payload, actor,
  correlation_id, causation_id, occurred_at, recorded_at
`;

const READ_STREAM = `SELECT ${EVENT_COLUMNS} FROM events WHERE stream_id = ? ORDER BY version ASC`;

const READ_ALL_BATCH = `
  SELECT ${EVENT_COLUMNS}
  FROM events
  WHERE global_position >= ?
  ORDER BY global_position ASC
  LIMIT ?
`;

const CURRENT_VERSION =
  'SELECT COALESCE(MAX(version), -1) AS version FROM events WHERE stream_id = ?';

const HEAD = 'SELECT COALESCE(MAX(global_position), 0) AS head FROM events';

const INSERT_TAG = 'INSERT OR IGNORE INTO event_tags (tag, global_position) VALUES (?, ?)';

const DELETE_TAGS = 'DELETE FROM event_tags';

const UNINDEXED_EVENTS = `
  SELECT ${EVENT_COLUMNS}
  FROM events
  WHERE global_position >= ?
    AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
  ORDER BY global_position ASC
`;

/** Batched so a rebuild over a long log does not materialise the whole thing in memory. */
const READ_ALL_BATCH_SIZE = 500;

type EventRow = {
  global_position: number;
  stream_id: string;
  version: number;
  event_type: string;
  schema_version: number;
  payload: string;
  actor: string;
  correlation_id: string;
  causation_id: string | null;
  occurred_at: string;
  recorded_at: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function actorFrom(value: unknown, position: number): Actor {
  if (!isRecord(value) || typeof value.kind !== 'string' || typeof value.id !== 'string') {
    throw new Error(`event at global_position ${position} has no usable actor`);
  }
  return { kind: value.kind, id: value.id };
}

/**
 * Parse a stored row back into a CommittedEvent.
 *
 * Events are validated on read as well as on write, because stored events outlive the code that wrote
 * them — a compile-time type says nothing about a row written eighteen months ago. This is a *tolerant*
 * reader on purpose: unknown payload fields written by a newer version are carried through rather than
 * rejected, which is what makes a rolling deploy possible. Only the envelope itself is required.
 */
function toCommittedEvent(row: EventRow): CommittedEvent {
  const payload: unknown = JSON.parse(row.payload);
  if (!isRecord(payload)) {
    throw new Error(`event at global_position ${row.global_position} has a non-object payload`);
  }
  if (row.schema_version !== 1) {
    throw new Error(
      `event at global_position ${row.global_position} is schema version ${row.schema_version}; ` +
        'add an upcaster for it before reading it as version 1',
    );
  }
  return {
    type: row.event_type,
    schemaVersion: 1,
    streamId: row.stream_id,
    payload,
    occurredAt: row.occurred_at,
    actor: actorFrom(JSON.parse(row.actor), row.global_position),
    correlationId: createCorrelationId(row.correlation_id),
    ...(row.causation_id === null ? {} : { causationId: createCausationId(row.causation_id) }),
    version: row.version,
    globalPosition: row.global_position,
    recordedAt: row.recorded_at,
  };
}

/**
 * A `TagQuery` as a SQL predicate over `e`, plus its parameters.
 *
 * `matchesFilter` in the port is the definition; this is a translation of it, and the contract suite is
 * what holds the two to each other. Every branch here has a case there:
 *
 *   * a filter's tags are a **conjunction**, so the count of its tags found against the event must equal
 *     how many it named — `IN` alone would be an "any of", which is a different and much weaker guard;
 *   * a filter's types narrow within that filter, never across the query;
 *   * a filter naming neither matches nothing, and a query with no filters matches nothing. `1 = 0` rather
 *     than an omitted predicate, because an absent guard would match everything and a conditional append
 *     that matched everything would refuse every write in the system.
 */
function tagQuerySql(query: TagQuery): { predicate: string; parameters: (string | number)[] } {
  if (query.filters.length === 0) return { predicate: '1 = 0', parameters: [] };
  const parameters: (string | number)[] = [];
  const predicates = query.filters.map((filter) => {
    const tags = filter.tags ?? [];
    const types = filter.types ?? [];
    if (tags.length === 0 && types.length === 0) return '1 = 0';
    const parts: string[] = [];
    if (tags.length > 0) {
      parts.push(
        `(SELECT COUNT(*) FROM event_tags t WHERE t.global_position = e.global_position` +
          ` AND t.tag IN (${tags.map(() => '?').join(', ')})) = ?`,
      );
      parameters.push(...tags, new Set(tags).size);
    }
    if (types.length > 0) {
      parts.push(`e.event_type IN (${types.map(() => '?').join(', ')})`);
      parameters.push(...types);
    }
    return `(${parts.join(' AND ')})`;
  });
  return { predicate: `(${predicates.join(' OR ')})`, parameters };
}

/**
 * The stream is not where the caller thought it was, or the condition no longer holds.
 *
 * Thrown inside the unit of work so the transaction unwinds, and caught immediately outside it and turned
 * back into a conflict *value*. Returning from inside the block would commit the half-written append it is
 * refusing.
 */
class Refused extends Error {}

/**
 * Somewhere to run SQL, and the transaction anything else on this connection joins.
 *
 * The checkpoint adapter is built from this rather than from a location: `record` has to commit with the
 * view rows it accounts for, and two adapters opening the same file are two connections and two
 * transactions.
 */
export type SqliteSession = Readonly<{
  database: DatabaseSync;
  inUnitOfWork<T>(work: () => Promise<T>): Promise<T>;
}>;

export type SqliteEventStore = EventStore & Readonly<{ session: SqliteSession; close(): void }>;

/**
 * Open (or create) a SQLite-backed event store.
 *
 * `location` is a file path, or `':memory:'` for a store that exists only as long as the process — which
 * is what the contract suite uses, so the same SQL runs in `make verify` with nothing installed.
 *
 * `tagsOf` is what this project's events are findable by; the default is the event's own stream, which is
 * what makes the tag index a superset of what the log already had.
 */
export function openSqliteEventStore(
  location: string,
  tagsOf: TagsOf = defaultTagsOf,
): SqliteEventStore {
  const database = new DatabaseSync(location);
  let tagging = tagsOf;
  let depth = 0;

  // WAL lets readers run while a writer holds the write lock, and is a no-op for `:memory:`. FULL
  // synchronous is the default and is what makes a committed append survive a power loss; anything
  // weaker trades the D in ACID for throughput, which an event log cannot afford.
  database.exec('PRAGMA journal_mode = WAL');
  database.exec('PRAGMA foreign_keys = ON');
  database.exec(SCHEMA);

  /**
   * One transaction, shared by this store and anything else on its connection.
   *
   * Nesting uses a SAVEPOINT rather than a counter that shrugs: an inner block that fails has to undo its
   * own writes and no more, and the alternative — leaving them in the outer transaction — would let a
   * refused append pollute a transaction that goes on to commit.
   */
  const inUnitOfWork = async <T>(work: () => Promise<T>): Promise<T> => {
    if (depth > 0) {
      depth += 1;
      const savepoint = `uow_${depth}`;
      database.exec(`SAVEPOINT ${savepoint}`);
      try {
        const result = await work();
        database.exec(`RELEASE SAVEPOINT ${savepoint}`);
        return result;
      } catch (error) {
        database.exec(`ROLLBACK TO SAVEPOINT ${savepoint}`);
        throw error;
      } finally {
        depth -= 1;
      }
    }
    database.exec('BEGIN IMMEDIATE');
    depth = 1;
    try {
      const result = await work();
      database.exec('COMMIT');
      return result;
    } catch (error) {
      database.exec('ROLLBACK');
      throw error;
    } finally {
      depth = 0;
    }
  };

  const currentStreamVersion = (streamId: string): number => {
    const row = database.prepare(CURRENT_VERSION).get(streamId) as { version: number } | undefined;
    return row?.version ?? -1;
  };

  const head = (): number => {
    const row = database.prepare(HEAD).get() as { head: number } | undefined;
    return row?.head ?? 0;
  };

  /**
   * One event, plus its tags, inside whatever transaction is open.
   *
   * The tags go in here rather than in a pass of their own, which is the whole design: an index written
   * after the append could be missing when the next conditional append checks it, and that append would
   * then be guarded by a boundary with a hole in it.
   */
  const insert = (
    event: DomainEvent,
    streamId: string,
    version: number,
    guardAgainst: number,
  ): void => {
    const result = database
      .prepare(INSERT_GUARDED)
      .run(
        streamId,
        version,
        event.type,
        event.schemaVersion,
        JSON.stringify(event.payload),
        JSON.stringify(event.actor),
        event.correlationId,
        event.causationId ?? null,
        event.occurredAt,
        streamId,
        guardAgainst,
      );
    if (result.changes === 0)
      throw new Refused('the stream is not where the caller thought it was');
    const position = Number(result.lastInsertRowid);
    for (const tag of tagging(event)) database.prepare(INSERT_TAG).run(tag, position);
  };

  const append = async (
    streamId: string,
    expectedVersion: number,
    events: readonly DomainEvent[],
  ): Promise<AppendResult> => {
    if (events.length === 0) return appended(expectedVersion);

    try {
      return await inUnitOfWork(async () => {
        let version = expectedVersion;
        for (const event of events) {
          const guardAgainst = version;
          version += 1;
          insert(event, streamId, version, guardAgainst);
        }
        return appended(version);
      });
    } catch (error) {
      // A conflict is a return value rather than a thrown error, because contention is expected under
      // load, not exceptional. The unique constraint catches what the guard could not — on SQLite that is
      // close to unreachable, since `BEGIN IMMEDIATE` holds the write lock for the whole append, but it is
      // reported the way Postgres reports it so that moving is a change of adapter, not of caller.
      if (error instanceof Refused) return versionConflict(currentStreamVersion(streamId));
      if (isRecord(error) && error.code === CONSTRAINT_VIOLATION) {
        return versionConflict(currentStreamVersion(streamId));
      }
      throw error;
    }
  };

  const read = async (streamId: string): Promise<readonly CommittedEvent[]> => {
    const rows = database.prepare(READ_STREAM).all(streamId) as unknown as EventRow[];
    return rows.map(toCommittedEvent);
  };

  async function* readAll(fromPosition: number): AsyncIterable<CommittedEvent> {
    let cursor = fromPosition;
    for (;;) {
      const rows = database
        .prepare(READ_ALL_BATCH)
        .all(cursor, READ_ALL_BATCH_SIZE) as unknown as EventRow[];
      const last = rows.at(-1);
      if (last === undefined) return;

      for (const row of rows) yield toCommittedEvent(row);
      cursor = last.global_position + 1;
    }
  }

  const readTagged = async (query: TagQuery, after = 0, until = 0): Promise<TaggedRead> => {
    const { predicate, parameters } = tagQuerySql(query);
    const ceiling = until === 0 ? head() : until;
    const rows = database
      .prepare(
        `SELECT ${EVENT_COLUMNS} FROM events e WHERE e.global_position > ?` +
          ` AND e.global_position <= ? AND ${predicate} ORDER BY e.global_position ASC`,
      )
      .all(after, ceiling, ...parameters) as unknown as EventRow[];
    return { events: rows.map(toCommittedEvent), head: ceiling };
  };

  const anythingMatching = (condition: Condition): boolean => {
    const { predicate, parameters } = tagQuerySql(condition.query);
    const row = database
      .prepare(
        `SELECT 1 AS found FROM events e WHERE e.global_position > ? AND ${predicate} LIMIT 1`,
      )
      .get(condition.after, ...parameters);
    return row !== undefined;
  };

  /**
   * The conditional append. SQLite gives the isolation for free.
   *
   * `BEGIN IMMEDIATE` takes the write lock before the condition is checked and holds it through the
   * inserts, and SQLite has one writer at a time, so the check and the write cannot be split by another
   * transaction. Postgres has to ask for `SERIALIZABLE` to get the same thing, and pays for it with a
   * retry path; here there is nothing to retry.
   */
  const appendIf = async (
    condition: Condition,
    events: readonly DomainEvent[],
  ): Promise<ConditionalAppendResult> => {
    try {
      return await inUnitOfWork(async () => {
        if (anythingMatching(condition)) throw new Refused('the condition no longer holds');
        for (const event of events) {
          // Each event still lands at the next version of the stream it names, so everything written
          // against `read` and `append` keeps working: what the condition replaced is the *guard*, not
          // the shape of the log.
          const at = currentStreamVersion(event.streamId);
          insert(event, event.streamId, at + 1, at);
        }
        return recorded(head());
      });
    } catch (error) {
      if (error instanceof Refused) return conditionConflict(head());
      throw error;
    }
  };

  const reindexTags = async (fromPosition = 0): Promise<number> =>
    inUnitOfWork(async () => {
      const rows = database.prepare(UNINDEXED_EVENTS).all(fromPosition) as unknown as EventRow[];
      let indexed = 0;
      for (const row of rows) {
        const event = toCommittedEvent(row);
        const tags = tagging(event);
        // Counted only when it made the event findable. An event this project's tagging function has
        // nothing to say about stays unindexed for good, so a run that counted it would promise an
        // index with nothing in it and never settle at zero.
        if (tags.length === 0) continue;
        for (const tag of tags) {
          database.prepare(INSERT_TAG).run(tag, event.globalPosition);
        }
        indexed += 1;
      }
      return indexed;
    });

  return {
    read,
    append,
    readAll,
    inUnitOfWork,
    head: async () => head(),
    readTagged,
    appendIf,
    reindexTags,
    retag: async (next: TagsOf): Promise<number> =>
      inUnitOfWork(async () => {
        tagging = next;
        database.exec(DELETE_TAGS);
        return reindexTags();
      }),
    session: { database, inUnitOfWork },
    close: () => database.close(),
  };
}

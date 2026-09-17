import { AsyncLocalStorage } from 'node:async_hooks';

import type { Pool, PoolClient, QueryResult, QueryResultRow } from 'pg';
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
} from '../../../application/ports/events.js';
import {
  appended,
  conditionConflict,
  createCausationId,
  createCorrelationId,
  defaultTagsOf,
  recorded,
  versionConflict,
} from '../../../application/ports/events.js';

/**
 * Postgres event-store adapter — the only file that knows the event log is SQL.
 *
 * `pg` is imported as a *type* here, so nothing loads the driver until a composition root actually
 * constructs a Pool. That is what keeps `make verify` free of infrastructure while this file is still
 * typechecked and linted.
 *
 * Concurrency is enforced twice over, deliberately:
 *   1. Each insert carries a `WHERE (SELECT MAX(version) …) = expected` guard, which catches a stale
 *      expectation — a caller that decided against version 3 while the stream had moved to 5.
 *   2. The `(stream_id, version)` unique constraint catches the true race, where two transactions both
 *      pass the guard and then try to write the same version.
 *
 * The guard alone is insufficient (two concurrent transactions see the same MAX under READ COMMITTED),
 * and the constraint alone is insufficient (a stale expectation could write a valid *later* version
 * without conflict). Both are needed.
 *
 * `appendIf` can use neither, because there is no version to compare: what it must prove is that *nothing
 * matching a query* arrived since the caller read. It asks Postgres for `SERIALIZABLE` and lets the
 * database prove it. The cost is a real one and it is the caller's: a serialisation failure is reported as
 * a conflict, and the caller re-reads and re-decides exactly as it does for a stale version.
 */

/** Postgres unique-violation SQLSTATE. */
const UNIQUE_VIOLATION = '23505';

/**
 * Postgres serialisation-failure SQLSTATE — a `SERIALIZABLE` transaction that could not be ordered
 * against a concurrent one. For a conditional append it means the same thing a broken condition does, and
 * asks the same thing of the caller: read again, decide again.
 */
const SERIALIZATION_FAILURE = '40001';

type EventRow = {
  global_position: string;
  stream_id: string;
  version: number;
  event_type: string;
  schema_version: number;
  payload: unknown;
  actor: unknown;
  correlation_id: string;
  causation_id: string | null;
  occurred_at: Date;
  recorded_at: Date;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function actorFrom(value: unknown, position: string): Actor {
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
  if (!isRecord(row.payload)) {
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
    payload: row.payload,
    occurredAt: row.occurred_at.toISOString(),
    actor: actorFrom(row.actor, row.global_position),
    correlationId: createCorrelationId(row.correlation_id),
    ...(row.causation_id === null ? {} : { causationId: createCausationId(row.causation_id) }),
    version: row.version,
    globalPosition: Number(row.global_position),
    recordedAt: row.recorded_at.toISOString(),
  };
}

const INSERT_GUARDED = `
  INSERT INTO events (
    stream_id, version, event_type, schema_version, payload, actor,
    correlation_id, causation_id, occurred_at
  )
  SELECT $1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::uuid, $8::uuid, $9::timestamptz
  WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = $1) = $10
  RETURNING global_position
`;

const EVENT_COLUMNS = `
  global_position, stream_id, version, event_type, schema_version, payload, actor,
  correlation_id, causation_id, occurred_at, recorded_at
`;

const READ_STREAM = `SELECT ${EVENT_COLUMNS} FROM events WHERE stream_id = $1 ORDER BY version ASC`;

const READ_ALL_BATCH = `
  SELECT ${EVENT_COLUMNS}
  FROM events
  WHERE global_position >= $1 AND global_position <= $2
  ORDER BY global_position ASC
  LIMIT $3
`;

/**
 * The log's own advisory lock, which is how a reader learns that a position is settled.
 *
 * A global position is assigned when a row is inserted and becomes visible when its transaction commits,
 * and those are not the same moment: two appends overlapping can take 5 and 6 and commit 6 first. A reader
 * that sees 6 and records "next is 7" has skipped 5 for good, because 5 arrives behind a checkpoint that
 * has already passed it. Nothing in the log is wrong afterwards, and the view is missing a row nothing
 * will ever put back.
 *
 * So an append takes this lock in **shared** mode before its first insert, which costs nothing because
 * shared holders do not block each other, and `readAll` takes it **exclusively** for one
 * `MAX(global_position)` query. Acquiring it exclusively means no append is between its insert and its
 * commit, so every position at or below that maximum is final: committed and visible, or aborted and gone
 * for good. Reading no further than that is what makes a single number a safe place for a projection to
 * resume from.
 *
 * The number is arbitrary and only has to be the same in every adapter that opens this log. It must not be
 * reused for anything else in the same database, which is why it lives here.
 */
const EVENTS_LOCK = 8_317_231;

/** Take the log's lock in shared mode, so appends never block each other. */
const LOCK_SHARED = 'SELECT pg_advisory_xact_lock_shared($1)';

/** Take it exclusively, which waits for every append in flight to finish. */
const LOCK_EXCLUSIVE = 'SELECT pg_advisory_xact_lock($1)';

const HEAD = 'SELECT COALESCE(MAX(global_position), 0) AS head FROM events';

const INSERT_TAG = `
  INSERT INTO event_tags (tag, global_position) VALUES ($1, $2)
  ON CONFLICT DO NOTHING
`;

const DELETE_TAGS = 'DELETE FROM event_tags';

const UNINDEXED_EVENTS = `
  SELECT ${EVENT_COLUMNS}
  FROM events
  WHERE global_position >= $1
    AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
  ORDER BY global_position ASC
  LIMIT $2
`;

/** Batched so a rebuild over a long log does not materialise the whole thing in memory. */
const READ_ALL_BATCH_SIZE = 500;

/**
 * A `TagQuery` as a SQL predicate over `e`, plus its parameters, numbered from `$next`.
 *
 * `matchesFilter` in the port is the definition; this is its translation, and the contract suite is what
 * holds the two to each other. Every SQL adapter carries its own copy of this translation, in whatever
 * placeholder syntax its driver wants, deliberately duplicated rather than shared: an adapter that
 * imports another adapter is two adapters that cannot be pruned apart.
 *
 *   * a filter's tags are a **conjunction** — the number of its tags found against the event must equal
 *     how many it named, because `= ANY` on its own is an "any of" and a much weaker guard than the caller
 *     asked for;
 *   * its types narrow within that filter only;
 *   * a filter naming neither, and a query with no filters at all, match nothing: `1 = 0` rather than a
 *     missing predicate, because an absent guard matches everything and a conditional append that matched
 *     everything would refuse every write in the system.
 */
function tagQuerySql(query: TagQuery, next: number): { predicate: string; parameters: unknown[] } {
  if (query.filters.length === 0) return { predicate: '1 = 0', parameters: [] };
  const parameters: unknown[] = [];
  const placeholder = (): string => `$${next + parameters.length}`;
  const predicates = query.filters.map((filter) => {
    const tags = filter.tags ?? [];
    const types = filter.types ?? [];
    if (tags.length === 0 && types.length === 0) return '1 = 0';
    const parts: string[] = [];
    if (tags.length > 0) {
      const tagsAt = placeholder();
      parameters.push([...tags]);
      const countAt = placeholder();
      parameters.push(new Set(tags).size);
      parts.push(
        `(SELECT COUNT(*) FROM event_tags t WHERE t.global_position = e.global_position` +
          ` AND t.tag = ANY(${tagsAt})) = ${countAt}`,
      );
    }
    if (types.length > 0) {
      const typesAt = placeholder();
      parameters.push([...types]);
      parts.push(`e.event_type = ANY(${typesAt})`);
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
 * refusing — and in Postgres a failed statement poisons the transaction until something rolls back, so
 * this is not only tidier, it is the only correct shape.
 */
class Refused extends Error {}

/**
 * Somewhere to run SQL, and the transaction anything else on this connection joins.
 *
 * The checkpoint adapter is built from this rather than from the pool: `record` has to commit with the
 * view rows it accounts for, and a second pool client is a second transaction.
 */
export type PostgresSession = Readonly<{
  query<R extends QueryResultRow>(sql: string, parameters?: unknown[]): Promise<QueryResult<R>>;
  inUnitOfWork<T>(work: () => Promise<T>, options?: { serializable?: boolean }): Promise<T>;
}>;

export type PostgresEventStore = EventStore & Readonly<{ session: PostgresSession }>;

/**
 * `tagsOf` is what this project's events are findable by; the default is the event's own stream, which is
 * what makes the tag index a superset of what the log already had.
 */
export function createPostgresEventStore(
  pool: Pool,
  tagsOf: TagsOf = defaultTagsOf,
): PostgresEventStore {
  let tagging = tagsOf;

  /**
   * Which client the current transaction is on, scoped to the async call that opened it.
   *
   * `AsyncLocalStorage` rather than a variable in this closure, and the difference is not stylistic: two
   * appends on one store run concurrently — `make test-integration` races eight of them — and a shared
   * variable would have the second one issue its statements on the first one's client, inside the first
   * one's transaction. Scoped this way, concurrent callers each get their own client and a nested call
   * sees its own caller's, which is exactly what "the read-side adapter joins the append's transaction"
   * needs.
   */
  const transaction = new AsyncLocalStorage<{ client: PoolClient; depth: number }>();

  const query = async <R extends QueryResultRow>(
    sql: string,
    parameters: unknown[] = [],
  ): Promise<QueryResult<R>> => {
    const open = transaction.getStore();
    return open === undefined
      ? pool.query<R>(sql, parameters)
      : open.client.query<R>(sql, parameters);
  };

  /**
   * One transaction, shared by this store and anything else on its session.
   *
   * Outside one, every method here runs on a pool client of its own and commits itself, exactly as it
   * always has. Inside one, everything runs on the pinned client and nothing commits until the outermost
   * call returns.
   *
   * Nesting uses a SAVEPOINT rather than a counter that shrugs: an inner block that fails has to undo its
   * own writes and no more. In Postgres it also *has* to, and not merely ought to — a failed statement
   * poisons the whole transaction until something rolls back to a savepoint, so without this an inner
   * failure would take the outer commit with it.
   *
   * `serializable` asks for the isolation `appendIf` needs. It is set on `BEGIN`, which is the only place
   * Postgres accepts it, so an `appendIf` called *inside* somebody else's unit of work runs at that
   * transaction's isolation level — open it with `{ serializable: true }` when a conditional append is
   * going to happen inside it.
   */
  const inUnitOfWork = async <T>(
    work: () => Promise<T>,
    options?: { serializable?: boolean },
  ): Promise<T> => {
    const open = transaction.getStore();
    if (open !== undefined) {
      const savepoint = `uow_${open.depth + 1}`;
      await open.client.query(`SAVEPOINT ${savepoint}`);
      try {
        const result = await transaction.run({ ...open, depth: open.depth + 1 }, work);
        await open.client.query(`RELEASE SAVEPOINT ${savepoint}`);
        return result;
      } catch (error) {
        await open.client.query(`ROLLBACK TO SAVEPOINT ${savepoint}`);
        throw error;
      }
    }

    const client = await pool.connect();
    try {
      await client.query(
        options?.serializable === true ? 'BEGIN ISOLATION LEVEL SERIALIZABLE' : 'BEGIN',
      );
      const result = await transaction.run({ client, depth: 1 }, work);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  };

  const currentStreamVersion = async (streamId: string): Promise<number> => {
    const result = await query<{ max: number | null }>(
      'SELECT MAX(version) AS max FROM events WHERE stream_id = $1',
      [streamId],
    );
    return result.rows[0]?.max ?? -1;
  };

  const head = async (): Promise<number> => {
    const result = await query<{ head: string }>(HEAD);
    return Number(result.rows[0]?.head ?? 0);
  };

  /**
   * One event, plus its tags, inside whatever transaction is open.
   *
   * The tags go in here rather than in a pass of their own, which is the whole design: an index written
   * after the append could be missing when the next conditional append checks it, and that append would
   * then be guarded by a boundary with a hole in it.
   */
  /**
   * Hold the log in shared mode until this transaction ends — see `EVENTS_LOCK`.
   *
   * Before the first insert, always, and re-entrant: taking it twice in one transaction is free. Shared,
   * so two appends never wait for each other; what waits is a reader asking whether a position has
   * settled.
   */
  const holdTheLog = async (): Promise<void> => {
    await query(LOCK_SHARED, [EVENTS_LOCK]);
  };

  const insert = async (
    event: DomainEvent,
    streamId: string,
    version: number,
    guardAgainst: number,
  ): Promise<void> => {
    const result = await query<{ global_position: string }>(INSERT_GUARDED, [
      streamId,
      version,
      event.type,
      event.schemaVersion,
      JSON.stringify(event.payload),
      JSON.stringify(event.actor),
      event.correlationId,
      event.causationId ?? null,
      event.occurredAt,
      guardAgainst,
    ]);
    const position = result.rows[0]?.global_position;
    if (position === undefined)
      throw new Refused('the stream is not where the caller thought it was');
    for (const tag of tagging(event)) await query(INSERT_TAG, [tag, position]);
  };

  const append = async (
    streamId: string,
    expectedVersion: number,
    events: readonly DomainEvent[],
  ): Promise<AppendResult> => {
    if (events.length === 0) return appended(expectedVersion);

    try {
      return await inUnitOfWork(async () => {
        await holdTheLog();
        let version = expectedVersion;
        for (const event of events) {
          const guardAgainst = version;
          version += 1;
          await insert(event, streamId, version, guardAgainst);
        }
        return appended(version);
      });
    } catch (error) {
      // A conflict is a return value, not a thrown error: contention is expected under load. The guard
      // catches a stale expectation; the unique constraint catches the true race, where two transactions
      // both passed the guard.
      if (error instanceof Refused) return versionConflict(await currentStreamVersion(streamId));
      if (isRecord(error) && error.code === UNIQUE_VIOLATION) {
        return versionConflict(await currentStreamVersion(streamId));
      }
      throw error;
    }
  };

  const read = async (streamId: string): Promise<readonly CommittedEvent[]> => {
    const result = await query<EventRow>(READ_STREAM, [streamId]);
    return result.rows.map(toCommittedEvent);
  };

  /**
   * The highest position nothing earlier can still be committed behind — see `EVENTS_LOCK`.
   *
   * Its own transaction, so the exclusive hold lasts microseconds: long enough to prove nothing is in
   * flight, short enough that the appends queueing behind it barely notice. Two statements rather than
   * one, because the order in which Postgres evaluates a lock function beside an aggregate is not
   * something to rely on.
   */
  const settledPosition = async (): Promise<number> =>
    inUnitOfWork(async () => {
      await query(LOCK_EXCLUSIVE, [EVENTS_LOCK]);
      return await head();
    });

  /**
   * The last **settled** position, which is the only kind a decision may be guarded at.
   *
   * The same protocol `readAll` uses, and for a reason that took a reproduction to see: a boundary past
   * an event still in flight is a boundary the guard cannot check. Two appends take 5 and 6, 6 commits
   * first, a decision reads a head of 6 while 5 is invisible — and `appendIf` then looks for anything
   * matching *after* 6 and never sees 5, because 5 sits below its own boundary. The append is allowed and
   * the constraint it was meant to hold is broken, with a correct-looking log to show for it.
   *
   * Waiting for the appends in flight fixes it twice over: the boundary is one nothing can arrive behind,
   * and the read that follows sees the very events the decision has to know about.
   *
   * Inside a unit of work, the answer is that transaction's own view instead — a caller reading its own
   * writes rather than drawing a boundary, which is what an inline read model does. Asking for the settled
   * position there would wait on a lock the transaction is itself holding.
   */
  const settledHead = async (): Promise<number> =>
    transaction.getStore() === undefined ? await settledPosition() : await head();

  /**
   * Replay in global order, and never past a position that is not settled yet.
   *
   * The ceiling is taken once, at the start: an event appended while a long replay is running belongs to
   * the next pass, and a checkpoint that stopped short of it loses nothing.
   */
  async function* readAll(fromPosition: number): AsyncIterable<CommittedEvent> {
    const settled = await settledPosition();
    let cursor = fromPosition;
    while (cursor <= settled) {
      const result = await query<EventRow>(READ_ALL_BATCH, [cursor, settled, READ_ALL_BATCH_SIZE]);
      const last = result.rows.at(-1);
      if (last === undefined) return;

      for (const row of result.rows) yield toCommittedEvent(row);
      cursor = Number(last.global_position) + 1;
    }
  }

  const readTagged = async (tagQuery: TagQuery, after = 0, until = 0): Promise<TaggedRead> => {
    const { predicate, parameters } = tagQuerySql(tagQuery, 3);
    const ceiling = until === 0 ? await settledHead() : until;
    const result = await query<EventRow>(
      `SELECT ${EVENT_COLUMNS} FROM events e WHERE e.global_position > $1` +
        ` AND e.global_position <= $2 AND ${predicate} ORDER BY e.global_position ASC`,
      [after, ceiling, ...parameters],
    );
    return { events: result.rows.map(toCommittedEvent), head: ceiling };
  };

  const anythingMatching = async (condition: Condition): Promise<boolean> => {
    const { predicate, parameters } = tagQuerySql(condition.query, 2);
    const result = await query(
      `SELECT 1 FROM events e WHERE e.global_position > $1 AND ${predicate} LIMIT 1`,
      [condition.after, ...parameters],
    );
    return (result.rowCount ?? 0) > 0;
  };

  /**
   * Append only if nothing matching the condition arrived since the caller read.
   *
   * `SERIALIZABLE`, not a clever `WHERE NOT EXISTS`: the guard is the *absence* of rows, and absence is
   * what no lock in a row-locking database can hold. Postgres detects the conflict at commit and raises a
   * serialisation failure, which is reported here as a conflict — because for the caller it is the same
   * fact and the same next move, re-read and re-decide.
   */
  const appendIf = async (
    condition: Condition,
    events: readonly DomainEvent[],
  ): Promise<ConditionalAppendResult> => {
    try {
      return await inUnitOfWork(
        async () => {
          await holdTheLog();
          if (await anythingMatching(condition)) throw new Refused('the condition no longer holds');
          for (const event of events) {
            // Each event still lands at the next version of the stream it names, so everything written
            // against `read` and `append` keeps working: what the condition replaced is the *guard*, not
            // the shape of the log.
            const at = await currentStreamVersion(event.streamId);
            await insert(event, event.streamId, at + 1, at);
          }
          return recorded(await head());
        },
        { serializable: true },
      );
    } catch (error) {
      if (error instanceof Refused) return conditionConflict(await head());
      if (isRecord(error) && error.code === SERIALIZATION_FAILURE) {
        return conditionConflict(await head());
      }
      throw error;
    }
  };

  /**
   * Index what this store's tagging function has not indexed yet, a batch at a time.
   *
   * Resumable on purpose: a project adopting tags runs this over a log that may be very long, and a run
   * that dies halfway is continued by running it again rather than started over.
   */
  const reindexTags = async (fromPosition = 0): Promise<number> => {
    let indexed = 0;
    let cursor = fromPosition;
    for (;;) {
      const done = await inUnitOfWork(async () => {
        const result = await query<EventRow>(UNINDEXED_EVENTS, [cursor, READ_ALL_BATCH_SIZE]);
        const last = result.rows.at(-1);
        if (last === undefined) return true;
        for (const row of result.rows) {
          const event = toCommittedEvent(row);
          const tags = tagging(event);
          // Counted only when it made the event findable. An event with no tags is re-read by every
          // later run, which is a scan and not a rewrite, and the alternative is a count that never
          // reaches zero.
          if (tags.length === 0) continue;
          for (const tag of tags) await query(INSERT_TAG, [tag, event.globalPosition]);
          indexed += 1;
        }
        cursor = Number(last.global_position) + 1;
        return false;
      });
      if (done) return indexed;
    }
  };

  return {
    read,
    append,
    readAll,
    inUnitOfWork,
    head: settledHead,
    readTagged,
    appendIf,
    reindexTags,
    retag: async (next: TagsOf): Promise<number> =>
      inUnitOfWork(async () => {
        tagging = next;
        await query(DELETE_TAGS);
        // Inside this unit of work, so the old index is never visible as gone: either the whole re-index
        // commits or the old one stands.
        return reindexTags();
      }),
    session: { query, inUnitOfWork },
  };
}

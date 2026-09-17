/**
 * The event-store port and the envelope it carries.
 *
 * Five capabilities, and a store that cannot offer all five must not be adopted:
 *
 *   1. append with an expected version (optimistic concurrency, one stream at a time)
 *   2. ordered reads of a single stream
 *   3. replay from position zero, across all streams
 *   4. reads by tag query, which return the store head as well as the events
 *   5. append conditional on a tag query — the same guarantee as (1) over a boundary that is not one
 *      stream
 *
 * The last two are the **Dynamic Consistency Boundary**, and they are additive: a stream and its
 * `expectedVersion` remain the default boundary, and every slice generated so far uses nothing else.
 * `docs/adr/0001-a-dcb-capable-log.md` in the factory that made this project records why the log carries
 * both. A tag is the more general of the two — stream-per-aggregate is the case where every event carries
 * exactly one tag, `stream:<streamId>`, which is what `defaultTagsOf` below actually returns.
 *
 * Nothing here names Postgres, SQL, or a vendor. The adapters under `src/adapters/driven/` implement
 * it — the in-memory fake, and the real store this project answered the event-store axis with, where
 * it answered with one — and the same contract suite runs against every one of them.
 */

/** `expectedVersion` for a stream that must not exist yet, which is how first-write races are detected. */
export const NO_STREAM = -1;

/** Who or what caused the event. Recorded on every event so the log answers "who did this". */
export type Actor = Readonly<{ kind: string; id: string }>;

/**
 * Correlation and causation are **UUIDs**, and branded so the compiler knows it. They are written by one
 * service and read by another, often years later by a tool nobody has written yet, so the one thing they
 * must be is unambiguous: a UUID is unique without a registry, parses the same everywhere, and cannot
 * quietly become a request path, a customer reference, or an empty string that nothing rejects.
 *
 * Two brands rather than one alias used twice, because they sit side by side in every event below and are
 * both strings underneath. Swapping them is invisible at runtime and destroys the one thing they exist for
 * — a causal tree in which everything appears to have caused itself.
 */
export type CorrelationId = string & { readonly __brand: 'CorrelationId' };
export type CausationId = string & { readonly __brand: 'CausationId' };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Lower-cased on the way through, so one id has one spelling. Postgres hands back the canonical form
 * whatever went in, and a store that keeps the caller's casing would compare unequal to the same id read
 * back from a `uuid` column.
 */
const asUuid = (raw: string, what: string): string => {
  if (!UUID.test(raw)) throw new Error(`a ${what} must be a UUID, and '${raw}' is not`);
  return raw.toLowerCase();
};

/**
 * Parse an incoming correlation id, or `randomUUID()` to start a new business transaction. Parsing at the
 * edge is what keeps the brand honest: a value that arrived as text — from a header, a queue message, or a
 * stored row — is checked once, here, rather than trusted everywhere.
 */
export const createCorrelationId = (raw: string): CorrelationId =>
  asUuid(raw, 'correlation id') as CorrelationId; // justified: validated above, then branded

/**
 * Parse the id of the message that directly caused an event. The rule, from Greg Young: responding to a
 * message, you copy its correlation id as your own and take its id as your causation id.
 */
export const createCausationId = (raw: string): CausationId =>
  asUuid(raw, 'causation id') as CausationId; // justified: validated above, then branded

export type DomainEvent = Readonly<{
  type: string;
  schemaVersion: 1;
  streamId: string;
  payload: Readonly<Record<string, unknown>>;
  /**
   * Domain time, as an ISO-8601 instant. Taken from a clock at the edge and passed in as a typed input —
   * the domain never reads the clock, which is what makes a decision function testable without freezing
   * global time. Distinct from `recordedAt` below, and conflating the two is how clock problems become
   * unreconcilable.
   */
  occurredAt: string;
  actor: Actor;
  /** The whole business transaction this event belongs to. */
  correlationId: CorrelationId;
  /**
   * The message that directly caused this event, and absent when nothing did — the first event of a
   * transaction has no cause to point at, and inventing one would be a lie about the shape of the tree.
   */
  causationId?: CausationId;
}>;

/** What the store gives back: the event plus the facts only the store can know. */
export type CommittedEvent = DomainEvent &
  Readonly<{
    version: number;
    globalPosition: number;
    recordedAt: string;
  }>;

/**
 * A version conflict is a **return value, not a thrown error**. Contention is expected under load, not
 * exceptional: the caller re-reads and re-decides. Throwing would push ordinary concurrency into an error
 * path and invite a `catch` that swallows it.
 */
export type AppendResult =
  | Readonly<{ outcome: 'appended'; version: number }>
  | Readonly<{ outcome: 'version-conflict'; actualVersion: number }>;

// ── The other consistency boundary ─────────────────────────────────────────────────────────────────
//
// Everything from here to `EventStore` is the Dynamic Consistency Boundary. Read it only when a decision
// cannot be guarded by one stream's version — a constraint spanning two entities, where either can change
// under you. Until then `append` is the whole port.

/**
 * The tag every event carries by default: its own stream, as a tag.
 *
 * Written as a function rather than inlined because it is the one place the correspondence between the two
 * boundaries is spelled: a stream id *is* a tag, so a log that indexes tags indexes the streams it already
 * had.
 */
export const streamTag = (streamId: string): string => `stream:${streamId}`;

/** How an adapter learns what to index an event by. A plain function, so a project's tagging rule is
 * testable without a database. */
export type TagsOf = (event: DomainEvent) => readonly string[];

/**
 * What an event is indexed by, unless this project says otherwise.
 *
 * Tags are **derived, never modelled**: nothing in `docs/event-model/model.yaml` names one, because a tag
 * is a technical index over the log and not a fact about the business. This function is where a project
 * decides what its events are findable by — usually the identifying attributes of the payload, alongside
 * the stream:
 *
 * ```ts
 * const tagsOf: TagsOf = (event) => {
 *   const tags = [streamTag(event.streamId)];
 *   const courseId = event.payload['courseId'];
 *   if (typeof courseId === 'string') tags.push(`course:${courseId}`);
 *   return tags;
 * };
 * ```
 *
 * Pass it to the adapter's factory. Changing it later is safe and cheap — the index is derived, so
 * `retag` rebuilds it from the log — which is the whole reason tags live in an index of their own rather
 * than on the event row.
 */
export const defaultTagsOf: TagsOf = (event) => [streamTag(event.streamId)];

/**
 * One conjunction: an event matches when it carries **every** tag named here and, where `types` names
 * any, when its type is one of them. A filter naming neither matches nothing — see `TagQuery`.
 */
export type TagFilter = Readonly<{ tags?: readonly string[]; types?: readonly string[] }>;

/**
 * Which events a decision loads, and — as part of a `Condition` — which events invalidate it.
 *
 * A disjunction of filters, because the constraint that motivates any of this spans entities: deciding
 * whether a student may subscribe to a course needs the course's events *and* that student's events, which
 * is two filters and cannot be one. Think of it as the SQL query that fetches exactly the events needed to
 * decide.
 *
 * **An empty query matches nothing**, never everything. A condition that matched everything would refuse
 * every concurrent append in the system, and a read that matched everything would quietly become a full
 * replay; both are failures worth being loud about, and neither is what anybody meant to write.
 */
export type TagQuery = Readonly<{ filters: readonly TagFilter[] }>;

/**
 * Whether one event matches a filter, given the tags it was indexed by.
 *
 * In the port rather than in each adapter because it is the definition, and an adapter that computed it
 * differently in SQL would be a second definition nothing compares. The in-memory adapter uses this
 * directly; the SQL adapters translate it, and the contract suite is what holds the translation to it.
 */
export function matchesFilter(
  filter: TagFilter,
  event: CommittedEvent,
  tags: readonly string[],
): boolean {
  const wanted = filter.tags ?? [];
  const types = filter.types ?? [];
  if (wanted.length === 0 && types.length === 0) return false;
  if (types.length > 0 && !types.includes(event.type)) return false;
  return wanted.every((tag) => tags.includes(tag));
}

export function matchesQuery(
  query: TagQuery,
  event: CommittedEvent,
  tags: readonly string[],
): boolean {
  return query.filters.some((filter) => matchesFilter(filter, event, tags));
}

/**
 * What a decision was made from, and the position it was made at.
 *
 * `head` is the store's last global position at the moment of the read — zero for an empty log. It is not
 * a nicety: it is the anchor a `Condition` is built from, so "these are the facts I decided on" and
 * "nothing else has happened since" are one round trip rather than two that can disagree.
 *
 * It is also read-your-writes made concrete. A caller that appends and then needs a
 * subscription-maintained view to have caught up can wait for a *specific* position instead of polling
 * blindly.
 */
export type TaggedRead = Readonly<{ events: readonly CommittedEvent[]; head: number }>;

/**
 * The guard on a conditional append: `query` must have matched nothing after `after`.
 *
 * `after` is the `head` of the `TaggedRead` the decision was made from. The pair is the boundary — dynamic
 * because the caller draws it per decision, out of tags, rather than inheriting it from how streams were
 * laid out months earlier.
 */
export type Condition = Readonly<{ query: TagQuery; after: number }>;

/**
 * A conditional append either recorded, or found its condition broken. `head` is the store head as found,
 * so a caller that retries reads from there.
 *
 * A conflict is a **value** here for the same reason `AppendResult`'s is, and this is where the two
 * boundaries agree: contention is ordinary, and a caller re-reads and re-decides.
 */
export type ConditionalAppendResult =
  | Readonly<{ outcome: 'recorded'; head: number }>
  | Readonly<{ outcome: 'condition-conflict'; head: number }>;

export function recorded(head: number): ConditionalAppendResult {
  return { outcome: 'recorded', head };
}

export function conditionConflict(head: number): ConditionalAppendResult {
  return { outcome: 'condition-conflict', head };
}

export interface EventStore {
  read(streamId: string): Promise<readonly CommittedEvent[]>;
  append(
    streamId: string,
    expectedVersion: number,
    events: readonly DomainEvent[],
  ): Promise<AppendResult>;
  /**
   * Replay across all streams from a global position. This exists so read models can be rebuilt from
   * zero — without it they are not disposable, and a projection bug becomes unfixable.
   */
  readAll(fromPosition: number): AsyncIterable<CommittedEvent>;
  /**
   * One transaction, which an append and somebody else's write share.
   *
   * Inside `work`, `append` and `appendIf` do **not** commit: returning from it commits everything once,
   * and a throw rolls all of it back. Outside it they commit themselves, exactly as they always have, so
   * nothing already written needs to know this exists.
   *
   * Two things need it, and they are the same need. A read model materialised **inline** is written here,
   * so a query can never see an event whose view row is missing — and a failed view write takes the append
   * down with it. A projection maintained **asynchronously** records its checkpoint here, in the same
   * transaction as the rows it derived, which is what makes it exactly-once rather than
   * approximately-once. A checkpoint committed separately from the view it describes is not a checkpoint;
   * it is a race with a number in it.
   *
   * Nesting is allowed and re-entrant: the outermost call owns the commit. Any other adapter built from
   * this store's session is inside it, which is why the read-side adapters are constructed from this one.
   */
  inUnitOfWork<T>(work: () => Promise<T>): Promise<T>;
  /**
   * The last global position in the log, or zero when it is empty.
   *
   * The boundary a decision is made against, taken **once** and then handed to every read that decision
   * needs. A command that reads twice and uses the second read's head has promised something it never
   * checked: an event matching the first query could have arrived between the two reads, before that
   * head, and the conditional append would not look for it. Pin it here, pass it as `until`, and that
   * mistake has nowhere to happen:
   *
   * ```ts
   * const boundary = await store.head();
   * const course = await store.readTagged(byCourse, 0, boundary);
   * const student = await store.readTagged(byStudent, 0, boundary);
   * await store.appendIf({ query: byCourseOrStudent, after: boundary }, [event]);
   * ```
   */
  head(): Promise<number>;
  /**
   * The events matching `query` in `(after, until]`, and the position they are as of.
   *
   * This is the DCB read: what a decision loads. `after` is for resuming a long read, not for the guard.
   * `until` is the ceiling — zero for none, which is every position, since the log starts at one — and it
   * is what a decision reading twice pins first, so both reads see the same log. The `head` handed back is
   * what the facts are as of: `until` when it is given, the store's head when it is not, and either way it
   * is what a `Condition` is built from.
   */
  readTagged(query: TagQuery, after?: number, until?: number): Promise<TaggedRead>;
  /**
   * Append only if nothing matching `condition.query` was recorded after `condition.after`.
   *
   * The events still name their streams and still land at gapless per-stream versions — the store assigns
   * each one the next version of the stream it names — so `read`, `folds` and every slice written against
   * `append` keep working unchanged. What differs is only what the write is guarded by.
   */
  appendIf(condition: Condition, events: readonly DomainEvent[]): Promise<ConditionalAppendResult>;
  /**
   * Index events this store's tagging function has not indexed yet; resolves to how many.
   *
   * The verb an already-running project needs: applying the migration creates an empty index, and this is
   * what fills it from the history that is already there. Idempotent, so running it twice indexes nothing
   * the second time and a run that died halfway is resumed by running it again.
   */
  reindexTags(fromPosition?: number): Promise<number>;
  /**
   * Adopt a new tagging function and rebuild the whole index under it; resolves to how many events were
   * indexed.
   *
   * Because the index is derived, what a project tags is a decision it can change — unlike the events
   * themselves. Both halves happen together on purpose: an index rebuilt under one function while appends
   * carry on under another is an index that disagrees with itself.
   */
  retag(tagsOf: TagsOf): Promise<number>;
}

export function versionConflict(actualVersion: number): AppendResult {
  return { outcome: 'version-conflict', actualVersion };
}

export function appended(version: number): AppendResult {
  return { outcome: 'appended', version };
}

/** The expected version to pass when appending to a stream whose history you have just read. */
export function currentVersion(events: readonly CommittedEvent[]): number {
  return events.at(-1)?.version ?? NO_STREAM;
}

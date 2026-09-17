# 0001. The log records tags, so a Dynamic Consistency Boundary stays available

Date: 2026-09-10

## Status

Accepted

## Context

Every project this factory generates writes its events through one port. `EventStore.append(stream_id,
expected_version, events)` makes a stream the consistency boundary and a stream version the only concurrency
control there is, `folds` is restricted to a slice's own stream, and `check.py` refuses to let a state-change
slice reach `planned` without naming its `stream`. That is stream-per-aggregate, end to end, and it was never
decided — it is what the first adapter did and everything since agreed with.

Where the field has moved is **Dynamic Consistency Boundaries** (Sara Pellegrini, "Killing the Aggregate"):
no aggregate object, consistency enforced by an atomic conditional append against a *query over tagged
events* rather than against a stream's version, the decision composed per use case. Martin Dilger's *How does
DCB affect Event Modeling* (6 July 2026) answers its own title with "it's not affected at all — quite the
opposite, everything gets simpler": aggregates are Static Consistency Boundaries, and the up-front questions
DCB removes — where is the aggregate, how are streams structured, where are the boundaries — are exactly the
ones he says are "set in stone" by production, where "changing those decisions later is not impossible, but
typically a lot of work and typically nobody does that".

That last sentence is the whole of this decision, because it is also true of
us. Four implementations were read as source rather than as documentation
before it was taken:

- `dilgerma/eventsourcing-book`, the book's own repository, serves one read model as a per-query fold and
  another — cross-stream — from a projected table, and has aggregates.
- `SBortz/understanding-eventsourcing-dotnet` implements one event model four ways: aggregate,
  command-handler-without-ES, decider, boundless. All four are sanctioned ports of the same model.
- `fmodel` is `Decider` + `View` and nothing else.
- `gnschenker/eventsourcing-dcb-kotlin` is aggregate-free DCB on Postgres, and it ships all three read-model
  lifecycles — `project` ("nothing is persisted; the next call reads the history again"), `SyncProjection`
  ("updated in the same transaction as append"), `AsyncProjection` ("state and the store head are saved
  together") — with our `materialisation` semantics exactly.

So Event Modeling is agnostic about the write-side mechanism, the Decider is not a deviation, and the
three-way `materialisation` choice survives the question untouched. What does *not* survive is the assumption
that a stream id is the only boundary a generated log can ever express.

**The asymmetry is the argument.** A tag is more general than a stream id: stream-per-aggregate is the special
case where every event carries exactly one tag, `stream:<stream_id>`. A log that records tags can grow a DCB
write path later. A log that records only `stream_id` cannot, because acquiring one means rewriting history it
is forbidden to rewrite. The cheap direction is available now and closed later, and that is true whichever way
the *default* write path goes.

## Decision

**The log becomes DCB-capable, additively, and stream-per-aggregate remains the default write path.**

1. **Tags are recorded in a derived index, not on the event row.** `event_tags (tag, global_position)` is a
   table *derived* from the log, maintained inside the same transaction as the append that produces the
   events. `events` is not altered — no new column, no backfill of an append-only table, no change to what
   001 and 002 created. A project already in production adopts this by applying one additive migration and
   replaying its own log into the index, which is the same rebuild any read model gets.
2. **Tags are derived, never modelled.** They come from a `tags_of(event)` function the project owns, whose
   default is `("stream:" + event.stream_id,)` — so the sentence "stream-per-aggregate is the case where every
   event carries one tag" is literally what the code does. The event model has no tag frame and no tag field;
   Dilger's reason is ours ("it's not essential to the business, it's a technical optimization. So there's no
   place for it in the Event Model").
3. **Two capabilities, one port.** `append(stream_id, expected_version, events)` is unchanged and remains what
   every generated slice calls. `append_if(condition, events)` is the conditional append: a tag query plus the
   store head the caller decided from. `read_tagged(query, after, until)` returns the matching events *and*
   the position they are as of, so what a decision was made from and what it is guarded against are one
   number. A decision needing two queries pins that number first with `head()` and passes it as `until`,
   which is what stops a caller from guarding with a position its facts do not cover. A slice declares which
   capability it uses; neither is deprecated.
4. **A conflict stays a value.** `ConditionConflict(head)` beside `VersionConflict(actual_version)`.
   `eventsourcing-dcb-kotlin` raises where we return, and the reason we return is written down in `events.py`:
   contention is expected under load, and raising invites an `except` that swallows it.
5. **The seam is one mechanism, and it serves three callers.** `unit_of_work()` on the store suspends
   `append`'s own commit for its duration. The tag index writes through it, an `inline` read model writes
   through it, and an `async` projection advances its checkpoint through it. `append` outside a unit of work
   commits itself exactly as it does today.
6. **The model contract is not changed by this ADR.** `stream` stays required of a state-change slice at
   `planned`, and `folds` still means the slice's own stream. Under DCB neither is the right question — what a
   command loads is derived from its Given/When/Then's GIVEN, per command — but that is a change to what
   `make check-model` demands of every project, and it is recorded here as owed, not taken. Future work carries
   it as S10 and S11. **Taken since, in [`0002`](0002-the-guard-a-slice-declares.md):** a state-change slice
   declares `stream` or a tag `guard`, and what it folds must be what that guard covers.

## Consequences

- A generated project can express a constraint that spans entities — the course-subscriptions case, where
  capacity and a student's subscription count are checked together — without a process manager. That is the
  thing stream-per-aggregate cannot hold, and it is why the capability is worth the two tables.
- **Postgres pays for it with isolation, not with a trick.** A conditional append opens `SERIALIZABLE`, checks
  the condition, inserts and commits. Serialisation failures are therefore a retry the caller owns, and that
  is a cost the per-stream guard does not have. SQLite gets the same guarantee free from serialised writers;
  the in-memory adapter is single-threaded and, as with `expected_version`, proves the semantics and not the
  race.
- **Nothing already generated changes behaviour.** An untagged append behaves exactly as it did; the contract
  suite proves that as a case, in every adapter, rather than leaving it as a claim.
- **A project already in production owes two steps, both of its own choosing:** apply `003` and `004`, then run
  the rebuild to index the history it already has. Until it does, `append_if` and `read_tagged` see only the
  events appended since. The `CHANGELOG` entry says so; nothing writes into a project uninvited.
- **A position is not settled when it is visible, and the read side had to be told.** Postgres assigns a
  global position at insert and reveals it at commit, so two overlapping appends can commit out of position
  order and a projection reading the later one would skip the earlier one permanently. The adapter answers it
  rather than the runner: an append holds the log's advisory lock in shared mode until it commits — shared, so
  appends never block each other — and `read_all` takes it exclusively for one `MAX(global_position)`, which
  proves nothing is in flight and gives a ceiling every position below is final at. A replay therefore waits
  for the appends in flight instead of skipping past them. **The write path needs it too, and worse:** a
  decision guarded at a boundary past an event still in flight is guarded from *after* that event, so the
  conditional append never looks where it is — the seat is claimed twice and the log looks correct
  afterwards. `head` is therefore the settled position as well, and waiting for it also makes the read that
  follows see the event the decision has to know about. The alternative considered was a commit-ordered
  cursor — a transaction id beside the position, ordered by `(tx, position)` — which needs no waiting but
  changes the checkpoint from one number to two, in every adapter and every language, and an additive column
  on `events`. If the wait ever becomes the constraint, that is the next step and not a redesign.
- The tag index is a second place a position is recorded, so it is a second place that can be wrong. It is
  written in the append's transaction — never after it — precisely so it cannot lag the log it indexes, and
  the contract suite asserts that an append's events and their tags arrive together or not at all.
- `skills/event-sourcing/resources/event-store.md` presented the per-stream compare-and-swap as the only way
  to guard an append. It now carries both, and says which this factory ships as the default.

## Alternatives considered

**Tags as a `text[]` column on `events`, as the Kotlin reference has it.** Rejected on the adoption cost, not
on taste: the column is additive but the *history* is not, and filling it means an `UPDATE` on the one table
002 installs a trigger to refuse. A derived index needs no rewrite, and being derived it can be rebuilt when a
project changes what it tags.

**Wait for the model contract first (S10/S11), then migrate the log.** Rejected because it inverts the
asymmetry. The model's contract can change in any release; the log's cannot change at all once history exists.
Recording tags now costs one migration and one rebuild, and postponing it costs every project generated in the
meantime the option entirely.

**Replace stream-per-aggregate.** Not supported by what was read. `03-decider-model` is one of four sanctioned
ports of the book's own model, the book's own repository has aggregates, and every generated project, contract
suite and slice already speaks `expected_version`. DCB becomes *expressible*; the aggregate does not become
forbidden.

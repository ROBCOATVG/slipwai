"""The event-store port and the envelope it carries.

Five capabilities, and a store that cannot offer all five must not be adopted:

  1. append with an expected version (optimistic concurrency, one stream at a time)
  2. ordered reads of a single stream
  3. replay from position zero, across all streams
  4. reads by tag query, which return the store head as well as the events
  5. append conditional on a tag query — the same guarantee as (1) over a boundary that is not
     one stream

The last two are the **Dynamic Consistency Boundary**, and they are additive: a stream and its
`expected_version` remain the default boundary, and every slice generated so far uses nothing
else. `docs/adr/0001-a-dcb-capable-log.md` in the factory that made this project records why the
log carries both. A tag is the more general of the two — stream-per-aggregate is the case where
every event carries exactly one tag, `stream:<stream_id>`, which is what `default_tags_of` below
actually returns.

Nothing here names Postgres, SQL, or a vendor. Every adapter under `adapters/driven/`
implements it, and the same contract suite runs against all of them.

The port is **synchronous**, deliberately. `sqlite3` and `psycopg` are synchronous drivers,
and an async port over a sync driver either blocks the event loop or hides a thread pool
behind a coroutine that looks like it does not. A driving adapter that needs concurrency owns
that decision at its own edge, where it can be seen.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Literal, NewType, Protocol

#: `expected_version` for a stream that must not exist yet, which is how first-write races
#: are detected.
NO_STREAM = -1

#: Correlation and causation are **UUIDs**, and typed as such rather than as free strings. They
#: are written by one service and read by another, often years later by a tool nobody has
#: written yet, so the one thing they must be is unambiguous: a UUID is unique without a
#: registry, parses the same everywhere, and cannot quietly become a request path, a customer
#: reference, or an empty string that nothing rejects.
#:
#: They are two types rather than one alias used twice, because they sit side by side in every
#: constructor below and carry the same shape. Swapping them is invisible at runtime and
#: destroys the one thing they exist for — a causal tree in which everything appears to have
#: caused itself. `NewType` erases to `uuid.UUID`, so the distinction costs nothing at runtime
#: and the type checker is what enforces it.
CorrelationId = NewType("CorrelationId", uuid.UUID)
CausationId = NewType("CausationId", uuid.UUID)


def _as_uuid(raw: str | uuid.UUID, what: str) -> uuid.UUID:
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(raw)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"a {what} must be a UUID, and {raw!r} is not") from error


def create_correlation_id(raw: str | uuid.UUID) -> CorrelationId:
    """Parse an incoming correlation id, or `uuid.uuid4()` to start a new business transaction.

    Parsing at the edge is what keeps the type honest: a value that reached here as text from a
    header, a queue message, or a stored row is checked once, here, rather than trusted
    everywhere.
    """
    return CorrelationId(_as_uuid(raw, "correlation id"))


def create_causation_id(raw: str | uuid.UUID) -> CausationId:
    """Parse the id of the message that directly caused an event.

    The rule, from Greg Young: responding to a message, you copy its correlation id as your
    own and take its id as your causation id.
    """
    return CausationId(_as_uuid(raw, "causation id"))


@dataclass(frozen=True, slots=True)
class Actor:
    """Who or what caused the event.

    Recorded on every event so the log answers "who did this".
    """

    kind: str
    id: str


@dataclass(frozen=True, slots=True)
class DomainEvent:
    type: str
    schema_version: Literal[1]
    stream_id: str
    payload: Mapping[str, object]
    #: Domain time, as an ISO-8601 instant. Taken from a clock at the edge and passed in as a
    #: typed input — the domain never reads the clock, which is what makes a decision function
    #: testable without freezing global time. Distinct from `recorded_at` below, and
    #: conflating the two is how clock problems become unreconcilable.
    occurred_at: str
    actor: Actor
    #: The whole business transaction this event belongs to.
    correlation_id: CorrelationId
    #: The message that directly caused this event, and `None` when nothing did — the first
    #: event of a transaction has no cause to point at, and inventing one would be a lie about
    #: the shape of the tree.
    causation_id: CausationId | None = None


@dataclass(frozen=True, slots=True)
class CommittedEvent:
    """What the store gives back: the event plus the facts only the store can know."""

    type: str
    schema_version: Literal[1]
    stream_id: str
    payload: Mapping[str, object]
    occurred_at: str
    actor: Actor
    correlation_id: CorrelationId
    version: int
    global_position: int
    recorded_at: str
    causation_id: CausationId | None = field(default=None)


@dataclass(frozen=True, slots=True)
class Appended:
    version: int


@dataclass(frozen=True, slots=True)
class VersionConflict:
    actual_version: int


#: A version conflict is a **return value, not a raised exception**. Contention is expected
#: under load, not exceptional: the caller re-reads and re-decides. Raising would push
#: ordinary concurrency into an error path and invite an `except` that swallows it.
AppendResult = Appended | VersionConflict


# ── The other consistency boundary ────────────────────────────────────────────────────────────
#
# Everything below is the Dynamic Consistency Boundary. Read it only when a decision cannot be
# guarded by one stream's version — a constraint spanning two entities, where either can change
# under you. Until then `append` above is the whole port.


def stream_tag(stream_id: str) -> str:
    """The tag every event carries by default: its own stream, as a tag.

    Written this way rather than inlined because it is the one place the correspondence between
    the two boundaries is spelled: a stream id *is* a tag, so a log that indexes tags indexes
    the streams it already had.
    """
    return f"stream:{stream_id}"


def default_tags_of(event: DomainEvent) -> tuple[str, ...]:
    """What an event is indexed by, unless this project says otherwise.

    Tags are **derived, never modelled**: nothing in `docs/event-model/model.yaml` names one,
    because a tag is a technical index over the log and not a fact about the business. This
    function is where a project decides what its events are findable by — usually the
    identifying attributes of the payload, alongside the stream:

        def tags_of(event: DomainEvent) -> tuple[str, ...]:
            tags = [stream_tag(event.stream_id)]
            if (course := event.payload.get("courseId")) is not None:
                tags.append(f"course:{course}")
            return tuple(tags)

    Pass it to the adapter's factory. Changing it later is safe and cheap — the index is derived,
    so `retag` rebuilds it from the log — which is the whole reason tags live in an index of
    their own rather than on the event row.
    """
    return (stream_tag(event.stream_id),)


#: How an adapter learns what to index an event by. A plain function, so a project's tagging rule
#: is testable without a database.
TagsOf = Callable[[DomainEvent], tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class TagFilter:
    """One conjunction: an event matches when it carries **every** tag named here and, where
    `types` names any, when its type is one of them.

    A filter with no tags and no types matches nothing. That is deliberate — see `TagQuery`.
    """

    tags: tuple[str, ...] = ()
    types: tuple[str, ...] = ()

    def matches(self, event: CommittedEvent, tags: Sequence[str]) -> bool:
        """Whether one event matches, given the tags it was indexed by.

        In the port rather than in each adapter because it is the definition, and an adapter
        that computed it differently in SQL would be a second definition nothing compares. The
        in-memory adapter uses this directly; the SQL adapters translate it, and the contract
        suite is what holds the translation to it.
        """
        if not self.tags and not self.types:
            return False
        if self.types and event.type not in self.types:
            return False
        return all(tag in tags for tag in self.tags)


@dataclass(frozen=True, slots=True)
class TagQuery:
    """Which events a decision loads, and — as part of a `Condition` — which events invalidate it.

    A disjunction of filters, because the constraint that motivates any of this spans entities:
    deciding whether a student may subscribe to a course needs the course's events *and* that
    student's events, which is two filters and cannot be one. Think of it as the SQL query that
    fetches exactly the events needed to decide.

    **An empty query matches nothing**, never everything. A condition that matched everything
    would refuse every concurrent append in the system, and a read that matched everything would
    quietly become a full replay; both are failures worth being loud about, and neither is what
    anybody meant to write.
    """

    filters: tuple[TagFilter, ...] = ()

    def matches(self, event: CommittedEvent, tags: Sequence[str]) -> bool:
        return any(one.matches(event, tags) for one in self.filters)

    @property
    def tags(self) -> tuple[str, ...]:
        """Every tag the query mentions, deduplicated — what an index lookup can narrow on
        before the filters are applied exactly."""
        seen: dict[str, None] = {}
        for one in self.filters:
            for tag in one.tags:
                seen[tag] = None
        return tuple(seen)


@dataclass(frozen=True, slots=True)
class TaggedRead:
    """What a decision was made from, and the position it was made at.

    `head` is the store's last global position at the moment of the read — zero for an empty
    log. It is not a nicety: it is the anchor a `Condition` is built from, so "these are the
    facts I decided on" and "nothing else has happened since" are one round trip rather than two
    that can disagree.

    It is also read-your-writes made concrete. A caller that appends and then needs a
    subscription-maintained view to have caught up can wait for a *specific* position instead of
    polling blindly.
    """

    events: tuple[CommittedEvent, ...]
    head: int


@dataclass(frozen=True, slots=True)
class Condition:
    """The guard on a conditional append: `query` must have matched nothing after `after`.

    `after` is the `head` of the `TaggedRead` the decision was made from. The pair is the
    boundary — dynamic because the caller draws it per decision, out of tags, rather than
    inheriting it from how streams were laid out months earlier.
    """

    query: TagQuery
    after: int


@dataclass(frozen=True, slots=True)
class Recorded:
    """A conditional append that held: `head` is the position of its last event."""

    head: int


@dataclass(frozen=True, slots=True)
class ConditionConflict:
    """The condition no longer holds: something matching it was recorded after `after`.

    `head` is the store head as found, so a caller that retries reads from there. A conflict is
    a **value** here for the same reason `VersionConflict` is one, and this is where the two
    boundaries agree: contention is ordinary, and a caller re-reads and re-decides.
    """

    head: int


ConditionalAppendResult = Recorded | ConditionConflict


class EventStore(Protocol):
    def read(self, stream_id: str) -> tuple[CommittedEvent, ...]: ...

    def append(
        self,
        stream_id: str,
        expected_version: int,
        events: Sequence[DomainEvent],
    ) -> AppendResult: ...

    def read_all(self, from_position: int) -> Iterator[CommittedEvent]:
        """Replay across all streams from a global position.

        This exists so read models can be rebuilt from zero — without it they are not
        disposable, and a projection bug becomes unfixable.
        """
        ...

    def unit_of_work(self) -> AbstractContextManager[None]:
        """One transaction, which an append and somebody else's write share.

        Inside it, `append` and `append_if` do **not** commit: leaving the block commits
        everything once, and an exception rolls all of it back. Outside it they commit
        themselves, exactly as they always have, so nothing already written needs to know this
        exists.

        Two things need it, and they are the same need. A read model materialised **inline** is
        written here, so a query can never see an event whose view row is missing — and a failed
        view write takes the append down with it. A projection maintained **asynchronously**
        records its checkpoint here, in the same transaction as the rows it derived, which is
        what makes it exactly-once rather than approximately-once. A checkpoint committed
        separately from the view it describes is not a checkpoint; it is a race with a number in
        it.

        Nesting is allowed and re-entrant: the outermost block owns the commit. Any other
        adapter built from the same connection is inside it, which is why the read-side adapters
        are constructed from this one.
        """
        ...

    def head(self) -> int:
        """The last global position in the log, or zero when it is empty.

        The boundary a decision is made against, taken **once** and then handed to every read
        that decision needs. A command that reads twice and uses the second read's head has
        promised something it never checked: an event matching the first query could have arrived
        between the two reads, before that head, and the conditional append would not look for it.
        Pin it here, pass it as `until`, and that mistake has nowhere to happen:

            boundary = store.head()
            course = store.read_tagged(by_course, until=boundary)
            student = store.read_tagged(by_student, until=boundary)
            store.append_if(Condition(by_course | by_student, boundary), [event])
        """
        ...

    def read_tagged(self, query: TagQuery, after: int = 0, until: int = 0) -> TaggedRead:
        """The events matching `query` in `(after, until]`, and the position they are as of.

        This is the DCB read: what a decision loads. `after` is for resuming a long read, not for
        the guard. `until` is the ceiling — zero for none, which is every position, since the log
        starts at one — and it is what a decision reading twice pins first, so both reads see the
        same log. The `head` handed back is what the facts are as of: `until` when it is given,
        the store's head when it is not, and either way it is what a `Condition` is built from.
        """
        ...

    def append_if(
        self,
        condition: Condition,
        events: Sequence[DomainEvent],
    ) -> ConditionalAppendResult:
        """Append only if nothing matching `condition.query` was recorded after
        `condition.after`.

        The events still name their streams and still land at gapless per-stream versions — the
        store assigns each one the next version of the stream it names — so `read`, `folds` and
        every slice written against `append` keep working unchanged. What differs is only what
        the write is guarded by.
        """
        ...

    def reindex_tags(self, from_position: int = 0) -> int:
        """Index events this store's tagging function has not indexed yet; returns how many.

        The verb an already-running project needs: applying the migration creates an empty
        index, and this is what fills it from the history that is already there. Idempotent, so
        running it twice indexes nothing the second time and a run that died halfway is resumed
        by running it again.
        """
        ...

    def retag(self, tags_of: TagsOf) -> int:
        """Adopt a new tagging function and rebuild the whole index under it; returns how many
        events were indexed.

        Because the index is derived, what a project tags is a decision it can change — unlike
        the events themselves. Both halves happen together on purpose: an index rebuilt under
        one function while appends carry on under another is an index that disagrees with itself.
        """
        ...


def current_version(events: Sequence[CommittedEvent]) -> int:
    """The expected version to pass when appending to a stream you have just read."""
    return events[-1].version if events else NO_STREAM

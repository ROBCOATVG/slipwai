"""One contract, run against every event-store adapter.

The in-memory and file-backed adapters run it in `make test`; Postgres runs it in
`make test-integration`.
Two adapters that pass different tests are two different ports wearing one name, and the day they
diverge is the day a slice that worked on the fake stops working in production.

A mixin rather than a fixture, because pytest collects `Test*` classes: each adapter's module
subclasses this and supplies `make_store`, and the whole suite runs again against it. The name
deliberately does not start with `Test`, so this file contributes no tests of its own.

Nothing here truncates or deletes: the log is append-only, and a real store enforces that with a
trigger, so a shared table cannot be cleaned between tests. Every test therefore works in freshly
named streams and asserts only about those. That is not a workaround — it is what testing against a
real append-only log actually looks like.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping

import pytest

from delivery_starter.application.ports.events import (
    NO_STREAM,
    Actor,
    Appended,
    CausationId,
    CommittedEvent,
    Condition,
    ConditionConflict,
    DomainEvent,
    EventStore,
    Recorded,
    TagFilter,
    TagQuery,
    TagsOf,
    VersionConflict,
    create_causation_id,
    create_correlation_id,
    current_version,
    default_tags_of,
    stream_tag,
)


def payload_tags(event: DomainEvent) -> tuple[str, ...]:
    """A tagging function of the shape a real project writes: the stream, plus the identifying
    attributes of the payload.

    Tags are derived from the event and nothing else, which is what makes the index rebuildable —
    so this function is called on the way in *and* during a reindex, and the contract below
    proves the two agree.
    """
    tags = [stream_tag(event.stream_id)]
    for attribute, kind in (("courseId", "course"), ("studentId", "student")):
        if (value := event.payload.get(attribute)) is not None:
            tags.append(f"{kind}:{value}")
    return tuple(tags)


def no_tags(event: DomainEvent) -> tuple[str, ...]:
    """What a project that has not adopted tags has: a log with no index over it.

    Every event already in a running project's log was written by a store that behaved exactly
    like this, which is why it is worth a fixture rather than a comment.
    """
    return ()


class EventStoreContract:
    """Subclass this and implement `make_store` to hold an adapter to the port's contract."""

    def make_store(
        self,
        tags_of: TagsOf = default_tags_of,
    ) -> EventStore:  # pragma: no cover - overridden by every subclass
        raise NotImplementedError

    @pytest.fixture
    def store(self) -> Iterator[EventStore]:
        yield self.make_store()

    @pytest.fixture
    def tagged_store(self) -> Iterator[EventStore]:
        """A store whose events are findable by their payload's ids as well as their stream —
        which is the only reason a Dynamic Consistency Boundary can be drawn at all."""
        yield self.make_store(payload_tags)

    @pytest.fixture
    def run_id(self) -> str:
        return str(uuid.uuid4())

    @pytest.fixture
    def new_stream(self, run_id: str) -> Iterator[object]:
        counter = {"value": 0}

        def make() -> str:
            counter["value"] += 1
            return f"contract-{run_id}-{counter['value']}"

        yield make

    @staticmethod
    def event(
        stream_id: str,
        event_type: str,
        run_id: str,
        payload: Mapping[str, object] | None = None,
        causation_id: CausationId | None = None,
    ) -> DomainEvent:
        return DomainEvent(
            type=event_type,
            schema_version=1,
            stream_id=stream_id,
            payload=dict(payload or {}),
            occurred_at="2024-01-01T00:00:00+00:00",
            actor=Actor(kind="test", id=run_id),
            correlation_id=create_correlation_id(run_id),
            causation_id=causation_id,
        )

    def test_reads_an_unknown_stream_as_empty_rather_than_failing(self, store, new_stream) -> None:
        assert store.read(new_stream()) == ()

    def test_appends_to_a_stream_that_does_not_exist_yet(self, store, new_stream, run_id) -> None:
        stream = new_stream()

        result = store.append(
            stream,
            NO_STREAM,
            [self.event(stream, "Started", run_id), self.event(stream, "Continued", run_id)],
        )

        assert result == Appended(1)

    def test_returns_the_stream_in_version_order_with_what_only_the_store_knows(
        self, store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id, {"step": 1})])
        store.append(stream, 0, [self.event(stream, "Continued", run_id, {"step": 2})])

        events = store.read(stream)

        versions = [(event.type, event.version) for event in events]

        assert versions == [("Started", 0), ("Continued", 1)]
        assert [event.payload for event in events] == [{"step": 1}, {"step": 2}]
        first, second = events
        assert second.global_position > first.global_position
        assert first.occurred_at.startswith("2024-01-01T00:00:00")
        assert first.actor == Actor(kind="test", id=run_id)
        assert first.recorded_at

    def test_round_trips_the_correlation_and_causation_ids_as_uuids(
        self, store, new_stream, run_id
    ) -> None:
        """Every adapter stores these ids the way its database can and hands back the same UUIDs.

        Postgres has a `uuid` column, SQLite has text, the in-memory store has neither. The
        difference stops at the adapter, and it is provable here rather than by reading three
        implementations: what goes in comes back out, as `CorrelationId` and `CausationId`.
        """
        stream = new_stream()
        cause = create_causation_id(uuid.uuid4())
        store.append(
            stream,
            NO_STREAM,
            [
                self.event(stream, "Started", run_id),
                self.event(stream, "Caused", run_id, causation_id=cause),
            ],
        )

        first, second = store.read(stream)

        assert first.correlation_id == create_correlation_id(run_id)
        # The first event of a transaction has no cause, and the store does not invent one.
        assert first.causation_id is None
        assert second.causation_id == cause

    def test_reports_a_stale_expected_version_as_a_value_not_an_exception(
        self, store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        raced = store.append(stream, NO_STREAM, [self.event(stream, "Raced", run_id)])

        assert raced == VersionConflict(0)

    def test_writes_nothing_when_the_expected_version_is_stale(
        self, store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        store.append(
            stream,
            NO_STREAM,
            [self.event(stream, "Rejected", run_id), self.event(stream, "AlsoRejected", run_id)],
        )

        assert [event.type for event in store.read(stream)] == ["Started"]

    def test_continues_a_stream_from_the_version_it_reports(
        self, store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])
        history = store.read(stream)

        assert current_version(history) == 0
        assert store.append(
            stream, current_version(history), [self.event(stream, "Continued", run_id)]
        ) == Appended(1)

    def test_treats_an_empty_append_as_a_no_op_at_the_expected_version(
        self, store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        assert store.append(stream, 0, []) == Appended(0)
        assert len(store.read(stream)) == 1

    def test_keeps_streams_apart(self, store, new_stream, run_id) -> None:
        one, other = new_stream(), new_stream()
        store.append(one, NO_STREAM, [self.event(one, "Mine", run_id)])
        store.append(other, NO_STREAM, [self.event(other, "Theirs", run_id)])

        assert [event.type for event in store.read(one)] == ["Mine"]
        assert [event.type for event in store.read(other)] == ["Theirs"]

    def test_replays_across_all_streams_in_global_position_order(
        self, store, new_stream, run_id
    ) -> None:
        one, other = new_stream(), new_stream()
        store.append(one, NO_STREAM, [self.event(one, "First", run_id)])
        store.append(other, NO_STREAM, [self.event(other, "Second", run_id)])
        store.append(one, 0, [self.event(one, "Third", run_id)])

        replayed: list[CommittedEvent] = [
            event for event in store.read_all(0) if event.stream_id in {one, other}
        ]

        assert [event.type for event in replayed] == ["First", "Second", "Third"]
        positions = [event.global_position for event in replayed]
        assert positions == sorted(positions)

    def test_replays_only_from_the_requested_position_onward(
        self, store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        store.append(
            stream,
            NO_STREAM,
            [self.event(stream, "First", run_id), self.event(stream, "Second", run_id)],
        )
        _, second = store.read(stream)

        replayed = [
            event for event in store.read_all(second.global_position) if event.stream_id == stream
        ]

        assert [event.type for event in replayed] == ["Second"]

    # ── The tag index, and the boundary drawn out of it ───────────────────────────────────────
    #
    # Everything below is the Dynamic Consistency Boundary, and it runs against all three
    # adapters for the same reason the rest of this file does: an in-memory fake that answers a
    # tag query differently from Postgres is a fake that proves nothing about production. The
    # SQL adapters translate `TagQuery.matches` into SQL, and these are the cases that hold the
    # translation to the definition.

    def test_indexes_every_event_by_its_own_stream_without_being_asked(
        self, store, new_stream, run_id
    ) -> None:
        """The default tagging function is `stream:<stream_id>`, so a log that indexes tags
        indexes the streams it already had. This is the sentence "stream-per-aggregate is the
        case where every event carries exactly one tag", as a test."""
        stream = new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        found = store.read_tagged(TagQuery((TagFilter(tags=(stream_tag(stream),)),)))

        assert [event.type for event in found.events] == ["Started"]

    def test_reports_the_store_head_with_what_it_read(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """The head is the anchor a condition is built from, so it comes back with the events
        rather than from a second call that could disagree with the first."""
        stream = new_stream()
        empty = tagged_store.read_tagged(TagQuery((TagFilter(tags=(stream_tag(stream),)),)))
        tagged_store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        after = tagged_store.read_tagged(TagQuery((TagFilter(tags=(stream_tag(stream),)),)))

        assert after.head > empty.head
        assert after.events[-1].global_position == after.head

    def test_matches_an_event_only_when_it_carries_every_tag_in_a_filter(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """A filter is a conjunction. An "any of these tags" filter would be a much weaker guard
        than the caller wrote, and the difference is invisible until it lets a write through."""
        stream = new_stream()
        course, student = f"course:{run_id}", f"student:{run_id}"
        tagged_store.append(
            stream,
            NO_STREAM,
            [self.event(stream, "Subscribed", run_id, {"courseId": run_id, "studentId": run_id})],
        )

        both = tagged_store.read_tagged(TagQuery((TagFilter(tags=(course, student)),)))
        one_wrong = tagged_store.read_tagged(
            TagQuery((TagFilter(tags=(course, f"student:{run_id}-nobody")),))
        )

        assert [event.type for event in both.events] == ["Subscribed"]
        assert one_wrong.events == ()

    def test_matches_any_filter_in_the_query(self, tagged_store, new_stream, run_id) -> None:
        """The query is a disjunction of conjunctions, because the constraint that motivates any
        of this spans entities: a course's events *and* a student's events, which is two filters
        and cannot be one."""
        course_stream, student_stream = new_stream(), new_stream()
        tagged_store.append(
            course_stream,
            NO_STREAM,
            [self.event(course_stream, "CourseCapacitySet", run_id, {"courseId": run_id})],
        )
        tagged_store.append(
            student_stream,
            NO_STREAM,
            [self.event(student_stream, "StudentSubscribed", run_id, {"studentId": run_id})],
        )

        found = tagged_store.read_tagged(
            TagQuery(
                (
                    TagFilter(tags=(f"course:{run_id}",)),
                    TagFilter(tags=(f"student:{run_id}",)),
                )
            )
        )

        assert [event.type for event in found.events] == [
            "CourseCapacitySet",
            "StudentSubscribed",
        ]
        positions = [event.global_position for event in found.events]
        assert positions == sorted(positions)

    def test_narrows_a_filter_by_event_type(self, tagged_store, new_stream, run_id) -> None:
        stream = new_stream()
        tagged_store.append(
            stream,
            NO_STREAM,
            [
                self.event(stream, "Subscribed", run_id, {"courseId": run_id}),
                self.event(stream, "Unsubscribed", run_id, {"courseId": run_id}),
            ],
        )

        found = tagged_store.read_tagged(
            TagQuery((TagFilter(tags=(f"course:{run_id}",), types=("Unsubscribed",)),))
        )

        assert [event.type for event in found.events] == ["Unsubscribed"]

    def test_an_empty_query_matches_nothing_rather_than_everything(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """The dangerous default, refused explicitly. A condition that matched everything would
        refuse every concurrent append in the system, and a read that matched everything would
        quietly become a full replay."""
        stream = new_stream()
        tagged_store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        assert tagged_store.read_tagged(TagQuery()).events == ()
        assert tagged_store.read_tagged(TagQuery((TagFilter(),))).events == ()

    def test_appends_conditionally_when_nothing_matching_arrived_since_the_read(
        self, tagged_store, new_stream, run_id
    ) -> None:
        stream = new_stream()
        query = TagQuery((TagFilter(tags=(f"course:{run_id}",)),))
        decided_at = tagged_store.read_tagged(query).head

        result = tagged_store.append_if(
            Condition(query, decided_at),
            [self.event(stream, "Subscribed", run_id, {"courseId": run_id})],
        )

        assert isinstance(result, Recorded)
        assert [event.type for event in tagged_store.read(stream)] == ["Subscribed"]

    def test_refuses_a_conditional_append_when_a_matching_event_arrived_since(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """The guard `expected_version` cannot express: the constraint spans two entities, and
        what invalidates the decision is an event in a stream the decision never named."""
        stream, other = new_stream(), new_stream()
        query = TagQuery((TagFilter(tags=(f"course:{run_id}",)),))
        decided_at = tagged_store.read_tagged(query).head
        tagged_store.append(
            other, NO_STREAM, [self.event(other, "Subscribed", run_id, {"courseId": run_id})]
        )

        result = tagged_store.append_if(
            Condition(query, decided_at),
            [self.event(stream, "Subscribed", run_id, {"courseId": run_id})],
        )

        assert isinstance(result, ConditionConflict)
        assert result.head >= decided_at
        assert tagged_store.read(stream) == ()

    def test_a_conditionally_appended_event_is_readable_as_part_of_its_stream(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """The compatibility that makes this additive rather than a fork. A conditional append
        still lands at the next version of the stream it names, so every slice written against
        `read`, `append` and `folds` goes on working unchanged."""
        stream = new_stream()
        query = TagQuery((TagFilter(tags=(f"course:{run_id}",)),))
        tagged_store.append(
            stream, NO_STREAM, [self.event(stream, "Opened", run_id, {"courseId": run_id})]
        )
        tagged_store.append_if(
            Condition(query, tagged_store.read_tagged(query).head),
            [self.event(stream, "Subscribed", run_id, {"courseId": run_id})],
        )

        events = tagged_store.read(stream)

        assert [(event.type, event.version) for event in events] == [
            ("Opened", 0),
            ("Subscribed", 1),
        ]
        assert tagged_store.append(stream, current_version(events), []) == Appended(1)

    def test_a_store_that_indexes_nothing_behaves_exactly_as_it_did_before(
        self, new_stream, run_id
    ) -> None:
        """What every project generated before tags existed is, and what it stays until it says
        otherwise: the log, unchanged, with an index over nothing."""
        store = self.make_store(no_tags)
        stream = new_stream()

        assert store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)]) == Appended(
            0
        )
        assert [event.type for event in store.read(stream)] == ["Started"]
        assert store.read_tagged(TagQuery((TagFilter(tags=(stream_tag(stream),)),))).events == ()

    def test_indexes_a_log_it_did_not_index_when_the_events_were_written(
        self, new_stream, run_id
    ) -> None:
        """The adoption path, as a test rather than as a paragraph.

        A project already in production applies the migration, which creates an empty index, and
        runs this. Nothing about the log changes — which is the only reason this is possible at
        all, since the log refuses to be rewritten.

        `retag` rebuilds the whole index rather than one stream's share of it. Against a shared
        database that is safe here because every tagging function in this suite returns the
        stream tag plus more, so a rebuild under one of them satisfies every other case's
        assumptions as well.
        """
        unindexed = self.make_store(no_tags)
        stream = new_stream()
        unindexed.append(
            stream,
            NO_STREAM,
            [
                self.event(stream, "Enrolled", run_id, {"courseId": run_id}),
                self.event(stream, "Graduated", run_id, {"courseId": run_id}),
            ],
        )
        query = TagQuery((TagFilter(tags=(f"course:{run_id}",)),))
        assert unindexed.read_tagged(query).events == ()

        indexed = unindexed.retag(payload_tags)

        assert indexed >= 2
        assert [event.type for event in unindexed.read_tagged(query).events] == [
            "Enrolled",
            "Graduated",
        ]
        # Idempotent: a second run indexes nothing, so a reindex that died halfway is finished
        # by running it again rather than started over.
        assert unindexed.reindex_tags() == 0
        assert len(unindexed.read_tagged(query).events) == 2

    def test_counts_only_the_events_a_reindex_made_findable(self, new_stream, run_id) -> None:
        """What "indexed" means, which the adapters have to agree on or the number an adoption run
        reports is a different number in every store.

        An event this project's tagging function returns nothing for is never findable by tag, so a
        reindex that counted it would report work it did not do and would never settle at zero.
        Both halves matter: the in-memory store must not record an empty index entry, which would
        make the event look indexed to a later run under a real tagging function, and the SQL
        stores must not count a row they wrote no tags for.
        """
        store = self.make_store(no_tags)
        stream = new_stream()
        store.append(
            stream,
            NO_STREAM,
            [
                self.event(stream, "Enrolled", run_id, {"courseId": run_id}),
                self.event(stream, "Graduated", run_id, {"courseId": run_id}),
            ],
        )

        assert store.reindex_tags() == 0

    def test_reads_as_of_a_boundary_and_nothing_after_it(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """The reason `head` is a method of its own, and what stops a decision from being made
        against two different moments.

        A command that needs two queries — a course's capacity and a student's own
        subscriptions — reads twice. If each read hands back its own head and the caller guards
        with the second one, an event matching the *first* query could have arrived between the
        two reads, before that head, and the conditional append would never look for it: the
        guard says "nothing since here" about a position the facts do not cover.

        Pinning the boundary first and passing it as `until` removes the gap. Both reads see the
        same log, the head handed back is the boundary rather than whatever has happened since,
        and a `Condition` built from it covers exactly the facts it was decided on.
        """
        stream = new_stream()
        query = TagQuery((TagFilter(tags=(f"course:{run_id}",)),))
        tagged_store.append(
            stream, NO_STREAM, [self.event(stream, "Enrolled", run_id, {"courseId": run_id})]
        )

        boundary = tagged_store.head()
        # Somebody else's event, after the boundary this decision was drawn at.
        tagged_store.append(
            stream, 0, [self.event(stream, "Graduated", run_id, {"courseId": run_id})]
        )

        as_of = tagged_store.read_tagged(query, until=boundary)
        assert [event.type for event in as_of.events] == ["Enrolled"]
        assert as_of.head == boundary

        # Unbounded, the same query sees both — the ceiling is the caller's decision, not a filter
        # the store applies on its own.
        current = tagged_store.read_tagged(query)
        assert [event.type for event in current.events] == ["Enrolled", "Graduated"]
        assert current.head >= boundary

    def test_an_append_and_its_tags_arrive_together_or_not_at_all(
        self, tagged_store, new_stream, run_id
    ) -> None:
        """The one failure that would make the index worse than not having it: an event visible
        to `read` whose tags are not yet visible to `read_tagged` would let the next conditional
        append miss the very event that should have refused it."""
        stream = new_stream()
        query = TagQuery((TagFilter(tags=(f"course:{run_id}",)),))

        tagged_store.append(
            stream, NO_STREAM, [self.event(stream, "Subscribed", run_id, {"courseId": run_id})]
        )

        assert len(tagged_store.read(stream)) == len(tagged_store.read_tagged(query).events) == 1

    def test_a_unit_of_work_that_fails_leaves_the_log_as_it_was(
        self, store, new_stream, run_id
    ) -> None:
        """What an `inline` read model and an `async` checkpoint are both built on: a write of
        somebody else's that fails takes the append with it."""
        stream = new_stream()

        with (
            pytest.raises(RuntimeError, match="the view write failed"),
            store.unit_of_work(),
        ):
            store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])
            raise RuntimeError("the view write failed")

        assert store.read(stream) == ()

    def test_a_unit_of_work_that_completes_commits_everything_in_it_once(
        self, store, new_stream, run_id
    ) -> None:
        one, other = new_stream(), new_stream()

        with store.unit_of_work():
            store.append(one, NO_STREAM, [self.event(one, "Mine", run_id)])
            store.append(other, NO_STREAM, [self.event(other, "Theirs", run_id)])

        assert [event.type for event in store.read(one)] == ["Mine"]
        assert [event.type for event in store.read(other)] == ["Theirs"]

    def test_a_refused_append_inside_a_unit_of_work_writes_nothing_and_ends_nothing(
        self, store, new_stream, run_id
    ) -> None:
        """A conflict is a value, so the caller's transaction survives it and goes on to commit
        what else it was doing. Without a savepoint per nested block, a refused append would
        either poison the outer transaction or leave its own half-written events inside it.
        """
        stream, other = new_stream(), new_stream()
        store.append(stream, NO_STREAM, [self.event(stream, "Started", run_id)])

        with store.unit_of_work():
            refused = store.append(
                stream,
                NO_STREAM,
                [
                    self.event(stream, "Rejected", run_id),
                    self.event(stream, "AlsoRejected", run_id),
                ],
            )
            store.append(other, NO_STREAM, [self.event(other, "Unaffected", run_id)])

        assert refused == VersionConflict(0)
        assert [event.type for event in store.read(stream)] == ["Started"]
        assert [event.type for event in store.read(other)] == ["Unaffected"]

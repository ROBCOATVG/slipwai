"""The catch-up runner.

Against the in-memory pair, and only that pair, because the runner has no I/O of its own: it is
two ports and a loop, and what these cases are about is the loop. That is also why it is here
rather than beside an adapter — a project that chose the in-memory store still gets every one of
these.

The guarantee the runner *rests* on — that a checkpoint recorded in a failed unit of work does
not move — is proved in `checkpoint_store_contract.py`, which runs against every store adapter
this project has, where a rollback is the database's own rather than a restored copy. Split that
way deliberately: the transaction is the adapters' promise, and the loop is what this file holds
to it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta

import pytest

from delivery_starter import projections
from delivery_starter.adapters.driven.checkpoint_store_memory import (
    create_in_memory_checkpoint_store,
)
from delivery_starter.adapters.driven.event_store_memory import (
    create_in_memory_event_store,
)
from delivery_starter.application.ports.events import (
    NO_STREAM,
    Actor,
    CommittedEvent,
    DomainEvent,
    EventStore,
    create_correlation_id,
)
from delivery_starter.application.ports.read_models import (
    FROM_THE_BEGINNING,
    CheckpointStore,
)

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def clock_at(instant: datetime) -> projections.Clock:
    return lambda: instant


class Titles:
    """A read model with somewhere to put the result, which is all a projection is.

    Its rows are **derived**: every one of them comes from an event, so `reset` plus a replay
    reproduces it exactly. A column this class alone knew — a flag it set when it processed a row
    — could not survive `reset`, and finding that out during an incident is how a rebuild becomes
    data loss.
    """

    name = "titles"

    def __init__(self) -> None:
        self.rows: list[str] = []
        self.batches = 0

    def apply(self, events: Sequence[CommittedEvent]) -> None:
        self.batches += 1
        self.rows.extend(f"{event.type}@{event.global_position}" for event in events)

    def reset(self) -> None:
        self.rows.clear()


class Broken(Titles):
    """A projection whose write fails after it has changed something."""

    name = "broken"

    def apply(self, events: Sequence[CommittedEvent]) -> None:
        super().apply(events)
        raise RuntimeError("the view write failed")


@pytest.fixture
def pair() -> Iterator[tuple[EventStore, CheckpointStore]]:
    """The store and the checkpoint store on one "connection", which is what the runner assumes
    and what every adapter pair provides."""
    store = create_in_memory_event_store()
    yield store, create_in_memory_checkpoint_store(store)


def event(stream_id: str, event_type: str) -> DomainEvent:
    return DomainEvent(
        type=event_type,
        schema_version=1,
        stream_id=stream_id,
        payload={},
        occurred_at="2024-01-01T00:00:00+00:00",
        actor=Actor(kind="test", id="projections"),
        correlation_id=create_correlation_id(uuid.uuid4()),
    )


def given_a_log_of(store: EventStore, *types: str) -> str:
    stream = f"projection-{uuid.uuid4()}"
    store.append(stream, NO_STREAM, [event(stream, one) for one in types])
    return stream


def test_applies_the_whole_log_and_leaves_the_checkpoint_past_it(pair) -> None:
    store, checkpoints = pair
    given_a_log_of(store, "Placed", "Paid")
    view = Titles()

    done = projections.catch_up(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))

    assert done == projections.Advance(applied=2, leased=True)
    assert [row.split("@")[0] for row in view.rows] == ["Placed", "Paid"]
    assert checkpoints.position_of("titles") == 3


def test_resumes_from_the_checkpoint_and_applies_nothing_twice(pair) -> None:
    store, checkpoints = pair
    given_a_log_of(store, "Placed")
    view = Titles()
    projections.catch_up(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))

    given_a_log_of(store, "Paid")
    again = projections.catch_up(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))

    assert again.applied == 1
    assert [row.split("@")[0] for row in view.rows] == ["Placed", "Paid"]


def test_a_pass_with_nothing_to_do_says_so_without_touching_the_view(pair) -> None:
    store, checkpoints = pair
    view = Titles()

    done = projections.catch_up(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))

    assert done == projections.Advance(applied=0, leased=True)
    assert view.rows == []
    assert view.batches == 0


def test_applies_a_long_log_in_batches_of_the_size_it_was_given(pair) -> None:
    """Each batch is one transaction, so the size trades how much a crash repeats against how
    long one transaction holds its locks. That it batches at all is what keeps a rebuild over a
    long log from materialising the whole thing."""
    store, checkpoints = pair
    given_a_log_of(store, "One", "Two", "Three", "Four", "Five")
    view = Titles()

    done = projections.catch_up(
        store, checkpoints, view, owner="worker-1", clock=clock_at(NOW), batch_size=2
    )

    assert done.applied == 5
    assert view.batches == 3
    assert len(view.rows) == 5


def test_a_second_worker_does_nothing_while_the_first_holds_the_lease(pair) -> None:
    """The ordinary case for every replica but one, and not a failure — which is why `leased`
    is reported separately from `applied`."""
    store, checkpoints = pair
    given_a_log_of(store, "Placed")
    checkpoints.claim("titles", "worker-1", NOW, timedelta(seconds=30))
    view = Titles()

    blocked = projections.catch_up(
        store, checkpoints, view, owner="worker-2", clock=clock_at(NOW + timedelta(seconds=1))
    )

    assert blocked == projections.Advance(applied=0, leased=False)
    assert view.rows == []


def test_another_worker_takes_over_once_the_lease_has_lapsed(pair) -> None:
    store, checkpoints = pair
    given_a_log_of(store, "Placed")
    checkpoints.claim("titles", "worker-1", NOW, timedelta(seconds=30))
    view = Titles()

    taken = projections.catch_up(
        store, checkpoints, view, owner="worker-2", clock=clock_at(NOW + timedelta(minutes=5))
    )

    assert taken.leased
    assert taken.applied == 1


def test_releases_the_lease_when_the_pass_is_done(pair) -> None:
    store, checkpoints = pair
    given_a_log_of(store, "Placed")

    projections.catch_up(store, checkpoints, Titles(), owner="worker-1", clock=clock_at(NOW))

    assert checkpoints.claim("titles", "worker-2", NOW, timedelta(seconds=30)) is not None


def test_a_failed_batch_moves_neither_the_view_nor_the_checkpoint(pair) -> None:
    """Exactly-once, and there is no idempotency key in it: the checkpoint moves in the same
    transaction as the rows, so a crash before the commit leaves both untouched and the next pass
    reads the same batch again."""
    store, checkpoints = pair
    given_a_log_of(store, "Placed")
    broken = Broken()

    with pytest.raises(RuntimeError, match="the view write failed"):
        projections.catch_up(store, checkpoints, broken, owner="worker-1", clock=clock_at(NOW))

    assert checkpoints.position_of("broken") == FROM_THE_BEGINNING


def test_releases_the_lease_even_when_the_pass_fails(pair) -> None:
    """Otherwise one bad batch costs a whole `ttl` before anything tries again — every time."""
    store, checkpoints = pair
    given_a_log_of(store, "Placed")

    with pytest.raises(RuntimeError):
        projections.catch_up(store, checkpoints, Broken(), owner="worker-1", clock=clock_at(NOW))

    assert checkpoints.claim("broken", "worker-2", NOW, timedelta(seconds=30)) is not None


class AlsoTitles(Titles):
    """The same fold under a second name, because two projections must not share a checkpoint."""

    name = "also-titles"


def test_catches_up_every_projection_in_one_pass(pair) -> None:
    store, checkpoints = pair
    given_a_log_of(store, "Placed", "Paid")
    view, other = Titles(), AlsoTitles()

    advances = projections.catch_up_each(
        store, checkpoints, [view, other], owner="worker-1", clock=clock_at(NOW)
    )

    assert advances == {
        "titles": projections.Advance(applied=2, leased=True),
        "also-titles": projections.Advance(applied=2, leased=True),
    }
    assert len(view.rows) == 2
    assert len(other.rows) == 2


def test_applies_the_other_projections_when_one_of_them_fails(pair) -> None:
    """One broken fold must not starve the projections after it in the list.

    The lifespan runs this on a timer, so a projection that raises every pass would otherwise stop
    every projection registered after it — permanently, and with nothing in the log to say which
    one was at fault. Every projection is attempted, and the pass then fails loudly with all of it.
    """
    store, checkpoints = pair
    given_a_log_of(store, "Placed")
    view = Titles()

    with pytest.raises(ExceptionGroup) as failed:
        projections.catch_up_each(
            store, checkpoints, [Broken(), view], owner="worker-1", clock=clock_at(NOW)
        )

    assert "1 projection(s)" in str(failed.value)
    assert len(view.rows) == 1


def test_a_rebuild_empties_the_view_and_folds_the_whole_log_into_it_again(pair) -> None:
    """What makes a read model disposable, and therefore what makes a projection bug fixable by
    changing the fold rather than by patching rows."""
    store, checkpoints = pair
    given_a_log_of(store, "Placed", "Paid")
    view = Titles()
    projections.catch_up(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))
    view.rows.append("something nothing derived")

    rebuilt = projections.rebuild(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))

    assert rebuilt == projections.Advance(applied=2, leased=True)
    assert [row.split("@")[0] for row in view.rows] == ["Placed", "Paid"]


def test_a_rebuild_that_cannot_take_the_lease_leaves_the_view_alone(pair) -> None:
    """A rebuild is destructive, so "somebody else is advancing this" has to be distinguishable
    from "there was nothing to apply". `leased` is that distinction."""
    store, checkpoints = pair
    given_a_log_of(store, "Placed")
    view = Titles()
    projections.catch_up(store, checkpoints, view, owner="worker-1", clock=clock_at(NOW))
    checkpoints.claim("titles", "worker-1", NOW, timedelta(seconds=30))

    refused = projections.rebuild(
        store, checkpoints, view, owner="worker-2", clock=clock_at(NOW + timedelta(seconds=1))
    )

    assert refused == projections.Advance(applied=0, leased=False)
    assert len(view.rows) == 1

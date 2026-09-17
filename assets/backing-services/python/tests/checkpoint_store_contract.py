"""One contract, run against every checkpoint adapter.

The in-memory and file-backed adapters run it in `make test`; Postgres runs it in
`make test-integration`. Two adapters that pass different tests are two different ports wearing
one name, and with a checkpoint the day they diverge is the day a projection silently applies an
event twice.

A mixin rather than a fixture, for the same reason as the event store's contract: each adapter's
module subclasses this and supplies `make_stores`, and the whole suite runs again against it.

Every case works in a freshly named projection, because the table is shared with everything else
in the database and a `DELETE` between tests would only prove that deletes work.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from delivery_starter.application.ports.events import (
    NO_STREAM,
    Actor,
    DomainEvent,
    create_correlation_id,
)
from delivery_starter.application.ports.read_models import (
    FROM_THE_BEGINNING,
    CheckpointStore,
    Lease,
)

#: A fixed instant, so expiry is tested by choosing the time rather than by sleeping through it.
NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

A_WHILE = timedelta(seconds=30)


class CheckpointStoreContract:
    """Subclass this and implement `make_stores`.

    It returns the pair, not the checkpoint store alone: every adapter is built from the event
    store it follows, because `record` has to land in the same transaction as the view write it
    accounts for. A contract that let an adapter be constructed on its own would be a contract
    that permitted the one mistake this port exists to prevent.
    """

    def make_stores(self) -> tuple[object, CheckpointStore]:  # pragma: no cover - overridden
        raise NotImplementedError

    @pytest.fixture
    def stores(self) -> Iterator[tuple[object, CheckpointStore]]:
        yield self.make_stores()

    @pytest.fixture
    def checkpoints(self, stores) -> CheckpointStore:
        return stores[1]

    @pytest.fixture
    def projection(self) -> str:
        return f"contract-{uuid.uuid4()}"

    @staticmethod
    def event(stream_id: str, event_type: str) -> DomainEvent:
        return DomainEvent(
            type=event_type,
            schema_version=1,
            stream_id=stream_id,
            payload={},
            occurred_at="2024-01-01T00:00:00+00:00",
            actor=Actor(kind="test", id="checkpoints"),
            correlation_id=create_correlation_id(uuid.uuid4()),
        )

    def test_a_projection_nothing_has_recorded_starts_at_the_beginning(
        self, checkpoints, projection
    ) -> None:
        """An unknown projection has consumed nothing, which is not an error — a rebuild has to
        be expressible without a special case."""
        assert checkpoints.position_of(projection) == FROM_THE_BEGINNING

    def test_records_a_position_and_reads_it_back(self, checkpoints, projection) -> None:
        checkpoints.record(projection, 42)

        assert checkpoints.position_of(projection) == 42

    def test_records_the_same_projection_twice_without_a_second_row(
        self, checkpoints, projection
    ) -> None:
        checkpoints.record(projection, 7)
        checkpoints.record(projection, 9)

        assert checkpoints.position_of(projection) == 9

    def test_puts_a_position_back_to_the_beginning_for_a_rebuild(
        self, checkpoints, projection
    ) -> None:
        checkpoints.record(projection, 99)

        checkpoints.record(projection, FROM_THE_BEGINNING)

        assert checkpoints.position_of(projection) == FROM_THE_BEGINNING

    def test_a_position_recorded_in_a_unit_of_work_that_fails_is_not_recorded(
        self, stores, projection
    ) -> None:
        """The whole reason this port exists, and the reason its adapters are built from the
        event store: the checkpoint moves in the same transaction as the rows it accounts for, so
        a crash before the commit leaves both untouched and the next pass reads the same batch
        again. That is exactly-once, and there is no idempotency key in it.
        """
        store, checkpoints = stores
        stream = f"checkpoint-{uuid.uuid4()}"

        with (
            pytest.raises(RuntimeError, match="the view write failed"),
            store.unit_of_work(),
        ):
            store.append(stream, NO_STREAM, [self.event(stream, "Started")])
            checkpoints.record(projection, 5)
            raise RuntimeError("the view write failed")

        assert checkpoints.position_of(projection) == FROM_THE_BEGINNING
        assert store.read(stream) == ()

    def test_claims_a_projection_for_one_owner(self, checkpoints, projection) -> None:
        lease = checkpoints.claim(projection, "worker-1", NOW, A_WHILE)

        assert lease == Lease(projection=projection, owner="worker-1", expires_at=NOW + A_WHILE)

    def test_refuses_a_claim_while_somebody_else_holds_an_unexpired_lease(
        self, checkpoints, projection
    ) -> None:
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE)

        later = NOW + timedelta(seconds=1)

        assert checkpoints.claim(projection, "worker-2", later, A_WHILE) is None

    def test_lets_the_owner_renew_its_own_lease(self, checkpoints, projection) -> None:
        """How a pass long enough to outlive its lease keeps it: the holder always succeeds."""
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE)

        renewed = checkpoints.claim(projection, "worker-1", NOW + timedelta(seconds=10), A_WHILE)

        assert renewed is not None
        assert renewed.expires_at == NOW + timedelta(seconds=10) + A_WHILE

    def test_lets_another_owner_claim_a_lapsed_lease(self, checkpoints, projection) -> None:
        """An expiry rather than a lock, because the failure to survive is a worker that dies
        holding it. A lock nothing releases is a projection that never advances again, and the
        first anybody hears of it is a stale view."""
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE)

        after_it_lapsed = NOW + A_WHILE + timedelta(seconds=1)

        taken = checkpoints.claim(projection, "worker-2", after_it_lapsed, A_WHILE)

        assert taken is not None
        assert taken.owner == "worker-2"

    def test_a_released_lease_is_claimable_at_once(self, checkpoints, projection) -> None:
        lease = checkpoints.claim(projection, "worker-1", NOW, A_WHILE)
        assert lease is not None

        checkpoints.release(lease)

        assert checkpoints.claim(projection, "worker-2", NOW, A_WHILE) is not None

    def test_releasing_a_lease_somebody_else_holds_does_nothing(
        self, checkpoints, projection
    ) -> None:
        held = checkpoints.claim(projection, "worker-1", NOW, A_WHILE)
        assert held is not None

        checkpoints.release(Lease(projection=projection, owner="worker-2", expires_at=NOW))

        assert checkpoints.claim(projection, "worker-3", NOW, A_WHILE) is None

    def test_a_lease_does_not_disturb_the_position(self, checkpoints, projection) -> None:
        """The two live in one row, and moving one must not move the other: a claim that reset
        the position would rebuild a projection every time a worker restarted."""
        checkpoints.record(projection, 12)

        lease = checkpoints.claim(projection, "worker-1", NOW, A_WHILE)
        assert lease is not None
        checkpoints.release(lease)

        assert checkpoints.position_of(projection) == 12

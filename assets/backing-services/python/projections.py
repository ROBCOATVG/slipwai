"""The catch-up runner: how an `async` read model is maintained, and how it is rebuilt.

Two verbs over the two ports, and no I/O of its own — which is why it is here beside the
application rather than under `adapters/`, and why its tests need no database.

    catch_up(store, checkpoints, view, owner="worker-1", clock=lambda: datetime.now(UTC))
    rebuild(store, checkpoints, view, owner="worker-1", clock=lambda: datetime.now(UTC))

`catch_up` is one pass: it reads the log from the projection's checkpoint, applies it in batches,
and advances the checkpoint **inside the same transaction as the rows it derived**. `catch_up_each`
is that pass over every projection at once, and what loops over *it* is the framework:
`projections_lifespan.py` is a FastAPI lifespan, started with the app and stopped
with it. A project with only `live` and `inline` read models passes no lifespan and runs nothing
here.

`rebuild` is the same pass from zero, with the view emptied first. It is what makes a read model
disposable: a projection with a bug is fixed by changing the fold and running this, not by
patching rows. It holds the lease across the empty *and* the re-fold, so a worker cannot catch up
into a half-empty view.

## Why exactly-once needs nothing else here

The checkpoint moves in the view's own transaction, so the pair is atomic: a crash before the
commit leaves both untouched, and the next pass reads the same batch again. Nothing is applied
twice and nothing is skipped, and there is no idempotency key to get wrong.

That guarantee is the transaction's, not this file's, and it is worth knowing exactly where it
stops. A projection whose rows are **not** in the same database as the checkpoint — an HTTP
search index, a cache, a file — cannot join that transaction, and for those the fold has to be
idempotent on `global_position` instead: record the position with the row and ignore an event at
or below what the row already holds. The lease reduces how often that matters; it never removes
the need.

## Why a lease and not a lock

Exactly one worker should advance a projection, and a lease with an expiry is how that survives
the worker dying. What it is *not* is the thing that makes the work happen once — the
transaction above is. A projection is a fold and folds are cheap; the lease is there to stop
every replica burning the same log, not to hold the system together.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import islice

from delivery_starter.application.ports.events import EventStore
from delivery_starter.application.ports.read_models import (
    FROM_THE_BEGINNING,
    CheckpointStore,
    Lease,
    Projection,
)

#: How long a claim is good for. Long enough that a slow batch does not lose it, short enough
#: that a dead worker's projection resumes within a stand-up rather than a support call.
DEFAULT_LEASE = timedelta(seconds=30)

#: How many events one transaction applies. A batch is one transaction, so this trades how much
#: work a crash repeats against how long a single transaction holds its locks.
DEFAULT_BATCH_SIZE = 500

#: The clock, as a function, because a pass long enough to need its lease renewed needs the time
#: *again* — which an instant passed in cannot give it. Everywhere else in this project an
#: instant is a typed input; here the input is the clock itself, and a test hands over a list.
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class Advance:
    """What one pass did.

    `leased` is separate from `applied` on purpose: "nothing to apply" and "somebody else is
    already applying it" are both a quiet zero, and a caller that cannot tell them apart will
    read the first as an empty log and the second as a finished rebuild.
    """

    applied: int
    leased: bool


def catch_up(
    store: EventStore,
    checkpoints: CheckpointStore,
    projection: Projection,
    *,
    owner: str,
    clock: Clock,
    ttl: timedelta = DEFAULT_LEASE,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Advance:
    """Apply everything the log has that this projection has not, once.

    Returns without doing anything if another worker holds the lease — that is the ordinary case
    for every replica but one, and not a failure.
    """
    lease = checkpoints.claim(projection.name, owner, clock(), ttl)
    if lease is None:
        return Advance(applied=0, leased=False)
    try:
        return Advance(
            applied=_apply_from_the_checkpoint(
                store,
                checkpoints,
                projection,
                lease=lease,
                clock=clock,
                ttl=ttl,
                batch_size=batch_size,
            ),
            leased=True,
        )
    finally:
        checkpoints.release(lease)


def catch_up_each(
    store: EventStore,
    checkpoints: CheckpointStore,
    projections: Iterable[Projection],
    *,
    owner: str,
    clock: Clock,
    ttl: timedelta = DEFAULT_LEASE,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Advance]:
    """One pass over every projection there is, which is what a scheduled worker calls.

    No projection's failure hides another's. Each is attempted, the advances come back by name, and
    a pass with failures ends by raising one `ExceptionGroup` carrying all of them — so whoever is
    logging sees every one, the next pass tries again, and a projection whose fold is broken does
    not quietly starve every projection after it in the list.
    """
    advances: dict[str, Advance] = {}
    failures: list[Exception] = []
    for projection in projections:
        try:
            advances[projection.name] = catch_up(
                store,
                checkpoints,
                projection,
                owner=owner,
                clock=clock,
                ttl=ttl,
                batch_size=batch_size,
            )
        except Exception as failure:  # noqa: BLE001 - every projection is attempted; see the group below
            failures.append(failure)
    if failures:
        raise ExceptionGroup(f"{len(failures)} projection(s) failed to catch up", failures)
    return advances


def rebuild(
    store: EventStore,
    checkpoints: CheckpointStore,
    projection: Projection,
    *,
    owner: str,
    clock: Clock,
    ttl: timedelta = DEFAULT_LEASE,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Advance:
    """Empty the view, put its checkpoint back to zero, and fold the whole log into it again.

    The reset and the checkpoint go back together, in one transaction, because a view emptied
    without its checkpoint is a permanently empty view and a checkpoint reset without its view is
    a doubled one.
    """
    lease = checkpoints.claim(projection.name, owner, clock(), ttl)
    if lease is None:
        return Advance(applied=0, leased=False)
    try:
        with store.unit_of_work():
            projection.reset()
            checkpoints.record(projection.name, FROM_THE_BEGINNING)
        return Advance(
            applied=_apply_from_the_checkpoint(
                store,
                checkpoints,
                projection,
                lease=lease,
                clock=clock,
                ttl=ttl,
                batch_size=batch_size,
            ),
            leased=True,
        )
    finally:
        checkpoints.release(lease)


def _apply_from_the_checkpoint(
    store: EventStore,
    checkpoints: CheckpointStore,
    projection: Projection,
    *,
    lease: Lease,
    clock: Clock,
    ttl: timedelta,
    batch_size: int,
) -> int:
    """Batch after batch until the log runs out, holding `lease` throughout.

    The checkpoint is re-read each time round rather than tracked in a local, so a batch that
    rolled back is read again instead of being skipped by a variable the database never agreed
    with.
    """
    applied = 0
    while True:
        position = checkpoints.position_of(projection.name)
        batch = tuple(islice(store.read_all(position), batch_size))
        if not batch:
            return applied
        with store.unit_of_work():
            projection.apply(batch)
            # The next position, not the last one applied: what `position_of` promises is where
            # to resume, and an off-by-one here re-applies one event forever.
            checkpoints.record(projection.name, batch[-1].global_position + 1)
        applied += len(batch)
        if len(batch) < batch_size:
            return applied
        if checkpoints.claim(lease.projection, lease.owner, clock(), ttl) is None:
            # The lease lapsed mid-pass and somebody else took it: stop where the checkpoint is,
            # which the new owner will read. Losing a lease is not an error — it is a slow pass.
            return applied

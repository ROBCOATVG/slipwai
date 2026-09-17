"""What runs an `async` read model: FastAPI's lifespan, ticking a catch-up pass.

A lifespan rather than a thread this project starts, and the difference is what the framework
gives back. FastAPI enters it as the app starts and leaves it as the app stops, so Ctrl-C in
`make dev` and a container's SIGTERM both stop the passes — with the shutdown *waiting* for the
pass in flight rather than killing it mid-transaction.

The pass itself is synchronous, because the stores are, and `asyncio.to_thread` is what keeps it
off the event loop — running a blocking pass there would stall every request while a batch
commits. The standard library and nothing else, and FastAPI is not imported at all: the read side
arrives with the event store, and a project can have one with no HTTP adapter to hang this on.
An `@asynccontextmanager` taking the app is exactly what `FastAPI(lifespan=...)` wants, so the
absence of the import costs nothing.

Wired in the composition root, which is the only place that knows which store this project uses.
The imports are relative because that is what the composition root's own already are:

    from .adapters.driven.checkpoint_store_postgres import create_postgres_checkpoint_store
    from .adapters.driven.event_store_postgres import open_postgres_event_store
    from .projections_lifespan import maintaining_projections

    store = open_postgres_event_store(os.environ["DATABASE_URL"])
    checkpoints = create_postgres_checkpoint_store(store)
    app = build_app(
        [register_order_routes(store)],
        lifespan=maintaining_projections(store, checkpoints, [orders_by_customer(store)]),
    )

A project whose read models are all `live` or `inline` passes no lifespan, and nothing runs.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta

from delivery_starter.application.ports.events import EventStore
from delivery_starter.application.ports.read_models import (
    CheckpointStore,
    Projection,
)
from delivery_starter.projections import catch_up_each

#: How long between passes. This is the lag this project accepts on its async views — the whole
#: cost of that answer, in one number — so it is an argument rather than a constant, and
#: `PROJECTIONS_EVERY_MS` is where a deployment turns it down.
DEFAULT_EVERY = timedelta(seconds=1)

_log = logging.getLogger(__name__)


def maintaining_projections(
    store: EventStore,
    checkpoints: CheckpointStore,
    projections: Sequence[Projection],
    *,
    every: timedelta | None = None,
    owner: str | None = None,
) -> Callable[[object], AbstractAsyncContextManager[None]]:
    """A lifespan that catches every projection up, over and over, while the app runs.

    `owner` defaults to a fresh identity per process: two replicas sharing a name would be one
    owner as far as the lease is concerned, and the holder of a lease may always renew it — so a
    shared name is two workers both certain they hold it.
    """
    interval = every if every is not None else _every_from_the_environment()
    holder = owner if owner is not None else f"worker-{uuid.uuid4()}"

    @asynccontextmanager
    async def lifespan(_app: object) -> AsyncIterator[None]:
        if not projections:
            yield
            return
        passes = asyncio.create_task(
            _keep_catching_up(store, checkpoints, projections, holder, interval)
        )
        try:
            yield
        finally:
            # Cancelled on shutdown, and awaited, which is what makes it orderly: a cancellation
            # lands between passes or while one is in a thread, and awaiting it means the batch in
            # flight is never abandoned halfway through a transaction.
            passes.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await passes

    return lifespan


async def _keep_catching_up(
    store: EventStore,
    checkpoints: CheckpointStore,
    projections: Sequence[Projection],
    owner: str,
    every: timedelta,
) -> None:
    while True:
        try:
            await asyncio.to_thread(
                catch_up_each,
                store,
                checkpoints,
                projections,
                owner=owner,
                clock=lambda: datetime.now(UTC),
            )
        except Exception:  # noqa: BLE001 - a failed pass must not end the subscription
            # Logged rather than raised: an exception here would take the task group down and with
            # it the app, so a projection that fails every pass would be a crash loop rather than a
            # stale view. `catch_up_each` has already tried every projection, so nothing is hidden.
            _log.exception("projection pass failed")
        # After the pass rather than on a fixed schedule, so a pass slower than the interval cannot
        # have a second pass pile up behind it. Skipping costs nothing: the checkpoint means the
        # next pass resumes exactly where this one stopped.
        await asyncio.sleep(every.total_seconds())


def _every_from_the_environment() -> timedelta:
    return timedelta(milliseconds=int(os.environ.get("PROJECTIONS_EVERY_MS", "1000")))

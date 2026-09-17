"""The lifespan that runs the catch-up runner — the timer, not the loop.

What is worth asserting here is exactly what the lifespan contributes: that a pass happens without
anybody calling it, and that leaving the lifespan stops it. The loop itself is
`test_projections.py`.

Driven directly rather than through a `TestClient`, because the lifespan ships with the read side
and the read side ships without a transport — a test that imported FastAPI would not run in a
project that has no HTTP adapter. What that costs is one thing: whether FastAPI itself enters and
leaves it. That is FastAPI's promise rather than this project's, and `build_app(lifespan=...)` is
where the two meet.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import timedelta
from threading import Thread

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
from delivery_starter.projections_lifespan import (
    maintaining_projections,
)

EVERY = timedelta(milliseconds=5)


class Titles:
    name = "titles"

    def __init__(self) -> None:
        self.rows: list[str] = []

    def apply(self, events: Sequence[CommittedEvent]) -> None:
        self.rows.extend(event.type for event in events)

    def reset(self) -> None:
        self.rows.clear()


def append(store: EventStore, event_type: str) -> None:
    stream = f"lifespan-{uuid.uuid4()}"
    store.append(
        stream,
        NO_STREAM,
        [
            DomainEvent(
                type=event_type,
                schema_version=1,
                stream_id=stream,
                payload={},
                occurred_at="2024-01-01T00:00:00+00:00",
                actor=Actor(kind="test", id="projections"),
                correlation_id=create_correlation_id(uuid.uuid4()),
            )
        ],
    )


def until(condition, timeout: float = 2.0) -> bool:
    """Poll rather than sleep for a fixed time: a passing test then costs one interval, and a
    failing one is not a flake waiting for a slower machine."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.005)
    return False


@contextmanager
def running(lifespan) -> Iterator[None]:
    """Enter the lifespan on an event loop of its own, as a server's start-up does, and leave it on
    the way out.

    A thread because the passes are asynchronous and the assertions are not: this is the smallest
    thing that behaves like uvicorn without being it.
    """
    started, finished = asyncio.Event(), asyncio.Event()
    loop = asyncio.new_event_loop()

    async def enter() -> None:
        async with lifespan(None):
            started.set()
            await finished.wait()

    def serve() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(enter())
        loop.close()

    thread = Thread(target=serve, daemon=True)
    thread.start()
    try:
        assert until(started.is_set), "the lifespan never started"
        yield
    finally:
        loop.call_soon_threadsafe(finished.set)
        thread.join(timeout=5)
        assert not thread.is_alive(), "the lifespan never finished"


def test_catches_a_projection_up_without_anybody_calling_it() -> None:
    store = create_in_memory_event_store()
    view = Titles()
    append(store, "Placed")
    lifespan = maintaining_projections(
        store, create_in_memory_checkpoint_store(store), [view], every=EVERY
    )

    with running(lifespan):
        assert until(lambda: view.rows == ["Placed"]), view.rows


def test_stops_passing_when_the_app_shuts_down() -> None:
    store = create_in_memory_event_store()
    view = Titles()
    lifespan = maintaining_projections(
        store, create_in_memory_checkpoint_store(store), [view], every=EVERY
    )

    with running(lifespan):
        pass

    # Appended *after* shutdown, so a pass still running would pick it up. Nothing does, which is
    # the whole reason this is a lifespan: a loop nobody cancels outlives SIGTERM.
    append(store, "Placed")
    assert not until(lambda: view.rows != [], timeout=0.2)
    assert view.rows == []

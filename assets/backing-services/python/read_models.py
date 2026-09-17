"""The read-side port: where a projection has got to, and who is allowed to advance it.

The write side of this project arrives finished — a port, its adapters, one contract suite. This
is the other half, and it exists because the half that was missing is the half that gets invented
badly: a read model folded in the request because that was the only read path already built.

Two ports, and they are deliberately separate:

  * `CheckpointStore` — how far a named projection has consumed the log, and an exclusive lease so
    exactly one worker advances it. This is infrastructure, and it ships with adapters.
  * `Projection` — what a project's own view *is*: a fold with somewhere to put the result. This
    ships as an interface only, because the rows are the project's.

**A checkpoint is only a checkpoint if it commits with the rows it describes.** Everything here is
shaped by that one sentence: `record` never commits on its own, and the runner in
`projections.py` calls it inside `EventStore.unit_of_work()`, so the position and the view move
together or neither moves. Record it separately and you have chosen, without noticing, between
losing updates and applying them twice.

`docs/event-model/README.md` says which of the three lifecycles — `live`, `inline`, `async` — a
slice's read model uses, and `make check-model` makes a slice say so before it can be planned.
This file is what `async` is built from, and `unit_of_work` is what `inline` is built from.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from delivery_starter.application.ports.events import CommittedEvent

#: Where a projection that has never run starts. The position is the *next* global position to
#: apply, so zero means "the whole log", and a rebuild is `record(name, FROM_THE_BEGINNING)`
#: followed by a catch-up.
FROM_THE_BEGINNING = 0


@dataclass(frozen=True, slots=True)
class Lease:
    """The right to advance one projection, held by one worker until it expires.

    An expiry rather than a lock, because the failure to survive is a worker that dies holding
    it: a lock nothing releases is a projection that never advances again, and the first anybody
    hears of it is a stale view. A lease that lapses is a projection that resumes on its own.

    The lease is an **efficiency measure, not a correctness one**. Two workers holding it at once
    would each apply events under `unit_of_work`, and the checkpoint moving in the same
    transaction is what makes the loser's work a no-op rather than a duplicate. The lease is what
    stops that being the normal case — see `projections.py`.
    """

    projection: str
    owner: str
    expires_at: datetime


class CheckpointStore(Protocol):
    """Where each projection has got to, and who currently owns advancing it.

    Every adapter is built from the event store it follows, deliberately: `record` has to land in
    the same transaction as the view write, and two adapters on two connections cannot do that
    however carefully they are called.
    """

    def position_of(self, projection: str) -> int:
        """The next global position this projection has not yet applied.

        `FROM_THE_BEGINNING` for a projection nothing has recorded — an unknown projection is one
        that has consumed nothing, not an error. A rebuild has to be expressible without a
        special case.
        """
        ...

    def record(self, projection: str, position: int) -> None:
        """Move the checkpoint. **Does not commit** — the caller's `unit_of_work` does.

        Call it inside the same unit of work as the writes it accounts for, always. It is safe to
        call outside one, and then it commits with whatever the connection is doing, which is
        exactly the mistake this docstring exists to name.
        """
        ...

    def claim(
        self,
        projection: str,
        owner: str,
        now: datetime,
        ttl: timedelta,
    ) -> Lease | None:
        """Take or renew the lease, or `None` if somebody else holds an unexpired one.

        `now` is passed in rather than read from a clock, for the reason every instant in this
        project is: a test that cannot choose the time cannot test expiry without sleeping.
        The owner already holding the lease always succeeds, which is how a long catch-up renews.
        """
        ...

    def release(self, lease: Lease) -> None:
        """Give the lease up early. A lease held by somebody else is left alone.

        Releasing is politeness, not correctness: not releasing costs the next worker one `ttl`.
        """
        ...


class Projection(Protocol):
    """A read model that is maintained rather than folded per query — `inline` or `async`.

    Three requirements, and the third is the one usually missed:

      * `name` identifies its checkpoint. Stable for the life of the projection: renaming it
        silently starts a second projection at position zero.
      * `apply` folds a batch into whatever the view is kept in. Under `async` it is called
        inside `EventStore.unit_of_work()`, so it must write through the same connection and must
        not commit; under `inline` the append's transaction is the one it joins.
      * `reset` empties the view. Without it the projection is not disposable, and a projection
        that cannot be rebuilt is a second source of truth — which is the whole thing an event
        log exists to avoid.

    Every row a projection writes is **derived**: it comes from the events, and nothing else. A
    column the projection alone knows — a `done_at` the worker stamps when it processes the row —
    cannot survive `reset`, and finding that out during an incident is how a rebuild becomes
    data loss. Where a value like that is needed, it belongs in an event.
    """

    @property
    def name(self) -> str: ...

    def apply(self, events: Sequence[CommittedEvent]) -> None: ...

    def reset(self) -> None: ...

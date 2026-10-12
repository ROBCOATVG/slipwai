"""The migration report shared by ordinary replay and the version 1 crossing."""
from __future__ import annotations

from dataclasses import dataclass

from .replay import Replay
from .unlabel import Refresh


@dataclass(frozen=True)
class Migration:
    """What `migrate` did: the replay it merged, the version the project was on, and how the merge ended."""

    offered: Replay
    was: str | None
    # Files with conflict markers, in path order; empty when the merge committed.
    conflicts: tuple[str, ...]
    # `git diff --stat`'s last line for what the keel changed since the base, or None when it changed nothing.
    changed: str | None
    # Whether the merge was a fast-forward: the project had nothing of its own since the last factory commit.
    fast_forward: bool = False
    # The projections re-derived after a clean merge; nothing at all where the merge stopped at a conflict.
    refresh: Refresh = Refresh()
    # Why the catch-up notes could not be written, or None when they were — which is every migration that
    # changed anything, whatever the versions crossed asked.
    unwritten: str | None = None


"""The strip on the Board tab that says a newer slipwai is out, and how to get it.

It tells and does not replace (double-click-plan.md, D5): a running copy cannot swap itself out, which is
what `upgrade.py` already says of the executable. The answer is `upgrade.newer_published`, the same
question `slipwai upgrade` and `migrate` ask, asked on a thread of its own at most once a day so a page is
never held waiting on the network — and a machine with no network sees no strip and no error.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .assets import FROZEN, INSTALLED
from .page_shell import esc
from .upgrade import FORGE, newer_published

#: How long one answer stands before it is asked again.
DAY = 24 * 60 * 60


class Newer:
    """The newest published version when it is newer than this one, asked in the background and kept."""

    def __init__(self, ask: Callable[[], str | None] = newer_published, clock: Callable[[], float] = time.time) -> None:
        self.ask, self.clock = ask, clock
        self.version: str | None = None
        self.asked_at = float("-inf")
        self.lock = threading.Lock()

    def refresh(self) -> None:
        try:
            found = self.ask()
        except Exception:  # noqa: BLE001 — no network, a refusal, a page that will not parse: all mean no strip
            found = None
        with self.lock:
            self.version = found

    def now(self, background: bool = True) -> str | None:
        """What is known now; a stale answer starts a fresh one and is returned meanwhile."""
        with self.lock:
            stale = self.clock() - self.asked_at > DAY
            if stale:
                self.asked_at = self.clock()
        if stale:
            if background:
                threading.Thread(target=self.refresh, daemon=True).start()
            else:
                self.refresh()
        with self.lock:
            return self.version


NEWER = Newer()


def banner(version: str | None = None, frozen: bool = FROZEN) -> str:
    """The strip, or `""` where this copy is the newest the board knows of. A checkout never asks: it follows
    `main`, and a release is never newer than what somebody working on the keel is running."""
    if version is None and not (FROZEN or INSTALLED):
        return ""
    version = NEWER.now() if version is None else version
    if not version:
        return ""
    how = (f'Download it from <a href="{FORGE}/releases/latest" target="_blank" rel="noopener">the releases '
           f'page</a> and open it; it replaces this one.' if frozen else
           "Run <code>slipwai upgrade</code> to get it.")
    return f'<div class="card lacking"><p>slipwai {esc(version)} is out. {how}</p></div>'

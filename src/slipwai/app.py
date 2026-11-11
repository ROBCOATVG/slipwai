"""The app: what `Slipwai.app` and `slipwai-board.exe` are built from, the same keel as the command.

Opened with nothing after it — a double-click — it is the app: `first_run.start` places it, keeps the board
running and opens it. Given anything at all it is the command, because the login service it registers runs
this very file as `<app> bridge --serve …`, and an agent told to run `slipwai` reaches it through the link
`first_run.link_command` makes. The command line therefore loses nothing by being opened this way, and
`cli_start.will_open` — which opens the board only for a person at a terminal — is not touched.
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from slipwai import certificates, first_run, splash
from slipwai.cli import main as command

#: Where an app with no terminal says what it would have printed.
LOG = Path.home() / ".slipwai" / "app.log"


def arguments(argv: list[str]) -> list[str]:
    """What was asked for, without the `-psn_…` process serial number older macOS adds to a Finder launch."""
    return [one for one in argv if not one.startswith("-psn_")]


def quiet() -> None:
    """A windowed build on Windows has no standard output at all, and a `print` there is a crash."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    held = LOG.open("a", encoding="utf-8")
    sys.stdout = sys.stdout or held
    sys.stderr = sys.stderr or held


def windowless(system: str | None = None, console: Callable[[], int] | None = None) -> bool:
    """Whatever this process starts opens no console window, where this process has none itself.

    The app on Windows is a windowed program. A console program started by one is given a console of its
    own, and Windows shows it: every agent session, every `git`, opened a terminal window that stayed
    blank — its output goes down a pipe to the board — and looked stuck, and closing it ended the session.
    A child told `CREATE_NO_WINDOW` has a console nobody sees, and what it starts shares that one. Set once
    here rather than at each of the sixty places the keel starts something. A caller that asks for a
    window — the sign-in, *Open a terminal here* — passes its own flags and is left alone, and so is a
    process started from a terminal, whose children belong in it. True where it was set."""
    if (system or sys.platform) != "win32":
        return False
    if console is None:
        import ctypes  # noqa: PLC0415 — Windows only
        console = ctypes.windll.kernel32.GetConsoleWindow  # type: ignore[attr-defined]
    if console():
        return False
    start, hidden = subprocess.Popen.__init__, getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    def quietly(self: Any, *args: Any, creationflags: int = 0, **kwargs: Any) -> None:
        start(self, *args, creationflags=creationflags or hidden, **kwargs)

    subprocess.Popen.__init__ = quietly  # type: ignore[method-assign]
    return True


def main(argv: list[str] | None = None) -> None:
    asked = arguments(sys.argv[1:] if argv is None else argv)
    quiet()
    windowless()
    # A first launch fetches before it reaches the command, so the app says it here as well.
    certificates.install()
    # The picture is for a double-click. Whatever this process starts — the board's children, an agent's
    # `slipwai` — is this same file as the command, and opens without it.
    splash.quiet_children()
    if asked:
        splash.close()
        sys.argv = [sys.argv[0], *asked]
        command()
        return
    first_run.start()


if __name__ == "__main__":
    main()

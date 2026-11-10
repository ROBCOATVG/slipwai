"""The app: what `Slipwai.app` and `slipwai-board.exe` are built from, the same keel as the command.

Opened with nothing after it — a double-click — it is the app: `first_run.start` places it, keeps the board
running and opens it. Given anything at all it is the command, because the login service it registers runs
this very file as `<app> bridge --serve …`, and an agent told to run `slipwai` reaches it through the link
`first_run.link_command` makes. The command line therefore loses nothing by being opened this way, and
`cli_start.will_open` — which opens the board only for a person at a terminal — is not touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

from slipwai import certificates, first_run
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


def main(argv: list[str] | None = None) -> None:
    asked = arguments(sys.argv[1:] if argv is None else argv)
    quiet()
    # A first launch fetches before it reaches the command, so the app says it here as well.
    certificates.install()
    if asked:
        sys.argv = [sys.argv[0], *asked]
        command()
        return
    first_run.start()


if __name__ == "__main__":
    main()

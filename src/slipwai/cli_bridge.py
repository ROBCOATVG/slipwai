"""`slipwai bridge`: serve the board locally, and `--publish` to write the read-only copy as a file."""
from __future__ import annotations

import argparse
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path

from .assets import this_command
from .at_login import board_install as install_board
from .at_login import remove as remove_at_login
from .bridge_page import read_only
from .cli_start import open_board, running
from .errors import GenerationError, refuse
from .fleet import board
from .harbour import config
from .project.harbour import CONFIG


def up(host: str, port: int, seconds: float = 10.0) -> Callable[[], bool]:
    """Whether the board answers within a few seconds — the service was just told to start, and a browser
    sent to a port nothing is listening on yet is a blank tab and a person who concludes it is broken."""
    def waited() -> bool:
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            if running(host, port):
                return True
            time.sleep(0.25)
        return running(host, port)
    return waited


def bridge_main(argv: list[str]) -> None:
    prog = f"{this_command()} bridge"
    parser = argparse.ArgumentParser(
        prog=prog, description="The board as a page you can answer from",
        epilog="An answer typed on the page becomes a line in that stream's own log, which is the point: a "
               "person answers from one seat. It binds the loopback address, because the page changes what "
               "a run does and a default that put that on a shared network would be wrong once and then "
               "permanently.")
    # One word rather than a flag, because it is a different thing to do with this machine rather than a
    # different way to serve: `install` is the only way most people will ever want the board — running, and
    # in the dock — and it is the one thing a person who does not open terminals has to be told to type once.
    parser.add_argument("what", nargs="?", choices=("install", "uninstall"), default=None,
                        help="install: keep the board running on this machine and open it so the browser can "
                             "put it in your dock. uninstall: stop it starting with you")
    parser.add_argument("--root", default=".", metavar="<directory>", help="the harbour (default: here)")
    parser.add_argument("--host", default="127.0.0.1", help="what to bind (default: this machine only)")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--publish", metavar="<file>", default=None,
                        help="write the read-only copy to a file and exit, which is what Pages serves")
    # What a service runs, and what makes one. Serving is not opening: nobody is at the machine when a
    # login service starts, and the directory it starts in is not a project yet — the board has always
    # opened in one that is not, and the page attaches anywhere else.
    parser.add_argument("--serve", action="store_true",
                        help="serve and open nothing, in whatever directory — what the login service runs")
    parsed = parser.parse_args(argv)
    root = Path(parsed.root).expanduser()
    if parsed.what is not None:
        print("\n".join(install_board(root, parsed.host, parsed.port, wait=up(parsed.host, parsed.port))
                        if parsed.what == "install" else remove_at_login()))
        return
    try:
        if not parsed.serve and not (root / ".slipwai").is_dir() and not (root / CONFIG).is_file():
            raise GenerationError(f"{root} is not a harbour: it has no .slipwai/ and no {CONFIG}")
        if parsed.publish:
            held = config(root)
            Path(parsed.publish).write_text(read_only(board(root, held), held), encoding="utf-8")
            print(f"{parsed.publish} written — the same page with nothing to press")
            return
        # There is one board, and this verb is a deep link into it: run while one is already serving, this
        # opens a tab on that one rather than starting a rival on another port. `--serve` opens nothing and
        # is still that rule: a service that bound a second port would be a second board.
        server = open_board(root, parsed.host, parsed.port, at="/",
                            open_page=(lambda where: None) if parsed.serve else webbrowser.open)
    except GenerationError as error:
        refuse(prog, error)
    except OSError as error:
        refuse(prog, f"the bridge could not bind {parsed.host}:{parsed.port} ({error}). "
                     f"`--port <n>` moves it")
    if server is None:
        print(f"bridge: http://{parsed.host}:{parsed.port}/  — already open, so this opened a tab on it")
        return
    print(f"bridge: http://{parsed.host}:{parsed.port}  — ctrl-c to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()

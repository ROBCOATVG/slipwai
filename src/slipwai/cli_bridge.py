"""`slipwai bridge`: serve the board locally, and `--publish` to write the read-only copy as a file."""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .bridge_page import read_only
from .cli_start import open_board
from .errors import GenerationError, refuse
from .fleet import board
from .harbour import config
from .project.harbour import CONFIG


def bridge_main(argv: list[str]) -> None:
    prog = f"{this_command()} bridge"
    parser = argparse.ArgumentParser(
        prog=prog, description="The board as a page you can answer from",
        epilog="An answer typed on the page becomes a line in that stream's own log, which is the point: a "
               "person answers from one seat. It binds the loopback address, because the page changes what "
               "a run does and a default that put that on a shared network would be wrong once and then "
               "permanently.")
    parser.add_argument("--root", default=".", metavar="<directory>", help="the harbour (default: here)")
    parser.add_argument("--host", default="127.0.0.1", help="what to bind (default: this machine only)")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--publish", metavar="<file>", default=None,
                        help="write the read-only copy to a file and exit, which is what Pages serves")
    parsed = parser.parse_args(argv)
    root = Path(parsed.root).expanduser()
    try:
        if not (root / ".slipwai").is_dir() and not (root / CONFIG).is_file():
            raise GenerationError(f"{root} is not a harbour: it has no .slipwai/ and no {CONFIG}")
        if parsed.publish:
            held = config(root)
            Path(parsed.publish).write_text(read_only(board(root, held), held), encoding="utf-8")
            print(f"{parsed.publish} written — the same page with nothing to press")
            return
        # There is one board, and this verb is a deep link into it: run while one is already serving, this
        # opens a tab on that one rather than starting a rival on another port.
        server = open_board(root, parsed.host, parsed.port, at="/")
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

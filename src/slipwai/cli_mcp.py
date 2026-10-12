"""`slipwai mcp`: the read side served to whatever is doing the work, over stdin and stdout.

Not a daemon and not a port. A harness starts this as a child process and speaks JSON-RPC down the pipe,
which is what makes it installable by a line in a configuration file rather than by somebody remembering to
start something.

The verb is bare on purpose: everything it serves is already a verb, and the whole of what this adds is the
other end of the pipe. `--root` is the harbour, because a harness starts the server from wherever it
happens to be.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import mcp
from .assets import this_command
from .errors import GenerationError, refuse


def mcp_main(argv: list[str]) -> None:
    prog = f"{this_command()} mcp"
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Serve the read side — the board, a stream's log, the inbox, clearance and the chart — "
                    "as MCP tools over stdin and stdout, plus the one write the bridge already allows",
        epilog="A harness starts this itself: point its MCP configuration at this command with `--root` "
               "set to the project. `slipwai package plugin` writes that configuration for Claude Code and "
               "`slipwai package harness <key>` for the others.")
    parser.add_argument("--root", default=".", metavar="<directory>", help="the harbour (default: here)")
    parsed = parser.parse_args(argv)
    root = Path(parsed.root).expanduser()
    try:
        mcp.serve(root, sys.stdin, sys.stdout)
    except GenerationError as error:
        refuse(prog, error)
    except (BrokenPipeError, KeyboardInterrupt):
        # The harness closed the pipe, which is how a session ends. Not a fault to print into a log.
        return

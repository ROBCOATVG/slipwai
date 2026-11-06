"""`slipwai brief check <dir>`: the folder the front door reads, read before anything is generated."""
from __future__ import annotations

import argparse
from pathlib import Path

from .assets import this_command
from .brief_check import report
from .errors import GenerationError, refuse


def brief_main(argv: list[str]) -> None:
    prog = f"{this_command()} brief"
    parser = argparse.ArgumentParser(
        prog=prog, description="A brief is one folder; this says what `generate --brief` will read from it",
        epilog="The folder's shape is docs/reference/the-brief.md: the requirements document is found by name "
               "or by its first heading, everything else is carried as design material, and each page under "
               "surfaces/ is one surface with an <article class=\"state\"> per state.")
    parser.add_argument("verb", choices=("check",),
                        help="check: read the folder the way generate --brief would, and say what it found")
    parser.add_argument("folder", nargs="?", metavar="<dir>", help="the folder the brief is in")
    parsed = parser.parse_args(argv)
    if parsed.folder is None:
        refuse(prog, f"name the folder: {prog} check <dir>")
    try:
        print("\n".join(report(Path(parsed.folder).expanduser())))
    except GenerationError as error:
        refuse(prog, error)

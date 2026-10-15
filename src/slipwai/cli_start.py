"""`slipwai` with nothing after it: the board, opened, rather than a usage message.

A usage message is the right answer for a tool somebody already knows and the wrong one for everything this
keel has been adding. There is a fleet board and there is a bridge, and neither is what a person reaches
first, because reaching them means knowing they exist. The verb that needs no argument should be the one
that shows you where you are, so bare `slipwai` opens the board and `slipwai --help` is what prints the
verbs.

**In a directory that is not a project it opens the board anyway**, empty, with what it *can* do from there.
The alternative — an empty board and a sentence telling somebody to go back to the terminal — is the moment
the tool was supposed to stop being a terminal.

**A tool run from a script has nobody to show a page to.** `--no-browser`, and a standard input that is not
a terminal, fall back to exactly the usage message this printed before. That is the whole of the rule: the
page is for the person who typed one word, and nothing else about any verb changes.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
import webbrowser
from collections.abc import Callable
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

from .assets import this_command
from .bridge import serve
from .errors import refuse

#: What the bridge binds, and what this binds with it: one board, one port.
HOST = "127.0.0.1"
PORT = 8099
#: The one flag a bare command takes for the sake of a script, and the three for the sake of a person whose
#: harbour or port is not the default. A first argument that is none of these is a verb, however spelled, and
#: belongs to the parser that refuses it by name.
NO_BROWSER = "--no-browser"
START_FLAGS = (NO_BROWSER, "--root", "--host", "--port")


def board_or_usage(argv: list[str]) -> list[str]:
    """What is left for the usage message, the board having been opened and closed where it could be.

    The one place that decides what no verb means, so `cli.dispatch` holds a line rather than the rule: the
    board is what answers the one word somebody who knows nothing else types, and where it is declined —
    `--no-browser`, or a script, which has nobody to show a page to — what is left is exactly the usage
    message that command always printed. A first argument that is not one of `START_FLAGS` is a verb however
    it is spelled, and goes to the parser that refuses it by name.

    A board that was opened and then closed is a command that has finished, so this exits rather than
    returning: falling through to the usage message after somebody has read the page and pressed ctrl-c
    would end a successful run with an error.
    """
    if argv and argv[0].partition("=")[0] not in START_FLAGS:
        return argv
    if start_main(argv):
        raise SystemExit(0)
    return []


def will_open(argv: list[str], interactive: bool) -> bool:
    """Whether a bare command should open a page rather than print the usage message.

    Two ways of saying no and they mean the same thing: there is nobody here to look at it. A script that
    got a server instead of the message it expected would hang, and hanging is the one failure a command
    line may not have.
    """
    return interactive and NO_BROWSER not in argv


def running(host: str = HOST, port: int = PORT, timeout: float = 0.5) -> bool:
    """Whether a board is already serving there.

    Asked of `/board.json`, which every board answers and nothing else on the machine would: the question is
    not "is this port taken" but "is the board already up", and the answer decides whether a verb joins it
    or binds one. `Server` is `http.server`'s own header, which the bridge names itself in.
    """
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/board.json", timeout=timeout) as answer:
            return str(answer.headers.get("Server", "")).startswith("slipwai")
    except (OSError, ValueError):  # HTTPError and URLError are both OSError; a bad URL is a ValueError
        return False


def looking_at(root: Path, at: str = "/") -> str:
    """That page, naming the directory the window opening it should look at.

    The board was one view of one directory until windows had seats of their own, so `--root` could only
    mean anything to the process that bound the port: typed at a board that was already serving it was
    dropped, and the tab that opened showed whatever that board was looking at. A window carries its own
    directory now, so the flag can mean what it says — `look` is read once, by the seat the new window is
    given on arrival, and is gone from the address after that.
    """
    return f"{at}{'&' if '?' in at else '?'}look={quote(str(root.expanduser().resolve()))}"


def open_board(root: Path, host: str = HOST, port: int = PORT,
               open_page: Callable[[str], object] = webbrowser.open,
               at: str = "/") -> ThreadingHTTPServer | None:
    """The browser pointed at the board, and the server that was bound for it — `None` where one was already
    serving and this joined it instead.

    There is one board, so a second verb opens a tab on the first rather than starting a rival on another
    port. Two servers each sure they are the board is the failure this prevents, and it is not theoretical:
    a person who ran `slipwai bridge` in one terminal and `slipwai` in another had two.

    Either way the window is opened on `root`, which is the whole of what makes two projects at once a
    thing somebody can do from a terminal: `slipwai --root ~/a` and then `slipwai --root ~/b` is two
    windows on two projects, rather than a second window on the first one's directory.

    Bound first and opened second, always: a browser sent to a port nothing is listening on is a blank tab
    and a person who concludes the command is broken. The server is returned rather than run, so a test can
    drive it and close it.
    """
    where = looking_at(root, at)
    if running(host, port):
        open_page(f"http://{host}:{port}{where}")
        return None
    server = serve(root, host, port)
    open_page(f"http://{host}:{server.server_address[1]}{where}")
    return server


def start_main(argv: list[str], *, interactive: bool | None = None,
               open_page: Callable[[str], object] = webbrowser.open) -> bool:
    """Open the board, or say that this was not the moment to: `False` means the caller prints the usage.

    `interactive` is the seam the suite sets; unsaid, it is whether standard input is a terminal.
    """
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not will_open(argv, interactive):
        return False
    prog = this_command()
    parser = argparse.ArgumentParser(
        prog=prog, description="Open the board: the fleet, and what can be started from here",
        epilog=f"`{prog} --help` lists the verbs. `{NO_BROWSER}`, and anything run from a script, print "
               f"that list instead of opening a page — a tool run without a person has nobody to show one "
               f"to.")
    parser.add_argument("--root", default=".", metavar="<directory>", help="the harbour (default: here)")
    parser.add_argument("--host", default=HOST, help="what to bind (default: this machine only)")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument(NO_BROWSER, action="store_true", help="print the verbs instead of opening a page")
    parsed = parser.parse_args(argv)
    root = Path(parsed.root).expanduser()
    try:
        server = open_board(root, parsed.host, parsed.port, open_page)
    except OSError as error:
        refuse(prog, f"the board could not bind {parsed.host}:{parsed.port} ({error}). "
                     f"`{prog} --port <n>` moves it")
    if server is None:
        print(f"board: http://{parsed.host}:{parsed.port}/  — already open, so this opened a tab on it")
        return True
    print(f"board: http://{parsed.host}:{server.server_address[1]}/  — ctrl-c to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return True

"""`slipwai fleet` and `slipwai fleet watch`: the board, drawn from the logs each time it is asked for.

What a person wants from a board is one answer: *is anything waiting on me, and is anything stuck?* So those
two are at the top and everything else is under them. The berth table is what is running; the inbox is what
is waiting on a person; the feed is the last lines of both logs, which is where a reader goes when a row
does not say enough.

`watch` redraws on an interval. Not a daemon and not a subscription: it folds the logs again, because the
whole board is a fold and one that cached anything could be wrong about what happened.
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from .assets import this_command
from .cli_start import start_main
from .deck import RECENT, recent, streams
from .errors import GenerationError, refuse
from .fleet import NOTHING, board, inbox_detail
from .fleet_page import headline
from .fleet_record import clock_of
from .harbour import config
from .project.harbour import CONFIG

CLEAR = "\x1b[H\x1b[2J"


def table(rows: list[dict], columns: list[tuple[str, str]]) -> list[str]:
    """One table, each column as wide as its widest cell. No box drawing: a board is read, not admired."""
    if not rows:
        return []
    widths = {key: max(len(title), *(len(str(row.get(key, ""))) for row in rows)) for key, title in columns}
    head = "  ".join(title.ljust(widths[key]) for key, title in columns)
    lines = [f"  {head}", "  " + "  ".join("-" * widths[key] for key, _ in columns)]
    return lines + ["  " + "  ".join(str(row.get(key, "")).ljust(widths[key]) for key, _ in columns)
                    for row in rows]


def lines(root: Path) -> list[str]:
    """The whole board, as it is printed."""
    held = config(root)
    found = board(root, held)
    width = max(shutil.get_terminal_size().columns, 60)
    said: list[str] = []

    waiting = found["inbox"]
    assert isinstance(waiting, list)
    _, sentence, under = headline(found)
    said += [sentence, f"  {under}"]
    on_you = [row for row in waiting if row.get("paused") != "yes"]
    resting = [row for row in waiting if row.get("paused") == "yes"]
    said.append(f"waiting on you: {len(on_you)}" if on_you else "waiting on you: nothing")
    for row in on_you:
        detail = inbox_detail(row)
        said.append(f"  {row['fairway']:<10} {row['kind']:<7} {detail[:width - 24]}")
    if resting:
        said.append(f"paused, nothing for you to do: {len(resting)}")
        for row in resting:
            said.append(f"  {row['fairway']:<10} {row.get('slice') or '':<7} {inbox_detail(row)[:width - 24]}")

    processes = found["processes"]
    assert isinstance(processes, list)
    said += ["", "processes"]
    for row in processes:
        when = clock_of(row["since"]) if row["since"] else ""
        rest = row["why"] or (f"starts again when {row['starts_when']}" if row["starts_when"] else "")
        said.append(f"  {row['name']:<22} {row['state']:<8} {when:<6} {rest[:width - 42]}")

    berths = found["berths"]
    assert isinstance(berths, list)
    stalled = [row for row in berths if row["state"] == "stalled"]
    said += ["", f"berths: {len(berths)}" + (f", {len(stalled)} stalled" if stalled else "")]
    said += table(berths, [("fairway", "fairway"), ("feature", "feature"), ("slice", "slice"),
                           ("queued", "queued"), ("state", "state"), ("waiting", "waiting"), ("last", "last line"),
                           ("tokens", "tokens"),
                           ("merged", "merged"), ("marks", "marks")]) or ["  no fairway has written a line"]

    pressure = found["pressure"]
    assert isinstance(pressure, dict)
    bunker = found["bunker"]
    assert isinstance(bunker, dict)
    spent = bunker["spent"]
    said += ["", f"telegraph: {pressure['position']}  boilers {pressure['boilers']}  "
                 f"fanout {pressure['fanout']}  bunker {spent if spent is not None else NOTHING}"
                 f"/{bunker['allowed']}k today"]
    if pressure["banked"]:
        said.append(f"  {pressure['banked']}")

    unreadable = found["unreadable"]
    assert isinstance(unreadable, dict)
    for name, fault in sorted(unreadable.items()):
        if name == "clearance":
            said.append(f"  clearance unavailable ({fault}); waiting counts are unknown")
        else:
            said.append(f"  {name}'s log cannot be read ({fault}); its row is what is left of it")

    feed = found["feed"]
    assert isinstance(feed, list)
    said += ["", "last lines"]
    said += [f"  {when}  {who:<10} {kind}" for when, who, kind in feed[-12:]] or ["  nothing yet"]
    return said


def stream_lines(root: Path, fairway: str, limit: int) -> list[str]:
    """One stream's own log, said. The answer to the question the board always provokes."""
    known = [name for _feature, name in streams(root)]
    if fairway not in known:
        offered = ", ".join(known) or "none"
        return [f"no stream called {fairway} has written a log here; streams: {offered}",
                "a stream is named after its context — `ordering`, not `ORD`"]
    found, fault = recent(root, fairway, limit)
    said = [f"{fairway}: the last {len(found)} line(s) its captain wrote"]
    said += [f"  {when}  {what}" for when, what in found] or ["  nothing yet"]
    if fault:
        said.append(f"  {fault}")
    return said


def fleet_main(argv: list[str]) -> None:
    prog = f"{this_command()} fleet"
    parser = argparse.ArgumentParser(
        prog=prog, description="What every fairway is doing, folded from the logs",
        epilog="`slipwai fleet <stream>` reads that stream's own log, said a line at a time — the question "
               "the board always provokes and cannot answer, because the answer is forty lines of one file. "
               "The board keeps no state: every column is computed from the logs each time it is drawn, "
               "because a board that can be wrong about what happened is worse than no board — it is "
               "believed.")
    parser.add_argument("verb", nargs="?", default="show",
                        help="show, watch, or a stream's name to read its captain's log")
    parser.add_argument("--root", default=".", metavar="<directory>", help="the harbour (default: here)")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between redraws, for watch")
    parser.add_argument("--limit", type=int, default=RECENT, help="lines to show for one stream")
    # The board is one page whatever started it, and this verb is one of its deep links: `--page` opens the
    # board at the fleet rather than printing it, joining the board already serving where there is one.
    parser.add_argument("--page", action="store_true", help="open the board in a browser instead of printing it")
    parsed = parser.parse_args(argv)
    root = Path(parsed.root).expanduser()
    try:
        if not (root / ".slipwai").is_dir() and not (root / CONFIG).is_file():
            raise GenerationError(f"{root} is not a harbour: it has no .slipwai/ and no {CONFIG}. Run this "
                                  f"in a project `slipwai generate` or `slipwai adopt` made")
        if parsed.page:
            start_main(["--root", str(root)], interactive=True)
            return
        if parsed.verb not in ("show", "watch"):
            print("\n".join(stream_lines(root, parsed.verb, parsed.limit)))
            return
        while True:
            print("\n".join(lines(root)))
            if parsed.verb == "show":
                return
            time.sleep(parsed.interval)
            print(CLEAR, end="")
    except GenerationError as error:
        refuse(prog, error)
    except KeyboardInterrupt:
        print()

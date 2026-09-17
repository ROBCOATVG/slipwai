#!/usr/bin/env python3
"""A checkbox menu for `./init`'s extension prompt: arrow keys (or j/k) move, Enter or Space checks the
highlighted row, a letter jumps to the first row starting with it, and a Confirm row at the bottom finishes
with whatever is checked — Enter *checks* rather than confirms because on a single-item list the intuitive
move is to press Enter on the thing you want, and silently adopting nothing would punish exactly that. The
list is framed by a one-line explanation of what an extension is and a key-hint footer, because this prompt
appears unannounced in the middle of `./init` — nothing before it says what is being asked.

Standalone and dependency-free on purpose — this ships inside a generated project, which has no access to
the factory's own `slipwai` package. It is the multi-select sibling of the single-select arrow-key
menu `cli_prompts.py` asks `slipwai generate`'s own fixed-list questions with (same termios/tty raw-mode and
ANSI-redraw technique); the two never share code because they run in different processes with different
questions, one selection each.

Reads the candidate list as JSON from stdin — `[{"key": ..., "name": ..., "description": ...}, ...]` — so
the interactive keys stay free to read the actual keystrokes from `/dev/tty` rather than stdin, which
`./init` may have already redirected by the time this runs. Writes the chosen keys, one per line, to
stdout; writes nothing when there is nothing to choose or no usable terminal, so `./init`'s
`selected_extensions=$(...)` capture is simply empty and everything downstream behaves exactly as if
`--extension` had never been mentioned.
"""
from __future__ import annotations

import json
import shutil
import sys
import textwrap
from select import select as wait_readable

try:
    import termios
    import tty
except ImportError:  # pragma: no cover - Windows
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]


PREAMBLE = (
    "Optional dev tooling — check any to adopt now, or none; "
    "`./init --extension <key>` adds one later just the same."
)
HINTS = "↑/↓ move · Enter or Space checks · Enter on Confirm finishes · Esc skips"


def read_key(tty_in) -> str:
    """One keypress, with an arrow key's escape sequence read whole. A bare Escape is just Escape — a real
    arrow key's remaining bytes arrive in the same burst, so only read on when they are already waiting;
    an unconditional read here would swallow the next two keypresses after a stray Escape."""
    key = tty_in.read(1)
    if key == b"\x1b" and wait_readable([tty_in], [], [], 0.05)[0]:
        key += tty_in.read(2)
    return key.decode(errors="replace")


def select(options: list[dict], tty_in, tty_out) -> list[str]:
    assert termios is not None and tty is not None
    index = 0
    checked = [False] * len(options)
    confirm = len(options)  # the Confirm row sits one past the last option
    width = max(shutil.get_terminal_size().columns, 40)

    def rows() -> list[str]:
        lines: list[str] = [f"  {line}" for line in textwrap.wrap(PREAMBLE, width - 4)]
        lines.append("")
        for i, option in enumerate(options):
            text = f"{option['name']} — {option['description']}"
            wrapped = textwrap.wrap(text, width - 8) or [text]
            cursor = "❯" if i == index else " "
            box = "[x]" if checked[i] else "[ ]"
            lines.append(f"  {cursor} {box} {wrapped[0]}")
            lines += [f"        {line}" for line in wrapped[1:]]
        lines.append("")
        lines.append(f"  {'❯' if index == confirm else ' '} [ Confirm ]")
        lines += ["", f"  {HINTS}"]
        return lines

    drawn = rows()
    tty_out.write("\x1b[?25l")  # hide the cursor while the list is live
    tty_out.write("\n".join(drawn) + "\n")
    tty_out.flush()
    settings = termios.tcgetattr(tty_in.fileno())
    try:
        # TCSANOW, not setcbreak's default TCSAFLUSH: a key pressed while the list is being drawn is an
        # answer, not noise to discard.
        tty.setcbreak(tty_in.fileno(), termios.TCSANOW)
        while True:
            key = read_key(tty_in)
            if key in ("\r", "\n", " ") and index == confirm:
                break
            if key in ("\x03", "\x1b"):
                checked = [False] * len(options)
                break
            if key in ("\x1b[A", "k"):
                index = (index - 1) % (confirm + 1)
            elif key in ("\x1b[B", "j"):
                index = (index + 1) % (confirm + 1)
            elif key in ("\r", "\n", " "):
                checked[index] = not checked[index]
            elif key.isalnum():
                match = next(
                    (i for i, option in enumerate(options) if option["key"].startswith(key.lower())), None
                )
                if match is None:
                    continue
                index = match
            else:
                continue
            tty_out.write(f"\x1b[{len(drawn)}A\x1b[J")
            drawn = rows()
            tty_out.write("\n".join(drawn) + "\n")
            tty_out.flush()
    finally:
        termios.tcsetattr(tty_in.fileno(), termios.TCSADRAIN, settings)
        tty_out.write("\x1b[?25h")
    chosen = [option["key"] for option, is_checked in zip(options, checked) if is_checked]
    summary = ", ".join(chosen) if chosen else "none"
    tty_out.write(f"\x1b[{len(drawn)}A\x1b[JExtensions: {summary}\n")
    tty_out.flush()
    return chosen


def main() -> int:
    options = json.load(sys.stdin)
    if not options:
        return 0
    if termios is None:
        return 0
    try:
        # Two separate handles, not one opened "r+": a combined read/write TextIOWrapper on a tty tries to
        # confirm it can seek and raises UnsupportedOperation immediately, since a tty cannot. Read-only and
        # write-only each avoid that check. Input is binary and unbuffered so `read_key`'s select() sees the
        # truth — a text layer's readahead would hold an arrow key's tail bytes where select cannot see them.
        tty_in = open("/dev/tty", "rb", buffering=0)
        tty_out = open("/dev/tty", "w", buffering=1)
    except OSError:
        # No controlling terminal — the same silent, exit-0 skip every other `./init` prompt falls back to.
        return 0
    try:
        chosen = select(options, tty_in, tty_out)
    finally:
        tty_in.close()
        tty_out.close()
    for key in chosen:
        print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

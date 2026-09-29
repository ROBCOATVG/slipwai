"""Answer `slipwai generate` in a real terminal (a pty) the way a person does.

Enter at every question, `c` at the coding-agent question (Claude Code), Escape at the extension menu; then print
the transcript's key lines. Used by `macos-like.zsh`, so it runs on the container's Python 3.9.
"""
import contextlib
import os
import pty
import re
import select
import sys
import time

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
SHOWN = ("Project name [", "Which coding agent", "Coding agent:", "Output parent", "install-tools:", "created:",
         "Choose your coding agent", "Choose script type", "./init is done", "Start your coding agent", "Could not",
         "Not running")


def drive(command: list) -> str:
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(command[0], command)
    log = b""
    pending = b""
    answered_agent = skipped_extensions = False
    deadline = time.time() + 1500
    while time.time() < deadline:
        ready, _, _ = select.select([fd], [], [], 30)
        if not ready:
            os.write(fd, b"\r")
            continue
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        log += chunk
        pending += chunk
        raw = pending.decode(errors="replace")
        text = ANSI.sub("", raw)
        if not answered_agent and "Which coding agent" in text:
            time.sleep(0.5)
            os.write(fd, b"c")
            time.sleep(0.3)
            os.write(fd, b"\r")
            answered_agent, pending = True, b""
        elif not skipped_extensions and "Optional dev tooling" in text:
            time.sleep(0.5)
            os.write(fd, b"\x1b")
            skipped_extensions, pending = True, b""
        elif text.endswith(": ") or "\x1b[?25l" in raw:
            time.sleep(0.2)
            os.write(fd, b"\r")
            pending = b""
    with contextlib.suppress(ChildProcessError):
        os.waitpid(pid, 0)
    return ANSI.sub("", log.decode(errors="replace")).replace("\r", "")


if __name__ == "__main__":
    transcript = drive(sys.argv[1:] or ["slipwai", "generate"])
    for pattern in SHOWN:
        line = next((line for line in transcript.splitlines() if pattern in line), None)
        if line is not None:
            print("  |", line.strip()[:150])

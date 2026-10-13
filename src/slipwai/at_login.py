"""The board as something that is simply running: a login service, so the installed window is never empty.

An installed page cannot start a server. A browser will not let one, and nothing about that is going to
change — so the window opens on `not-running.html` whenever nobody has typed the command, which is honest
and is still a window that does not work. The other end of the same problem is the one that can be solved:
the board is a loopback server with no state of its own, and this machine can simply keep it up.

One shape per platform and nothing clever about any of them: a launchd agent, a systemd user unit, or a
file in the Startup folder. Each is a file in the person's own account — no root, no daemon, no installer —
each names the exact copy of slipwai that wrote it (`relaunch`), and each is removed by the verb that wrote
it. Nothing here is loaded at import time or runs on its own: `slipwai bridge --at-login` is the only way in.

**Which directory it serves is barely a question now.** The board attaches from its own page, so the one
written here is where it starts rather than where it is stuck.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from .assets import relaunch
from .cli_start import running

#: One name for the service on all three platforms, in the reverse-domain form launchd wants and the other
#: two do not mind. A second board under a second label is the failure this prevents.
LABEL = "ai.slipwai.board"
#: Where a service that nobody is watching writes what it says. Beside the packages, which is the one
#: directory this keel already owns in a person's home.
LOG = Path(".slipwai/board.log")

#: A step this runs that is allowed to fail. `bootout` before `bootstrap` is how launchd is told to replace
#: an agent, and it is an error when there was nothing to replace — which is the ordinary first install.
MAY_FAIL = "may-fail"


@dataclass(frozen=True)
class Service:
    """What this platform's login service is, as a file and the commands that load and unload it."""

    kind: str
    path: Path
    text: str
    load: tuple[tuple[str, ...], ...] = ()
    unload: tuple[tuple[str, ...], ...] = ()
    #: Said after a successful install where the platform has no command to start it now.
    at_next: str = ""


def argv(root: Path, host: str, port: int) -> list[str]:
    """What the service runs: this copy of slipwai, serving and opening nothing.

    `relaunch` rather than `slipwai` off the PATH, because a service is started by the system with an
    environment nobody chose — and because the copy that wrote the file is the copy somebody meant.
    """
    return [*relaunch(), "bridge", "--serve", "--root", str(root), "--host", host, "--port", str(port)]


def launchd(line: Sequence[str], home: Path) -> Service:
    """macOS: a per-user agent in `~/Library/LaunchAgents`, kept alive and started at login."""
    log = home / LOG
    arguments = "".join(f"    <string>{xml_escape(one)}</string>\n" for one in line)
    uid = os.getuid() if hasattr(os, "getuid") else 0  # pragma: no cover — POSIX is where this is read
    return Service(
        "a launchd agent",
        home / f"Library/LaunchAgents/{LABEL}.plist",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>Label</key><string>{LABEL}</string>\n"
        f"  <key>ProgramArguments</key><array>\n{arguments}  </array>\n"
        "  <key>RunAtLoad</key><true/>\n"
        # Restarted when it falls over, and not when it ends cleanly — which it does when it finds a board
        # already serving. `KeepAlive: true` would have launchd start a second one every ten seconds for as
        # long as the first one was up.
        "  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>\n"
        f"  <key>StandardOutPath</key><string>{xml_escape(str(log))}</string>\n"
        f"  <key>StandardErrorPath</key><string>{xml_escape(str(log))}</string>\n"
        "</dict></plist>\n",
        load=(("launchctl", "bootout", f"gui/{uid}/{LABEL}", MAY_FAIL),
              ("launchctl", "bootstrap", f"gui/{uid}", str(home / f"Library/LaunchAgents/{LABEL}.plist"))),
        unload=(("launchctl", "bootout", f"gui/{uid}/{LABEL}", MAY_FAIL),),
    )


def systemd(line: Sequence[str], home: Path) -> Service:
    """Linux: a user unit, enabled and started in one go, restarted if it ever stops."""
    runs = " ".join(_quoted(one) for one in line)
    return Service(
        "a systemd user unit",
        home / f".config/systemd/user/{LABEL}.service",
        "[Unit]\n"
        "Description=slipwai — the board\n\n"
        "[Service]\n"
        f"ExecStart={runs}\n"
        # on-failure, not always: ending cleanly is what it does when a board is already serving, and
        # restarting that is a second board every two seconds for as long as the first one is up.
        "Restart=on-failure\n"
        "RestartSec=2\n\n"
        "[Install]\n"
        "WantedBy=default.target\n",
        load=(("systemctl", "--user", "daemon-reload"),
              ("systemctl", "--user", "enable", "--now", f"{LABEL}.service")),
        unload=(("systemctl", "--user", "disable", "--now", f"{LABEL}.service", MAY_FAIL),
                ("systemctl", "--user", "daemon-reload")),
    )


def startup(line: Sequence[str], home: Path) -> Service:
    """Windows: a shortcut in the Startup folder, which needs no service manager and no administrator."""
    return Service(
        "a file in the Startup folder",
        home / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/slipwai-board.cmd",
        "@echo off\r\n"
        f'start "" /b {subprocess.list2cmdline(list(line))}\r\n',
        at_next="It starts at your next sign-in; until then, the command above is what runs it.",
    )


def _quoted(one: str) -> str:
    """One argument of an `ExecStart`, which is a line systemd splits on spaces unless it is quoted."""
    return f'"{one}"' if " " in one or '"' in one else one


def service(root: Path, host: str = "127.0.0.1", port: int = 8099, home: Path | None = None) -> Service:
    """This platform's login service for that root, built and not written."""
    where = Path.home() if home is None else home
    line = argv(root.resolve(), host, port)
    if sys.platform == "darwin":
        return launchd(line, where)
    if sys.platform == "win32":  # pragma: no cover — read on the platform it is for
        return startup(line, where)
    return systemd(line, where)


def ran(steps: Sequence[Sequence[str]], run: Callable[..., subprocess.CompletedProcess]) -> list[str]:
    """Each step in turn, the ones marked `may-fail` allowed to. What went wrong, where anything did."""
    said = []
    for step in steps:
        allowed = step[-1] == MAY_FAIL
        done = run([*step[:-1]] if allowed else list(step), capture_output=True, text=True, check=False)
        if done.returncode and not allowed:
            said.append(f"`{' '.join(step)}` exited {done.returncode}: "
                        f"{(done.stderr or done.stdout or '').strip() or 'no reason given'}")
    return said


def install(root: Path, host: str = "127.0.0.1", port: int = 8099, home: Path | None = None,
            run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> list[str]:
    """Write this platform's service and load it. The lines to print, including anything that went wrong."""
    one = service(root, host, port, home)
    one.path.parent.mkdir(parents=True, exist_ok=True)
    one.path.write_text(one.text, encoding="utf-8")
    wrong = ran(one.load, run)
    said = [f"The board starts with you now: {one.kind} at {one.path}.",
            f"It serves http://{host}:{port}/ from {root.resolve()}, and the page itself attaches "
            f"anywhere else. `slipwai bridge --no-at-login` undoes this."]
    if one.at_next:
        said.append(one.at_next)
    # One board, one port — which the service obeys like every other way in: finding one already there, it
    # ends rather than binding a rival, and then nothing restarts it until the next login. Said now, because
    # the alternative is a person who installed this, stopped their own board an hour later, and found the
    # window empty with nothing to tell them why.
    if running(host, port):
        said.append(f"Something is already serving http://{host}:{port}/ — your own `slipwai`, most likely. "
                    f"The service will not start a rival: stop that one and run this again, or it takes the "
                    f"port at your next login.")
    return said + wrong


def remove(home: Path | None = None,
           run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> list[str]:
    """Unload this platform's service and delete it. Saying so either way, because a person who ran this
    wants to know the board will not come back, not whether there was a file to delete."""
    one = service(Path.cwd(), home=home)
    wrong = ran(one.unload, run)
    one.path.unlink(missing_ok=True)
    return [f"The board no longer starts with you: {one.path} is gone. "
            f"Whatever is serving now keeps serving until it is stopped."] + wrong

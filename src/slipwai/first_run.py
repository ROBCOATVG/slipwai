"""The app's first launch, and every launch after: place it, keep the board running, open it.

A person who downloaded the app and opened it should see the board and nothing else to do. Three steps make
that true, and each is skipped where it is already done:

1. **Place.** The login service runs whichever copy wrote it (`at_login.argv`), so it is written only from
   a copy that will still be there tomorrow. On macOS that is an Applications folder: an app opened from
   Downloads runs from a randomised, read-only App Translocation path that is gone after a reboot, so the
   app asks — in the system's own dialog — to move itself, and copies itself there with `ditto`. On
   Windows it is `%LOCALAPPDATA%\\Programs\\slipwai\\`, with a Start-menu shortcut; nothing there needs
   asking, and nothing needs an administrator. Then the placed copy is started and this one ends.
2. **Register.** `at_login.install` from the placed copy, so the board starts with the person from now on.
   Where a service already exists and names another copy — an older download, a moved app — it is
   rewritten; where it names this one, it is left alone.
3. **Open.** The board, on the home folder, in the default browser.

A person who declines the move gets the board anyway, served by this process for as long as it runs, and
nothing registered: a service pointing at a path that will vanish is worse than none.

Nothing here runs for the command line. `app.main` calls it only for the app opened with no arguments.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path

from . import at_login, tool_install
from .cli_start import HOST, PORT, open_board, running
from .shell_environment import TOOLS, login_environment

#: The question the move is asked with, in the dialog's own words.
MOVE = "Move slipwai to your Applications folder? It keeps the board running from there."


def bundle(executable: Path | None = None) -> Path | None:
    """The `.app` this executable is inside, on macOS; `None` where it is not in one."""
    here = (Path(sys.executable) if executable is None else executable).resolve()
    return next((one for one in here.parents if one.suffix == ".app"), None)


def translocated(path: Path) -> bool:
    """Whether macOS is running this copy from its randomised App Translocation path."""
    return "/AppTranslocation/" in str(path)


def programs(environ: dict[str, str] | None = None) -> Path:
    """Where the app places itself on Windows: the per-user programs folder, no administrator needed."""
    held = os.environ if environ is None else environ
    return Path(held.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "Programs/slipwai"


def placed(executable: Path | None = None, system: str | None = None, home: Path | None = None,
           environ: dict[str, str] | None = None) -> bool:
    """Whether this copy is somewhere a login service may name."""
    system = system or sys.platform
    here = (Path(sys.executable) if executable is None else executable).resolve()
    if system == "darwin":
        app = bundle(here)
        if app is None or translocated(app):
            return False
        homes = (Path("/Applications"), ((Path.home() if home is None else home) / "Applications").resolve())
        return app.parent in homes
    if system == "win32":
        return here.parent == programs(environ).resolve()
    return True


def ask_move(run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> bool:
    """Ask in the system's own dialog; `True` only for the Move button."""
    script = (f'button returned of (display dialog "{MOVE}" buttons {{"Not now", "Move"}} '
              f'default button "Move" with title "slipwai")')
    try:
        done = run(["osascript", "-e", script], capture_output=True, text=True, timeout=600, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0 and done.stdout.strip() == "Move"


def move_app(app: Path, home: Path | None = None,
             run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> Path:
    """Copy the bundle into `/Applications`, or `~/Applications` where that cannot be written. `ditto`, because
    it keeps the signature and the bundle's extended attributes whole where a plain copy would not."""
    system_wide = Path("/Applications")
    own = (Path.home() if home is None else home) / "Applications"
    folder = system_wide if os.access(system_wide, os.W_OK) else own
    folder.mkdir(parents=True, exist_ok=True)
    where = folder / app.name
    if where.exists():
        shutil.rmtree(where)
    run(["ditto", str(app), str(where)], check=True, capture_output=True)
    return where


def place_windows(executable: Path, environ: dict[str, str] | None = None,
                  run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> Path:
    """Copy the executable into the per-user programs folder and put a shortcut in the Start menu."""
    folder = programs(environ)
    folder.mkdir(parents=True, exist_ok=True)
    where = folder / executable.name
    shutil.copy2(executable, where)
    held = os.environ if environ is None else environ
    menu = Path(held.get("APPDATA") or Path.home() / "AppData/Roaming") / "Microsoft/Windows/Start Menu/Programs"
    link = menu / "slipwai.lnk"
    script = (f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{link}'); "
              f"$s.TargetPath = '{where}'; $s.Save()")
    run(["powershell", "-NoProfile", "-Command", script], capture_output=True, check=False)
    return where


def start_copy(where: Path, system: str | None = None) -> list[str]:
    """The command that opens the placed copy as the person would: `open` for a bundle, the file itself on
    Windows."""
    if (system or sys.platform) == "darwin":
        return ["open", "-n", str(where)]
    return [str(where)]


def register(root: Path, home: Path | None = None,
             install: Callable[..., list[str]] = at_login.install) -> list[str]:
    """Write the login service, unless the one there already names this copy. The lines `install` said."""
    wanted = at_login.service(root, HOST, PORT, home)
    try:
        if wanted.path.read_bytes() == wanted.text.encode("utf-8"):  # as written, line endings and all
            return []
    except OSError:
        pass
    return install(root, HOST, PORT, home)


def link_command(executable: Path | None = None, tools: Path | None = None, path: str | None = None,
                 system: str | None = None) -> Path | None:
    """`slipwai` for the board's children, pointing at this copy, where the machine has no `slipwai` of its own.

    The agents' prompts tell them to run `slipwai adopt --next`, `slipwai describe-service` and the rest, and a
    person who only ever opened the app has no command on any `PATH`. So it is linked under the board's tools,
    which `shell_environment` puts on the end of a child's `PATH`; a `slipwai` the person installed is found
    first and this link is never made. The link is refreshed each launch, so it follows a moved app.
    """
    system = system or sys.platform
    here = (Path(sys.executable) if executable is None else executable).resolve()
    home = (TOOLS if tools is None else tools) / "slipwai"
    folder = home / "bin"
    path = login_environment().get("PATH", "") if path is None else path
    theirs = shutil.which("slipwai", path=path)
    if theirs and Path(theirs).parent.resolve() != folder.resolve():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    # A wrapper, not a symlink: a frozen bundle finds its files from its own path. On Windows a `.cmd` too,
    # for PowerShell and cmd; the wrapper is the one Git's bash, where a project's recipes run, can start.
    if system == "win32":
        (folder / "slipwai.cmd").write_text(f'@"{here}" %*\r\n', encoding="utf-8")
    link = folder / "slipwai"
    link.write_text(f'#!/bin/sh\nexec "{here.as_posix()}" "$@"\n', encoding="utf-8", newline="\n")
    link.chmod(0o755)
    (home / "tool.json").write_text(json.dumps({"bin": str(folder), "version": "", "at": str(here)}) + "\n",
                                    encoding="utf-8")
    return link


def wait_for_board(seconds: float = 15.0, up: Callable[[], bool] = running,
                   pause: Callable[[float], None] = time.sleep) -> bool:
    """Whether the board answered within `seconds` of its service being loaded."""
    for _ in range(int(seconds * 2)):
        if up():
            return True
        pause(0.5)
    return up()


def serve_here(root: Path, open_page: Callable[[str], object] = webbrowser.open) -> None:
    """The board served by this process, as bare `slipwai` does: for as long as the app runs."""
    server = open_board(root, open_page=open_page)
    if server is None:
        return
    try:
        server.serve_forever()
    finally:
        server.server_close()


def start(home: Path | None = None, system: str | None = None,
          open_page: Callable[[str], object] = webbrowser.open,
          run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> str:
    """The whole launch. Says which way it went — `moved`, `here`, `registered` or `opened` — for the suite."""
    system = system or sys.platform
    root = Path.home() if home is None else home
    if not placed(system=system, home=home):
        if system == "darwin":
            app = bundle()
            if app is None or not ask_move(run):
                serve_here(root, open_page)
                return "here"
            where = move_app(app, home, run)
        else:
            where = place_windows(Path(sys.executable).resolve(), run=run)
        subprocess.Popen(start_copy(where, system))  # noqa: S603 — the copy just placed
        return "moved"
    link_command()
    tool_install.windows_shims()
    said = register(root, home)
    if running() or wait_for_board():
        open_page(f"http://{HOST}:{PORT}/")
        return "registered" if said else "opened"
    serve_here(root, open_page)
    return "here"

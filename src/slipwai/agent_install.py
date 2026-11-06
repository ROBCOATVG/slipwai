"""Installing an agent from the settings page: the registry's archive for this platform, fetched, checked and
unpacked under the board's own folder.

The protocol registry's manifest for an agent distributed as a binary names, per platform, an archive, the
command inside it and — for most — its sha256. The board installs only where the sha256 is given: a
download nobody can check is a download the page shows the link for and leaves to the person. What is
installed lives under `~/.slipwai/agents/<key>/`, never on PATH, and `harness.acp_launch` finds it there
when the agent's own command is not on the machine. Nothing is run during an install; *Make ready* is
the first start, and the handshake is its proof.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import stat
import tarfile
import threading
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assets import SLIPWAI
from .board_settings import read, write
from .harness import acp_row, name_of

#: Where an installed agent lives: its archive, what it unpacked to, and `launch.json` saying what to run.
HOME = SLIPWAI / "agents"
LAUNCH = "launch.json"
#: The registry's platform targets, from this machine's own words for itself.
SYSTEMS = {"darwin": "darwin", "linux": "linux", "windows": "windows"}
MACHINES = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x86_64", "amd64": "x86_64"}


def target() -> str:
    """This machine as the registry names platforms: `darwin-aarch64`, `linux-x86_64`, …; empty where it
    is not one the registry knows."""
    system = SYSTEMS.get(platform.system().lower(), "")
    machine = MACHINES.get(platform.machine().lower(), "")
    return f"{system}-{machine}" if system and machine else ""


def archive_for(key: str, here: str | None = None) -> dict[str, Any] | None:
    """The registry's archive for this agent on this platform, or `None` where the manifest has none."""
    row = acp_row(key) or {}
    found = (row.get("archive") or {}).get(target() if here is None else here)
    return dict(found) if isinstance(found, dict) else None


def installed(key: str, home: Path | None = None) -> dict[str, Any] | None:
    """What the board installed for this agent — `cmd`, `args`, `version`, `at` — or `None`."""
    try:
        held = json.loads(((HOME if home is None else home) / key / LAUNCH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return held if isinstance(held, dict) and Path(str(held.get("cmd") or "")).is_file() else None


class Installing:
    """One install on a thread of its own, said as lines for the page to poll."""

    def __init__(self, key: str, archive: dict[str, Any], home: Path | None = None,
                 settings_path: Path | None = None) -> None:
        self.key, self.archive = key, archive
        self.home = (HOME if home is None else home) / key
        self.settings_path = settings_path
        self.lines: list[str] = []
        self.done = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def say(self, line: str) -> None:
        with self.lock:
            self.lines.append(line)

    def run(self) -> None:
        record: dict[str, Any] = {"at": datetime.now(UTC).strftime("%Y-%m-%d"), "fault": "",
                                  "version": str((acp_row(self.key) or {}).get("version") or "")}
        try:
            file = self.fetch()
            self.check(file)
            launch = self.unpack(file)
            record["cmd"] = launch["cmd"]
            self.say(f"Installed: {launch['cmd']}")
        except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as fault:
            record["fault"] = str(fault)
            self.say(f"! {fault}")
        finally:
            settings = read(self.settings_path)
            settings.ready[self.key] = {**settings.ready.get(self.key, {}), "install": record}
            write(settings, self.settings_path)
            with self.lock:
                self.done = True

    def fetch(self) -> Path:
        url = str(self.archive["url"])
        name = url.rsplit("/", 1)[-1] or "archive"
        self.home.mkdir(parents=True, exist_ok=True)
        file = self.home / name
        self.say(f"Fetching {url}")
        with urllib.request.urlopen(url, timeout=120) as reading, file.open("wb") as writing:  # noqa: S310 — the registry's URL
            shutil.copyfileobj(reading, writing)
        self.say(f"Fetched {file.stat().st_size:,} bytes.")
        return file

    def check(self, file: Path) -> None:
        wanted = str(self.archive.get("sha256") or "").lower()
        if not wanted:
            raise ValueError("the registry's manifest gives no sha256 for this platform, so the archive cannot be "
                             "checked and was not unpacked")
        digest = hashlib.sha256()
        with file.open("rb") as reading:
            for chunk in iter(lambda: reading.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != wanted:
            file.unlink(missing_ok=True)
            raise ValueError(f"the archive's sha256 is {digest.hexdigest()[:12]}…, not the {wanted[:12]}… the registry "
                             f"gives; it was thrown away")
        self.say("Checksum matches the registry's.")

    def unpack(self, file: Path) -> dict[str, Any]:
        place = self.home / "unpacked"
        shutil.rmtree(place, ignore_errors=True)
        place.mkdir(parents=True)
        name = file.name.lower()
        if name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar")):
            with tarfile.open(file) as held:
                for member in held.getmembers():
                    if member.name.startswith("/") or ".." in Path(member.name).parts:
                        raise ValueError(f"the archive reaches outside itself ({member.name}); not unpacked")
                try:
                    held.extractall(place, filter="data")
                except TypeError:  # pragma: no cover — a Python before the filter; the names were checked above
                    held.extractall(place)
        elif name.endswith(".zip"):
            with zipfile.ZipFile(file) as held:
                for entry in held.namelist():
                    if entry.startswith("/") or ".." in Path(entry).parts:
                        raise ValueError(f"the archive reaches outside itself ({entry}); not unpacked")
                held.extractall(place)
        else:  # a raw binary: the file itself is the command
            shutil.copy(file, place / Path(str(self.archive["cmd"])).name)
        command = place / str(self.archive["cmd"]).replace("\\", "/").removeprefix("./")
        if not command.is_file():
            raise ValueError(f"the archive holds no {self.archive['cmd']}; not installed")
        command.chmod(command.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        launch = {"cmd": str(command), "args": [str(a) for a in self.archive.get("args") or []],
                  "version": str((acp_row(self.key) or {}).get("version") or ""),
                  "at": datetime.now(UTC).strftime("%Y-%m-%d")}
        (self.home / LAUNCH).write_text(json.dumps(launch, indent=2) + "\n", encoding="utf-8")
        self.say(f"Unpacked to {place}.")
        return launch

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {"key": self.key, "lines": list(self.lines), "done": self.done}


RUNNING: dict[str, Installing] = {}


def begin(key: str, home: Path | None = None, settings_path: Path | None = None) -> Installing | str:
    """Start an install, or say why not: no row, no archive for this platform, no checksum, or one running."""
    if not acp_row(key):
        return f"{key} is not a harness the registry can launch"
    archive = archive_for(key)
    if archive is None:
        return f"{name_of(key)} has no archive for this machine ({target() or 'an unknown platform'}) in the registry"
    if not archive.get("sha256"):
        return (f"{name_of(key)}'s manifest gives no checksum for this platform, so the board will not fetch it; "
                f"install it yourself from {archive['url']}")
    held = RUNNING.get(key)
    if held is not None and not held.state()["done"]:
        return f"{name_of(key)} is being installed now"
    installing = Installing(key, archive, home, settings_path)
    RUNNING[key] = installing
    installing.thread.start()
    return installing


def state(key: str) -> dict[str, Any]:
    held = RUNNING.get(key)
    return held.state() if held is not None else {"key": key, "lines": [], "done": True}

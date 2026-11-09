"""Installing a tool from the board, where the machine has no copy of it or only one too old.

A good copy the person installed is theirs, and the board never fetches a second one beside it: `begin`
refuses where `prerequisites.found` finds one. Where there is none, or only one older than the tool's floor —
a Mac's own `python3` is 3.9 — the tool comes from its own publisher, is checked against the checksum that
publisher gives, and is unpacked under `~/.slipwai/tools/<key>/`, with `tool.json` naming its `bin`
directory for `shell_environment` to put on the board's children's `PATH`. A copy installed because the
machine had none goes on the end; one installed over an old copy goes first, or the old one would still be
the one found. The old copy itself, the system `PATH` and the shell profile are never touched.

Where each comes from:

- **Node**, on every platform: the newest LTS in `nodejs.org/dist/index.json`, its archive for this
  platform, checked against that release's `SHASUMS256.txt`.
- **Git on Windows**: MinGit from Git for Windows' latest release, checked against the sha256 GitHub
  records for the asset.
- **Git on macOS**: Apple's own installer for the command line developer tools, opened with
  `xcode-select --install`. The board downloads nothing; the dialog is the system's.
- **Make on macOS**: the same developer tools, the same dialog.
- **Python** on macOS and Linux: python-build-standalone's newest 3.13 `install_only` build for this
  platform, checked against the sha256 GitHub records for the asset. Not Apple's developer tools: the
  `python3` they carry is 3.9, older than a project's scripts need.
- **Git, Make on Linux**, and **uv, Go, Java** anywhere: nothing to fetch that would work everywhere, so the
  card links to the publisher.
"""
from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import threading
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent_install import checked, fetched, unpacked
from .prerequisites import BY_KEY, found
from .shell_environment import TOOLS

NODE_INDEX = "https://nodejs.org/dist/index.json"
NODE_DIST = "https://nodejs.org/dist"
MINGIT = "https://api.github.com/repos/git-for-windows/git/releases/latest"
STANDALONE = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
#: This machine as python-build-standalone names its builds.
TRIPLES = {("darwin", "arm64"): "aarch64-apple-darwin", ("darwin", "x86_64"): "x86_64-apple-darwin",
           ("linux", "x86_64"): "x86_64-unknown-linux-gnu", ("linux", "aarch64"): "aarch64-unknown-linux-gnu"}
#: This machine's processor, in each publisher's words.
NODE_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}
MINGIT_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "64-bit", "amd64": "64-bit"}


def machine() -> str:
    return platform.machine().lower()


def read_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=60) as answer:  # noqa: S310 — a publisher's fixed URL
        return json.loads(answer.read().decode("utf-8"))


def read_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as answer:  # noqa: S310 — a publisher's fixed URL
        return answer.read().decode("utf-8")


def node_archive(index: list[dict[str, Any]], sums: str | None = None, system: str | None = None,
                 arch: str | None = None) -> dict[str, str]:
    """The newest LTS's archive for this platform: `url`, `sha256`, `version`, and `bin` inside the unpacked
    tree. `sums` is that release's SHASUMS256.txt, fetched here where not given."""
    system = system or sys.platform
    arch = arch or NODE_ARCH.get(machine(), "")
    lts = next((one for one in index if one.get("lts")), None)
    if lts is None or not arch:
        raise ValueError("nodejs.org lists no LTS release for this machine")
    version = str(lts["version"])
    if system == "win32":
        stem, suffix, inside = f"node-{version}-win-{arch}", ".zip", ""
    elif system == "darwin":
        stem, suffix, inside = f"node-{version}-darwin-{arch}", ".tar.gz", "/bin"
    else:
        stem, suffix, inside = f"node-{version}-linux-{arch}", ".tar.xz", "/bin"
    sums = read_text(f"{NODE_DIST}/{version}/SHASUMS256.txt") if sums is None else sums
    wanted = next((line.split()[0] for line in sums.splitlines() if line.endswith(f"  {stem}{suffix}")), "")
    if not wanted:
        raise ValueError(f"nodejs.org's SHASUMS256.txt for {version} has no line for {stem}{suffix}")
    return {"url": f"{NODE_DIST}/{version}/{stem}{suffix}", "sha256": wanted, "version": version.lstrip("v"),
            "bin": stem + inside}


def mingit_archive(release: dict[str, Any], arch: str | None = None) -> dict[str, str]:
    """MinGit for this processor from Git for Windows' latest release, with the sha256 GitHub records."""
    arch = arch or MINGIT_ARCH.get(machine(), "")
    def fits(name: str) -> bool:
        return name.startswith("MinGit-") and name.endswith(f"-{arch}.zip") and "busybox" not in name

    asset = next((one for one in release.get("assets") or [] if fits(str(one.get("name", "")))), None)
    if asset is None:
        raise ValueError(f"Git for Windows' latest release has no MinGit for {arch or 'this processor'}")
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:"):
        raise ValueError("GitHub records no sha256 for MinGit, so it cannot be checked and was not fetched; install "
                         "Git from https://git-scm.com/downloads")
    return {"url": str(asset["browser_download_url"]), "sha256": digest.removeprefix("sha256:"),
            "version": str(release.get("tag_name") or "").lstrip("v"), "bin": "cmd"}


def python_archive(release: dict[str, Any], triple: str | None = None) -> dict[str, str]:
    """The newest CPython 3.13 `install_only` build for this machine, with the sha256 GitHub records."""
    triple = triple or TRIPLES.get((sys.platform, machine()), "")
    pattern = re.compile(rf"cpython-(3\.13\.\d+)\+\d+-{re.escape(triple)}-install_only\.tar\.gz")
    hits: list[tuple[re.Match[str], dict[str, Any]]] = []
    for one in release.get("assets") or []:
        if hit := pattern.fullmatch(str(one.get("name", ""))):
            hits.append((hit, one))
    if not triple or not hits:
        raise ValueError("python-build-standalone's latest release has no Python 3.13 for this machine")
    hit, asset = max(hits, key=lambda pair: tuple(int(n) for n in pair[0].group(1).split(".")))
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:"):
        raise ValueError("GitHub records no sha256 for that build, so it cannot be checked and was not fetched; "
                         "install Python from https://www.python.org/downloads/")
    return {"url": str(asset["browser_download_url"]), "sha256": digest.removeprefix("sha256:"),
            "version": hit.group(1), "bin": "python/bin"}


def way(key: str) -> str:
    """How the board puts `key` on this machine: `archive`, `apple` (the system's own installer), or `""`."""
    if key == "node":
        return "archive" if NODE_ARCH.get(machine()) else ""
    if key == "git":
        return {"win32": "archive" if MINGIT_ARCH.get(machine()) else "", "darwin": "apple"}.get(sys.platform, "")
    if key == "make":
        return "apple" if sys.platform == "darwin" else ""
    if key == "python3":
        return "archive" if (sys.platform, machine()) in TRIPLES else ""
    return ""


class Installing:
    """One tool's install on a thread of its own, said as lines for the page to poll."""

    def __init__(self, key: str, home: Path | None = None, first: bool = False) -> None:
        self.key, self.first = key, first
        self.home = (TOOLS if home is None else home) / key
        self.lines: list[str] = []
        self.done = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def say(self, line: str) -> None:
        with self.lock:
            self.lines.append(line)

    def archive(self) -> dict[str, str]:
        if self.key == "node":
            return node_archive(read_json(NODE_INDEX))
        if self.key == "python3":
            return python_archive(read_json(STANDALONE))
        return mingit_archive(read_json(MINGIT))

    def run(self) -> None:
        try:
            archive = self.archive()
            file = fetched(archive["url"], self.home, self.say)
            checked(file, archive["sha256"], "the publisher", self.say)
            place = unpacked(file, self.home / "unpacked")
            file.unlink(missing_ok=True)
            where = place / archive["bin"]
            if not where.is_dir():
                raise ValueError(f"the archive holds no {archive['bin']}; not installed")
            record = {"bin": str(where), "version": archive["version"], "at": datetime.now(UTC).strftime("%Y-%m-%d"),
                      "first": self.first}
            (self.home / "tool.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            self.say(f"Installed {BY_KEY[self.key].name} {archive['version']} in {where}.")
        except (OSError, ValueError, KeyError) as fault:
            self.say(f"! {fault}")
        finally:
            with self.lock:
                self.done = True

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {"key": self.key, "lines": list(self.lines), "done": self.done}


class Opened(str):
    """Not a refusal: the system's own installer was opened, and the rest is the person's."""


RUNNING: dict[str, Installing] = {}


def begin(key: str, home: Path | None = None, look=found,
          run=subprocess.run) -> Installing | str:
    """Start an install, or say why not — above all, that the machine already has the tool."""
    tool = BY_KEY.get(key)
    if tool is None:
        return f"{key} is not a tool the board installs"
    have = look(tool)
    if have.state == "found":
        return (f"{tool.name} {have.version} is already on this machine at {have.where}. The board installs only "
                f"where there is none, or only one too old.")
    how = way(key)
    if how == "apple":
        try:
            run(["xcode-select", "--install"], capture_output=True, timeout=30, check=False)
        except (OSError, subprocess.SubprocessError) as fault:
            return f"Apple's installer would not open ({fault}); install {tool.name} from {tool.page}"
        return Opened("Apple's installer for the command line developer tools is open: press Install there, "
                      "then come back to this page.")
    if not how:
        return f"The board cannot install {tool.name} on this machine; install it from {tool.page}"
    held = RUNNING.get(key)
    if held is not None and not held.state()["done"]:
        return f"{tool.name} is being installed now"
    installing = Installing(key, home, first=have.state == "old")
    RUNNING[key] = installing
    installing.thread.start()
    return installing


def state(key: str) -> dict[str, Any]:
    held = RUNNING.get(key)
    return held.state() if held is not None else {"key": key, "lines": [], "done": True}

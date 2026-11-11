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
- **Git on Windows**: PortableGit from Git for Windows' latest release, checked against the sha256 GitHub
  records for the asset and unpacked by running it, silently, into the board's tools. Not MinGit, which
  has no bash, and a project's scripts run under Git's bash there.
- **Make on Windows**: ezwinports' native GNU Make, the build Git Bash users add by hand, pinned here by the
  sha256 SourceForge publishes for it: it has no release feed to read a newer one from.
- **Git on macOS**: Apple's own installer for the command line developer tools, opened with
  `xcode-select --install`. The board downloads nothing; the dialog is the system's.
- **Make on macOS**: the same developer tools, the same dialog.
- **Python**: python-build-standalone's newest 3.13 `install_only` build for this platform, checked
  against the sha256 GitHub records for the asset. Not Apple's developer tools: the `python3` they carry
  is 3.9, older than a project's scripts need. On Windows a `python3` shim for bash is written beside it,
  and goes first, ahead of the Store's stub of that name (`windows_shims` writes the same for a Python the
  person installed).
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
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agent_install import checked, fetched, unpacked
from .prerequisites import BY_KEY, found
from .shell_environment import TOOLS, adopt_tools

NODE_INDEX = "https://nodejs.org/dist/index.json"
NODE_DIST = "https://nodejs.org/dist"
GIT_FOR_WINDOWS = "https://api.github.com/repos/git-for-windows/git/releases/latest"
#: ezwinports' GNU Make for Windows, with the sha256 SourceForge publishes beside it.
MAKE_W32 = {"url": "https://sourceforge.net/projects/ezwinports/files/make-4.4.1-without-guile-w32-bin.zip/download",
            "sha256": "fb66a02b530f7466f6222ce53c0b602c5288e601547a034e4156a512dd895ee7", "version": "4.4.1",
            "bin": "bin", "name": "make-4.4.1-without-guile-w32-bin.zip"}
STANDALONE = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
#: This machine as python-build-standalone names its builds.
TRIPLES = {("darwin", "arm64"): "aarch64-apple-darwin", ("darwin", "x86_64"): "x86_64-apple-darwin",
           ("linux", "x86_64"): "x86_64-unknown-linux-gnu", ("linux", "aarch64"): "aarch64-unknown-linux-gnu",
           ("win32", "amd64"): "x86_64-pc-windows-msvc", ("win32", "arm64"): "aarch64-pc-windows-msvc"}
#: This machine's processor, in each publisher's words.
NODE_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}
GIT_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "64-bit", "amd64": "64-bit"}


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


def portable_git_archive(release: dict[str, Any], arch: str | None = None) -> dict[str, str]:
    """PortableGit for this processor from Git for Windows' latest release, with the sha256 GitHub records."""
    arch = arch or GIT_ARCH.get(machine(), "")
    def fits(name: str) -> bool:
        return name.startswith("PortableGit-") and name.endswith(f"-{arch}.7z.exe")

    asset = next((one for one in release.get("assets") or [] if fits(str(one.get("name", "")))), None)
    if asset is None:
        raise ValueError(f"Git for Windows' latest release has no PortableGit for {arch or 'this processor'}")
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:"):
        raise ValueError("GitHub records no sha256 for PortableGit, so it cannot be checked and was not fetched; "
                         "install Git from https://git-scm.com/downloads")
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
            "version": hit.group(1), "bin": "python" if "windows" in triple else "python/bin"}


def way(key: str) -> str:
    """How the board puts `key` on this machine: `archive`, `apple` (the system's own installer), or `""`."""
    if key == "node":
        return "archive" if NODE_ARCH.get(machine()) else ""
    if key == "git":
        return {"win32": "archive" if GIT_ARCH.get(machine()) else "", "darwin": "apple"}.get(sys.platform, "")
    if key == "make":
        return {"win32": "archive", "darwin": "apple"}.get(sys.platform, "")
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
        # The step under way, in words, since when, and how far through it where that can be counted. The
        # lines are what has happened; this is what is happening, which is what a person waiting looks for.
        self.now, self.since, self.got, self.total = "", time.monotonic(), 0, 0
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def say(self, line: str) -> None:
        with self.lock:
            self.lines.append(line)

    def step(self, words: str) -> None:
        """What is being done from here on, until the next step or the end."""
        with self.lock:
            self.now, self.since, self.got, self.total = words, time.monotonic(), 0, 0

    def progress(self, got: int, total: int) -> None:
        with self.lock:
            self.got, self.total = got, total

    def archive(self) -> dict[str, str]:
        if self.key == "node":
            return node_archive(read_json(NODE_INDEX))
        if self.key == "python3":
            return python_archive(read_json(STANDALONE))
        if self.key == "make":
            return dict(MAKE_W32)
        return portable_git_archive(read_json(GIT_FOR_WINDOWS))

    def run(self) -> None:
        try:
            self.step("Asking the publisher for its newest release")
            archive = self.archive()
            self.step("Downloading")
            file = fetched(archive["url"], self.home, self.say, self.progress)
            if "name" in archive:  # a URL that does not end in the file's name
                file = file.replace(file.with_name(archive["name"]))
            self.step("Checking it against the publisher's checksum")
            checked(file, archive["sha256"], "the publisher", self.say)
            self.step("Unpacking")
            if file.name.endswith(".7z.exe"):
                place = self.home / "unpacked"
                self.say("Unpacking PortableGit…")
                subprocess.run([str(file), f"-o{place}", "-y"], capture_output=True, timeout=900, check=True)
            else:
                place = unpacked(file, self.home / "unpacked")
            self.step("Finishing")
            discard(file)
            where = place / archive["bin"]
            if not where.is_dir():
                raise ValueError(f"the archive holds no {archive['bin']}; not installed")
            if self.key == "python3" and sys.platform == "win32":
                shim(where / "python3", where / "python.exe")
                self.first = True
            record = {"bin": str(where), "version": archive["version"], "at": datetime.now(UTC).strftime("%Y-%m-%d"),
                      "first": self.first}
            (self.home / "tool.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            adopt_tools(home=self.home.parent)  # the board's own `git` is found from now, not from a restart
            self.say(f"Installed {BY_KEY[self.key].name} {archive['version']} in {where}.")
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as fault:
            self.say(f"! {fault}")
        finally:
            with self.lock:
                self.done = True

    def state(self) -> dict[str, Any]:
        """What the page polls: the lines so far, whether it is over and whether it failed, and while it is
        under way the step in words (`now`) with how far through it (`fraction`, where it can be counted)."""
        with self.lock:
            failed = bool(self.lines) and self.lines[-1].startswith("!")
            if self.done:
                return {"key": self.key, "lines": list(self.lines), "done": True, "failed": failed,
                        "now": "", "fraction": None}
            waited = int(time.monotonic() - self.since)
            if self.total:
                how = f": {self.got / 1e6:.0f} of {self.total / 1e6:.0f} MB"
            elif self.got:
                how = f": {self.got / 1e6:.0f} MB so far"
            else:
                how = f"… {waited} s" if waited >= 3 else "…"
            return {"key": self.key, "lines": list(self.lines), "done": False, "failed": False,
                    "now": self.now + how if self.now else "",
                    "fraction": round(self.got / self.total, 3) if self.total else None}


def discard(file: Path, tries: int = 10, wait: float = 0.5) -> None:
    """The archive thrown away once it is unpacked, where it can be. Windows refused the first PortableGit —
    *Access is denied*, its self-extractor a moment gone and a virus scanner still reading it — and that
    refusal was reported as the install's: Git sat unpacked and unrecorded, and the card said nothing. An
    archive that will not go is tidying left undone, not a tool that was not installed."""
    for _ in range(tries):
        try:
            file.unlink(missing_ok=True)
            return
        except OSError:
            time.sleep(wait)


def shim(file: Path, target: Path) -> Path:
    """A `python3` bash can run, starting `target`: Windows programs start only `.exe` files, but every
    recipe a project runs goes through bash, which starts this."""
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f'#!/bin/sh\nexec "{target.as_posix()}" "$@"\n', encoding="utf-8", newline="\n")
    return file


def windows_shims(home: Path | None = None, look=found) -> Path | None:
    """On Windows, a `python3` for bash in front of a Python the person installed — ahead of the Store's
    stub of that name — where the board did not install the Python itself. None where there is nothing to
    write: elsewhere, no Python, or one with its shim beside it already."""
    if sys.platform != "win32":
        return None
    have = look(BY_KEY["python3"])
    if have.state != "found" or (Path(have.where).parent / "python3").is_file():
        return None
    folder = (TOOLS if home is None else home) / "python3-shim"
    written = shim(folder / "bin/python3", Path(have.where))
    record = {"bin": str(written.parent), "version": have.version, "at": datetime.now(UTC).strftime("%Y-%m-%d"),
              "first": True}
    (folder / "tool.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return written


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
    installing = Installing(key, home, first=have.state == "old" and not have.lacks)
    RUNNING[key] = installing
    installing.thread.start()
    return installing


def state(key: str) -> dict[str, Any]:
    held = RUNNING.get(key)
    return held.state() if held is not None else {"key": key, "lines": [], "done": True, "failed": False,
                                                  "now": "", "fraction": None}

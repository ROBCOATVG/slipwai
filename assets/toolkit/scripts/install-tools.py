#!/usr/bin/env python3
"""`python3 scripts/install-tools.py <tool>...`: put what this project needs on this machine, whatever it is.

A person who answered slipwai's questions, or ticked an extension, has already said what they want; being
handed an install command to go and run is friction with nothing gained. So slipwai, `./init` and every
extension call this instead of printing one, and it installs the tool the way this machine installs things:

- **the package manager the machine has** — Homebrew or MacPorts on macOS; apt, dnf, pacman, zypper or apk on
  Linux and WSL (through `sudo`, which may ask for a password); winget, Scoop or Chocolatey on Windows;
- **the publisher's own user-level download** where a distribution's package is too old to build with, or
  where no manager carries it: Node, Go and the JDK on Linux and macOS, from nodejs.org, go.dev and Adoptium,
  into `~/.local/share/slipwai-tools` with the commands linked into `~/.local/bin`; uv from astral.sh;
- and afterwards the directories those put commands in are added to this process's `PATH`, so the step that
  asked can carry on without a new shell.

What is already on `PATH` is never reinstalled. Nothing here is fatal to the caller: a tool that could not be
installed is returned, and the caller says what that costs. `SLIPWAI_NO_INSTALL=1` turns all of it off — for CI,
an air-gapped machine, or anyone who installs their own tools — and then this only reports what is missing.

slipwai itself loads this same file (its `host.py`), so the machine detection, the recipes and the installs
are one implementation, not one in the factory and a second in every project. Standard library only: it has
to run on a machine that has nothing yet.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

# Per operating system, the package managers looked for, preferred first: Homebrew on Linux is somebody's
# deliberate choice, so it comes before the distribution's own.
MANAGERS: dict[str, tuple[str, ...]] = {
    "macos": ("brew", "port"),
    "linux": ("brew", "apt-get", "dnf", "pacman", "zypper", "apk"),
    "windows": ("winget", "scoop", "choco"),
}

# How each manager installs one package. The system managers need root; `sudo` is dropped where this already
# runs as root, and made non-interactive (`sudo -n`) where there is no terminal to type a password into.
INSTALL: dict[str, str] = {
    "brew": "brew install {}",
    "port": "sudo port install {}",
    "apt-get": "sudo apt-get install -y {}",
    "dnf": "sudo dnf install -y {}",
    "pacman": "sudo pacman -S --needed --noconfirm {}",
    "zypper": "sudo zypper install -y {}",
    "apk": "sudo apk add {}",
    "winget": "winget install --exact --id {}",
    "scoop": "scoop install {}",
    "choco": "choco install -y {}",
}

# What a manager needs before its first install in a session: apt's package lists are usually stale on a fresh
# machine or container, and an install from a stale list fails on a version that is no longer served.
REFRESH: dict[str, str] = {"apt-get": "sudo apt-get update -qq", "apk": "sudo apk update -q"}

# Flags a manager needs to install without asking, beyond what `INSTALL` spells for a person to read.
UNATTENDED: dict[str, str] = {
    "winget": " --silent --accept-package-agreements --accept-source-agreements",
}

# Per tool, the package each manager knows it as. A manager with no entry has no package worth naming. Node, Go
# and the JDK are deliberately absent for the Linux managers: their packages trail what a generated project
# builds with (Node 22.13+, Go 1.26+, JDK 25), so those come from `DOWNLOADS` there instead.
PACKAGES: dict[str, dict[str, str]] = {
    "git": {
        "brew": "git", "port": "git", "apt-get": "git", "dnf": "git", "pacman": "git", "zypper": "git",
        "apk": "git", "winget": "Git.Git", "scoop": "git", "choco": "git",
    },
    # Homebrew links `python3` only for its current Python (the unversioned `python`); `python@3.13` installs a
    # keg with no `python3` on PATH, which is what a Mac run found.
    "python3": {
        "brew": "python", "port": "python313", "apt-get": "python3 python3-venv", "dnf": "python3",
        "pacman": "python", "zypper": "python3", "apk": "python3", "winget": "Python.Python.3.13",
        "scoop": "python", "choco": "python",
    },
    "uv": {"brew": "uv", "pacman": "uv", "dnf": "uv", "apk": "uv", "winget": "astral-sh.uv", "scoop": "uv"},
    "make": {
        "brew": "make", "apt-get": "make", "dnf": "make", "pacman": "make", "zypper": "make", "apk": "make",
        "winget": "ezwinports.make", "scoop": "make", "choco": "make",
    },
    "node": {"brew": "node", "apk": "nodejs npm", "winget": "OpenJS.NodeJS.LTS", "scoop": "nodejs-lts",
             "choco": "nodejs-lts"},
    "go": {"brew": "go", "apk": "go", "winget": "GoLang.Go", "scoop": "go", "choco": "golang"},
    "java": {"winget": "EclipseAdoptium.Temurin.25.JDK", "scoop": "temurin25-jdk", "choco": "temurin25"},
    "tofu": {"brew": "opentofu", "winget": "OpenTofu.Tofu", "scoop": "opentofu", "choco": "opentofu"},
    "aws": {"brew": "awscli", "pacman": "aws-cli-v2", "winget": "Amazon.AWSCLI", "choco": "awscli"},
    "az": {"brew": "azure-cli", "winget": "Microsoft.AzureCLI", "choco": "azure-cli"},
    "curl": {
        "brew": "curl", "port": "curl", "apt-get": "curl ca-certificates", "dnf": "curl", "pacman": "curl",
        "zypper": "curl", "apk": "curl", "winget": "cURL.cURL", "scoop": "curl", "choco": "curl",
    },
    "gh": {
        "brew": "gh", "port": "gh", "apt-get": "gh", "dnf": "gh", "pacman": "github-cli", "zypper": "gh",
        "apk": "github-cli", "winget": "GitHub.cli", "scoop": "gh", "choco": "gh",
    },
}

# Publishers' own installers, for a tool no manager present carries. Each is user-level: it needs no root.
FALLBACK: dict[str, dict[str, str]] = {
    "uv": {
        "posix": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "windows": 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    },
    "codegraph": {
        "posix": "curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh",
    },
    "tofu": {
        "posix": "curl -fsSL https://get.opentofu.org/install-opentofu.sh | sh -s -- --install-method standalone",
    },
}

# The same installers, as what this script runs on a POSIX machine: the script is fetched with the standard
# library and handed to `sh`, so a machine without `curl` — a bare container — installs them too. The `curl`
# lines above are what a person is shown.
FALLBACK_SCRIPTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "uv": ("https://astral.sh/uv/install.sh", ()),
    "codegraph": ("https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh", ()),
    "tofu": ("https://get.opentofu.org/install-opentofu.sh", ("--install-method", "standalone")),
}

# The command a tool is known by on PATH, where it differs from the tool's name here.
COMMAND = {"node": "node", "java": "java", "python3": "python3"}

NAMES = {"macos": "macOS", "linux": "Linux", "wsl": "Linux under WSL", "windows": "Windows", "other": "this system"}
HOME = Path.home()
BIN = HOME / ".local/bin"
# The PATH this process started with, before `refresh_path` adds to it: what a new shell would see.
STARTING_PATH = os.environ.get("PATH", "").split(os.pathsep)
TOOLS_HOME = HOME / ".local/share/slipwai-tools"
NODE_MAJOR = 24  # what a generated project's CI and Compose run (`.nvmrc`); the gate needs 22.13 or newer
JDK_MAJOR = 25


@dataclass(frozen=True)
class Host:
    """The operating system, and which of its package managers are on the PATH, preferred first."""

    system: str
    managers: tuple[str, ...]

    @property
    def name(self) -> str:
        return NAMES[self.system]

    @property
    def posix(self) -> bool:
        """Whether a `/bin/sh` script such as `./init` runs here as it is."""
        return self.system != "windows"


def system() -> str:
    """`macos`, `linux`, `wsl`, `windows` or `other`. Cygwin and MSYS2 are POSIX shells and read as `other`.

    `SLIPWAI_HOST_SYSTEM` names one outright. It exists to test slipwai itself: a container can only be Linux, and
    the macOS routes (Homebrew first) are exercised in one that sets `SLIPWAI_HOST_SYSTEM=macos`."""
    forced = os.environ.get("SLIPWAI_HOST_SYSTEM", "").strip()
    if forced in NAMES:
        return forced
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        # WSL is Linux to every program inside it; the difference is only written in the kernel's release.
        return "wsl" if "microsoft" in platform.release().lower() else "linux"
    return "other"


def detect() -> Host:
    """This machine: its operating system and the package managers present on it."""
    found = system()
    candidates = MANAGERS.get("linux" if found == "wsl" else found, ())
    return Host(found, tuple(manager for manager in candidates if shutil.which(manager)))


def install_command(tool: str, host: Host | None = None) -> str | None:
    """The one line that installs `tool` here with a package manager or publisher's installer, or None."""
    host = host or detect()
    for manager in host.managers:
        package = PACKAGES.get(tool, {}).get(manager)
        if package:
            return INSTALL[manager].format(package)
    return FALLBACK.get(tool, {}).get("posix" if host.posix else "windows")


def install_hint(tool: str, where: str, host: Host | None = None) -> str:
    """How to get `tool`: this machine's command where one is known, with the page for everything else."""
    command = install_command(tool, host)
    return f"`{command}` (or {where})" if command else where


def uv_by_uname() -> str:
    """The uv line, spelled as `/bin/sh` for `./init`, which asks `uname` where it runs. Git Bash says MINGW."""
    choices = {
        "Darwin": INSTALL["brew"].format(PACKAGES["uv"]["brew"]),
        "MINGW*|MSYS*|CYGWIN*": INSTALL["winget"].format(PACKAGES["uv"]["winget"]),
        "*": FALLBACK["uv"]["posix"],
    }
    arms = "".join(f"    {pattern}) uv_install='{command}' ;;\n" for pattern, command in choices.items())
    return (
        f'  case "$(uname -s 2>/dev/null)" in\n{arms}  esac\n'
        """  printf '%s\\n' "On this machine, uv installs with: $uv_install" >&2\n"""
    )


# --- installing ----------------------------------------------------------------------------------------------


def disabled() -> bool:
    return os.environ.get("SLIPWAI_NO_INSTALL", "").strip() not in ("", "0", "false", "no")


# Where a tool on PATH can be too old to count. A stock Mac's `python3` is Apple's 3.9, below what the gate scripts
# run on; an old distribution's Node is below what a generated project builds with. Such a tool is installed over,
# the same as a missing one.
MINIMUM: dict[str, tuple[int, ...]] = {"python3": (3, 10), "node": (22, 13)}
VERSION_ARGS: dict[str, list[str]] = {
    "python3": ["-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
    "node": ["--version"],
}


def version_of(tool: str) -> tuple[int, ...] | None:
    """The version the tool on PATH reports, or None where it says nothing that reads as one."""
    import re

    path = shutil.which(COMMAND.get(tool, tool))
    if path is None:
        return None
    try:
        said = subprocess.run([path, *VERSION_ARGS.get(tool, ["--version"])], capture_output=True, text=True,
                              timeout=30, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", said)
    return tuple(int(part) for part in found.groups() if part is not None) if found else None


def present(tool: str) -> bool:
    """On PATH, and — where there is a floor — runnable and new enough. A floored tool that cannot say its version
    does not count: Windows' `python3` Store alias, or a glibc build on a musl system, is on PATH and runs nothing."""
    if shutil.which(COMMAND.get(tool, tool)) is None:
        return False
    floor = MINIMUM.get(tool)
    if not floor:
        return True
    found = version_of(tool)
    return found is not None and found >= floor


def musl() -> bool:
    """Whether this Linux links against musl (Alpine), where the publishers' glibc builds do not run."""
    return any(Path(p).exists() for p in ("/lib/ld-musl-x86_64.so.1", "/lib/ld-musl-aarch64.so.1"))


def arch() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in ("arm64", "aarch64") else "x64"


# Named, because Python's default `Python-urllib/3.x` is refused outright by some of these hosts' CDNs — astral.sh
# answers it 403 — and a bare container has no `curl` to fall back on.
AGENT = "slipwai-install-tools/1 (+https://github.com/ROBCOATVG/slipwai)"


def open_url(url: str, timeout: int):  # type: ignore[no-untyped-def]
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - fixed https hosts only


def fetch_json(url: str) -> object:
    with open_url(url, 60) as response:
        return json.load(response)


def fetch(url: str, into: Path, name: str | None = None) -> Path:
    target = into / (name or url.rsplit("/", 1)[-1].split("?", 1)[0])
    with open_url(url, 600) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return target


def unpack(archive: Path, destination: Path) -> Path:
    """Extract a release archive into `destination` and return the single directory it holds."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with tarfile.open(archive) as bundle:
        if hasattr(tarfile, "data_filter"):
            bundle.extractall(destination, filter="data")
        else:  # Python before 3.12's extraction filters
            bundle.extractall(destination)  # noqa: S202 - a publisher's release archive over https
    inner = [child for child in destination.iterdir() if child.is_dir()]
    return inner[0] if len(inner) == 1 else destination


def link(bin_dir: Path, names: tuple[str, ...]) -> None:
    BIN.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = bin_dir / name
        if source.exists():
            target = BIN / name
            if target.is_symlink() or target.exists():
                target.unlink()
            target.symlink_to(source)


def download_node(work: Path) -> None:
    releases = fetch_json("https://nodejs.org/dist/index.json")
    wanted = f"v{NODE_MAJOR}."
    version = next(r["version"] for r in releases if r["version"].startswith(wanted))  # type: ignore[index,union-attr]
    platform_name = "darwin" if sys.platform == "darwin" else "linux"
    archive = fetch(f"https://nodejs.org/dist/{version}/node-{version}-{platform_name}-{arch()}.tar.gz", work)
    home = unpack(archive, TOOLS_HOME / "node")
    link(home / "bin", ("node", "npm", "npx", "corepack"))


def download_go(work: Path) -> None:
    releases = fetch_json("https://go.dev/dl/?mode=json")
    version = next(r["version"] for r in releases if r.get("stable"))  # type: ignore[union-attr]
    platform_name = "darwin" if sys.platform == "darwin" else "linux"
    go_arch = "arm64" if arch() == "arm64" else "amd64"
    archive = fetch(f"https://go.dev/dl/{version}.{platform_name}-{go_arch}.tar.gz", work)
    home = unpack(archive, TOOLS_HOME / "go")
    link(home / "bin", ("go", "gofmt"))


def download_java(work: Path) -> None:
    os_name = "mac" if sys.platform == "darwin" else "linux"
    jdk_arch = "aarch64" if arch() == "arm64" else "x64"
    url = f"https://api.adoptium.net/v3/binary/latest/{JDK_MAJOR}/ga/{os_name}/{jdk_arch}/jdk/hotspot/normal/eclipse"
    target = fetch(url, work, "jdk.tar.gz")
    home = unpack(target, TOOLS_HOME / "java")
    if (home / "Contents/Home").is_dir():
        home = home / "Contents/Home"
    link(home / "bin", ("java", "javac", "jar", "jshell"))


def download_uv(work: Path) -> None:
    """uv's own release archive from GitHub: what its installer fetches, without needing the installer's `curl`."""
    machine = "aarch64" if arch() == "arm64" else "x86_64"
    target = f"{machine}-apple-darwin" if sys.platform == "darwin" else f"{machine}-unknown-linux-gnu"
    archive = fetch(f"https://github.com/astral-sh/uv/releases/latest/download/uv-{target}.tar.gz", work)
    home = unpack(archive, TOOLS_HOME / "uv")
    link(home, ("uv", "uvx"))


# The publisher's download, preferred over any package manager on these systems: Linux distributions' Node, Go
# and JDK packages trail what a generated project builds with. On macOS Homebrew is current, so it is used for
# Node and Go where present; the JDK comes from Adoptium, pinned to the major the project needs.
DOWNLOADS = {"node": download_node, "go": download_go, "java": download_java, "uv": download_uv}
DOWNLOAD_ON = {
    "node": ("linux", "wsl"), "go": ("linux", "wsl"),
    "java": ("linux", "wsl", "macos"), "uv": ("linux", "wsl", "macos"),
}


def shell(command: str, host: Host) -> int:
    """Run one install line, with `sudo` made fit for where this runs."""
    if host.posix:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            command = command.replace("sudo -n ", "").replace("sudo ", "")
        elif not sys.stdin.isatty():
            command = command.replace("sudo ", "sudo -n ")
    print(f"install-tools: {command}", flush=True)
    return subprocess.run(command, shell=True, check=False).returncode


def refresh_path() -> None:
    """Put the directories the installers above write commands to on this process's PATH."""
    extra = [
        str(BIN), str(HOME / ".cargo/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/home/linuxbrew/.linuxbrew/bin",
    ]
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        extra += [
            os.path.join(local, "Microsoft", "WinGet", "Links"),
            str(HOME / "scoop" / "shims"),
            r"C:\ProgramData\chocolatey\bin",
            r"C:\Program Files\nodejs",
            r"C:\Program Files\Go\bin",
            r"C:\Program Files\Git\cmd",
        ]
        import winreg

        for hive, key in (
            (winreg.HKEY_CURRENT_USER, "Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:  # one hive at a time: a profile with no user-level Path must not hide the machine's
                with winreg.OpenKey(hive, key) as handle:
                    value, _kind = winreg.QueryValueEx(handle, "Path")
                    extra += os.path.expandvars(value).split(os.pathsep)
            except OSError:
                continue
    current = os.environ.get("PATH", "").split(os.pathsep)
    os.environ["PATH"] = os.pathsep.join([*[p for p in extra if p and p not in current], *current])


def persist_bin_on_path(host: Host) -> None:
    """Make `~/.local/bin` part of every new login shell, the way uv's own installer does, where it is not."""
    if not host.posix or str(BIN) in STARTING_PATH:
        return
    line = 'export PATH="$HOME/.local/bin:$PATH"  # added by slipwai install-tools'
    for profile in (HOME / ".zprofile", HOME / ".profile") if host.system == "macos" else (HOME / ".profile",):
        text = profile.read_text(encoding="utf-8") if profile.is_file() else ""
        if line not in text:
            with profile.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"\n{line}\n")


def install(tool: str, host: Host, refreshed: set[str]) -> bool:
    """One tool, by the first route this machine has; whether it is on PATH afterwards."""
    if tool in DOWNLOADS and host.system in DOWNLOAD_ON.get(tool, ()) and not musl() and not (
        host.system == "macos" and tool in PACKAGES and "brew" in host.managers and PACKAGES[tool].get("brew")
    ):
        try:
            with tempfile.TemporaryDirectory() as work:
                print(f"install-tools: downloading {tool} from its publisher", flush=True)
                DOWNLOADS[tool](Path(work))
            persist_bin_on_path(host)
        except (OSError, ValueError, StopIteration, tarfile.TarError) as error:
            print(f"install-tools: the {tool} download failed: {error}", file=sys.stderr)
        refresh_path()
        return present(tool)
    for manager in host.managers:
        package = PACKAGES.get(tool, {}).get(manager)
        if not package:
            continue
        if manager in REFRESH and manager not in refreshed:
            shell(REFRESH[manager], host)
            refreshed.add(manager)
        shell(INSTALL[manager].format(package) + UNATTENDED.get(manager, ""), host)
        refresh_path()
        if present(tool):
            return True
    if host.posix and tool in FALLBACK_SCRIPTS:
        url, arguments = FALLBACK_SCRIPTS[tool]
        if not present("curl") and not present("wget"):
            install("curl", host, refreshed)  # the publishers' installers download with one of the two
        try:
            with tempfile.TemporaryDirectory() as work:
                script = fetch(url, Path(work))
                print(f"install-tools: sh {url} {' '.join(arguments)}".rstrip(), flush=True)
                subprocess.run(["sh", str(script), *arguments], check=False)
        except OSError as error:
            print(f"install-tools: fetching {url} failed: {error}", file=sys.stderr)
        persist_bin_on_path(host)
        refresh_path()
    elif (fallback := FALLBACK.get(tool, {}).get("windows")) and not host.posix:
        shell(fallback, host)
        refresh_path()
    return present(tool)


def ensure(tools: list[str], host: Host | None = None) -> list[str]:
    """Install every tool in `tools` that is not on PATH; return the ones still missing afterwards."""
    refresh_path()
    wanted = [tool for tool in dict.fromkeys(tools) if not present(tool)]
    if not wanted:
        return []
    if disabled():
        return wanted
    host = host or detect()
    refreshed: set[str] = set()
    return [tool for tool in wanted if not install(tool, host, refreshed)]


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    missing = ensure(argv)
    for tool in missing:
        hint = install_command(tool)
        print(
            f"install-tools: {tool} is still not installed"
            + (f"; `{hint}` is the line for this machine" if hint else "")
            + (" (SLIPWAI_NO_INSTALL is set)" if disabled() else ""),
            file=sys.stderr,
        )
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""Which machine this is, and how a missing tool is installed on it.

A missing tool used to be answered with a link: `opentofu.org/docs/intro/install/`, whichever machine asked.
The person then read an installation page to find the one line for their platform — the line this module
already knows. So the operating system is established from the interpreter (`sys.platform`, and the kernel
release for WSL, which reports itself as Linux), the package managers from the PATH, and each tool the
factory or a project's `./init` needs is given the command that installs it with the first of those present.

Nothing is installed here. A command is printed for a person to run, because installing software is theirs
to decide and often needs `sudo` or an elevated shell a generator should never ask for. Where no manager
present has a recipe, the answer is `None`, and the caller keeps the link it always had.

The recipes are the package names each manager's own index uses. A manager is only named where the package
is in its default index: Debian's `apt` has `gh` and `git` but not OpenTofu, so for OpenTofu on Debian the
answer is the link, not a third-party repository added on the person's behalf.
"""
from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass

# Per operating system, the package managers looked for, in the order one is preferred where several are
# present: Homebrew on Linux is somebody's deliberate choice, so it comes before the distribution's own.
MANAGERS: dict[str, tuple[str, ...]] = {
    "macos": ("brew", "port"),
    "linux": ("brew", "apt-get", "dnf", "pacman", "zypper", "apk"),
    "windows": ("winget", "scoop", "choco"),
}

# How each manager is invoked to install one package. A system manager on Linux needs root; a Windows one
# may need an elevated shell, which is the person's to open and not something a command line can add.
INSTALL: dict[str, str] = {
    "brew": "brew install {}",
    "port": "sudo port install {}",
    "apt-get": "sudo apt-get install -y {}",
    "dnf": "sudo dnf install -y {}",
    "pacman": "sudo pacman -S --needed {}",
    "zypper": "sudo zypper install -y {}",
    "apk": "sudo apk add {}",
    "winget": "winget install --exact --id {}",
    "scoop": "scoop install {}",
    "choco": "choco install -y {}",
}

# Per tool, the package each manager knows it as. A manager with no entry has no package worth naming.
PACKAGES: dict[str, dict[str, str]] = {
    "git": {
        "brew": "git", "port": "git", "apt-get": "git", "dnf": "git", "pacman": "git", "zypper": "git",
        "apk": "git", "winget": "Git.Git", "scoop": "git", "choco": "git",
    },
    "python3": {
        "brew": "python@3.13", "port": "python313", "apt-get": "python3 python3-venv", "dnf": "python3",
        "pacman": "python", "zypper": "python3", "apk": "python3", "winget": "Python.Python.3.13",
        "scoop": "python", "choco": "python",
    },
    "uv": {"brew": "uv", "pacman": "uv", "dnf": "uv", "apk": "uv", "winget": "astral-sh.uv", "scoop": "uv"},
    "tofu": {"brew": "opentofu", "winget": "OpenTofu.Tofu", "scoop": "opentofu", "choco": "opentofu"},
    "aws": {"brew": "awscli", "pacman": "aws-cli-v2", "winget": "Amazon.AWSCLI", "choco": "awscli"},
    "az": {"brew": "azure-cli", "winget": "Microsoft.AzureCLI", "choco": "azure-cli"},
    "gh": {
        "brew": "gh", "port": "gh", "apt-get": "gh", "dnf": "gh", "pacman": "github-cli", "zypper": "gh",
        "apk": "github-cli", "winget": "GitHub.cli", "scoop": "gh", "choco": "gh",
    },
}

# uv publishes its own installer, which works where no manager carries it — Debian and Ubuntu among them.
FALLBACK: dict[str, dict[str, str]] = {
    "uv": {
        "posix": "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "windows": 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    },
}

NAMES = {"macos": "macOS", "linux": "Linux", "wsl": "Linux under WSL", "windows": "Windows", "other": "this system"}


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
    """`macos`, `linux`, `wsl`, `windows` or `other`. Cygwin and MSYS2 are POSIX shells and read as `other`."""
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        # WSL is Linux to every program inside it, and the one difference that matters here — that Windows
        # is a separate machine whose PATH this cannot see — is only written in the kernel's release string.
        return "wsl" if "microsoft" in platform.release().lower() else "linux"
    return "other"


def detect() -> Host:
    """This machine: its operating system and the package managers present on it."""
    found = system()
    candidates = MANAGERS.get("linux" if found == "wsl" else found, ())
    return Host(found, tuple(manager for manager in candidates if shutil.which(manager)))


def install_command(tool: str, host: Host | None = None) -> str | None:
    """The one line that installs `tool` here, or None where no manager present carries it."""
    host = host or detect()
    for manager in host.managers:
        package = PACKAGES.get(tool, {}).get(manager)
        if package:
            return INSTALL[manager].format(package)
    return FALLBACK.get(tool, {}).get("posix" if host.posix else "windows")


def uv_by_uname() -> str:
    """The same answer for uv, spelled as `/bin/sh` for `./init`, which runs wherever the repository is cloned
    rather than where it was generated — so it asks `uname` then. Git Bash and MSYS report MINGW or MSYS."""
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


def install_hint(tool: str, where: str, host: Host | None = None) -> str:
    """How to get `tool`: this machine's command where one is known, with the page for everything else."""
    command = install_command(tool, host)
    return f"`{command}` (or {where})" if command else where

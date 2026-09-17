"""`slipwai upgrade`: making this copy the newest one, whichever way it was installed.

There are four ways to have a `slipwai` and no two of them are made newer by the same command — a tool
environment `uv` owns, a package inside somebody's virtual environment, a single-file executable that cannot
overwrite itself while it is running, and a checkout whose newest version arrives as a merge. Whoever
installed it six months ago does not remember which of the four they chose, and the command that would tell
them is the one they are looking for. So this verb works it out and does the right thing: it runs the
upgrade where running it is safe, and where it is not — a binary replacing itself, a working tree that may
have local commits in it — it prints exactly what to do instead and touches nothing.

It asks the registry what the newest version is before it does any of that,
rather than handing the whole question to the installer. Public installs ask
PyPI; an install whose uv receipt names an internal mirror keeps asking that
mirror, and `SLIPWAI_INDEX` remains the explicit override.
"""
from __future__ import annotations

import argparse
import base64
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .assets import FROZEN, INSTALLED, ROOT, VERSION
from .errors import GenerationError
from .versions import is_prerelease, key

PACKAGE = "slipwai"
FORGE = "https://git.treyco.dev/ROBCOATVG/slipwai"
# Where public releases are published. The name matters for an internal mirror
# that requires credentials: uv derives that mirror's environment variables
# from it. Both are defaults; an installed tool's receipt remains authoritative.
INDEX = "https://pypi.org/simple"
INDEX_NAME = "slipwai"
# The file `uv tool install` leaves at the root of the environment it made, holding what it installed and
# which indexes to consult next time. Its presence is the only reliable mark of a uv-managed tool: the
# environment is otherwise an ordinary virtual environment.
RECEIPT = "uv-receipt.toml"
TIMEOUT = 15


def how_installed(frozen: bool = FROZEN, installed: bool = INSTALLED, prefix: Path | None = None) -> str:
    """Which of the four this copy is: `executable`, `uv-tool`, `environment` or `checkout`.

    Read off the running interpreter rather than asked, because the answer is not something a user can be
    expected to know. The frozen executable and the checkout are already distinguished by `assets`, which
    has to tell them apart to find its own material; what `assets` calls installed splits again here, into
    the tool environment `uv` owns and a package sitting in an environment somebody else owns — the same
    files, but `pip` may not touch the first and `uv tool upgrade` does not know about the second.

    The parameters are for the tests, which have to be able to ask about the three shapes this checkout is
    not.
    """
    if frozen:
        return "executable"
    if not installed:
        return "checkout"
    root = Path(sys.prefix) if prefix is None else prefix
    return "uv-tool" if (root / RECEIPT).is_file() else "environment"


def index_of(receipt: Path) -> tuple[str, str]:
    """Which index to ask, as (name, url): `SLIPWAI_INDEX`, else the receipt's, else the documented default.

    An installed tool's own receipt is the authority on where its copies come from — somebody who installed
    from a mirror is upgraded from that mirror, not from whatever this file was compiled believing. The
    default is for the three shapes that have no receipt at all, and the variable is for the one shape that
    has neither: a package `pip` installed into somebody's environment, whose index is in a `pip.conf` this
    command has no business parsing. Naming it there also makes the answer to "what would this say" testable
    without a forge.
    """
    override = os.environ.get("SLIPWAI_INDEX")
    if override:
        return INDEX_NAME, override
    try:
        content = tomllib.loads(receipt.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return INDEX_NAME, INDEX
    for index in content.get("tool", {}).get("options", {}).get("index", []):
        if isinstance(index, dict) and isinstance(index.get("url"), str):
            name = index.get("name")
            return (name if isinstance(name, str) else INDEX_NAME), index["url"]
    return INDEX_NAME, INDEX


def environment_variable(index_name: str) -> str:
    """The stem `uv` reads an index's credentials from: the index's name, upper-cased, non-alphanumerics
    flattened to underscores. `UV_INDEX_SLIPWAI_USERNAME` and `..._PASSWORD` for an index named `slipwai`."""
    flattened = "".join(character if character.isalnum() else "_" for character in index_name)
    return f"UV_INDEX_{flattened.upper()}"


def credentials(index_name: str, url: str) -> tuple[str, str] | None:
    """The username and password to query the index with: the environment's, or the URL's own.

    The same two variables `uv` reads, so a machine set up to upgrade with `uv` needs nothing further set up
    to be told *whether* to. An index URL that carries its own credentials — the shape `pip`'s
    `--index-url` takes — is honoured too, so that install is not left unable to answer its own question.
    """
    stem = environment_variable(index_name)
    user, password = os.environ.get(f"{stem}_USERNAME"), os.environ.get(f"{stem}_PASSWORD")
    if user and password:
        return user, password
    parsed = urllib.parse.urlsplit(url)
    if parsed.username and parsed.password:
        return urllib.parse.unquote(parsed.username), urllib.parse.unquote(parsed.password)
    return None


def versions_in(page: str) -> list[str]:
    """Every version a PEP 503 index page lists, read off the filenames it links to.

    The filename is the authority — `slipwai-1.6.0-py3-none-any.whl`, `slipwai-1.6.0.tar.gz` — because it is
    the one part of the page every index agrees on: the URLs are absolute on one registry and relative on
    another, the `data-` attributes are optional, and the link text is a courtesy.
    """
    found: list[str] = []
    for href in re.findall(r'href\s*=\s*"([^"]+)"', page):
        filename = urllib.parse.unquote(posixpath.basename(urllib.parse.urlsplit(href).path))
        if not filename.lower().startswith(f"{PACKAGE}-"):
            continue
        if filename.endswith(".whl"):
            found.append(filename.split("-")[1])
        elif filename.endswith(".tar.gz"):
            found.append(filename[: -len(".tar.gz")].split("-")[-1])
    return found


def published(index_name: str, url: str, prerelease: bool = False) -> str | None:
    """The newest version of this package the index holds, or `None` when it holds none of it.

    Releases only, unless `prerelease` — the same rule `pip` and `uv` apply, because the registry also holds
    the snapshot of `main` (`1.3.0.dev7`, [docs/publishing.md](../../docs/publishing.md)) and an install
    that never asked for one must never be told it is behind it. Every refusal is raised with what the forge
    actually answered, because the failure this whole verb is about is a `401` read as an empty registry.
    """
    query = f"{url.rstrip('/')}/{PACKAGE}/"
    parsed = urllib.parse.urlsplit(query)
    # The URL is the receipt's or the constant above, with any embedded credentials moved into the header.
    request = urllib.request.Request(
        urllib.parse.urlunsplit(parsed._replace(netloc=parsed.netloc.rpartition("@")[2])),
        headers={"User-Agent": f"slipwai/{VERSION}", "Accept": "text/html"},
    )
    secret = credentials(index_name, url)
    if secret is not None:
        token = base64.b64encode(":".join(secret).encode()).decode()
        request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            page = answer.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        error.close()
        if error.code == 404:
            return None
        raise GenerationError(refusal(error.code, index_name, url)) from error
    except urllib.error.URLError as error:
        raise GenerationError(f"cannot reach the registry at {query}: {error.reason}") from error
    found = versions_in(page)
    if not prerelease:
        found = [version for version in found if not is_prerelease(version)]
    return max(found, key=key, default=None)


def following_snapshots(asked: bool = False) -> bool:
    """Whether snapshots count as versions to upgrade to: when asked with `--pre`, or when this copy is one.

    A copy that is itself `1.3.0.dev4` was installed by somebody following `main`, and telling them the
    newest version is a release they are already past would be the wrong answer to the question they asked.
    """
    return asked or is_prerelease(VERSION)


def newer_published() -> str | None:
    """The newest published version when it is newer than this one, else `None`.

    For `migrate`, which brings a project up to *this* version and should say so when this is not the newest
    there is — without upgrading anything itself. Raises what `published` raises when the registry cannot be
    asked, and the caller decides how loudly to pass that on."""
    name, url = index_of(Path(sys.prefix) / RECEIPT)
    newest = published(name, url, following_snapshots())
    if newest is None or key(newest) <= key(VERSION):
        return None
    return newest


def refusal(status: int, index_name: str, url: str) -> str:
    """What to do about a registry that answered rather than a registry that was not there.

    `401` and `403` are the ones with an answer: the credentials were never sent. `uv` does not keep the ones
    an index was installed with — only the URL — so an install done the way the documentation used to say,
    with the token inside the URL, has nothing to authenticate with a year later. Naming the two variables
    is the whole of the fix.
    """
    if status not in (401, 403):
        return f"the registry at {url} answered {status} for {PACKAGE}"
    stem = environment_variable(index_name)
    return (
        f"the registry at {url} answered {status}: it wants credentials this command was not given. uv keeps "
        f"an index's URL but never the token it was installed with, so export them under the index's name "
        f"and run this again:\n"
        f"  export {stem}_USERNAME=<your forge username>\n"
        f"  export {stem}_PASSWORD=<a token with read:package>"
    )


def upgrade_command(kind: str, prerelease: bool = False) -> list[str]:
    """The command that makes this copy newer, for the two shapes something may be run for.

    Neither spells an index. `uv` reuses the one in its receipt and `pip` the one in the environment's
    configuration, so the upgrade goes wherever the install came from — and a machine configured for a
    different forge is not overridden by an argument this factory guessed. Both are told to take a
    pre-release only when `prerelease`: left to themselves they pass a snapshot over, which is right for
    everyone who did not ask for one.
    """
    if kind == "uv-tool":
        uv = shutil.which("uv")
        if uv is None:
            raise GenerationError(
                "this copy is a uv tool, but `uv` is not on the PATH to upgrade it with. Install uv "
                "(curl -LsSf https://astral.sh/uv/install.sh | sh), then run `slipwai upgrade` again."
            )
        return [uv, "tool", "upgrade", *(["--prerelease", "allow"] if prerelease else []), PACKAGE]
    if kind == "environment":
        return [sys.executable, "-m", "pip", "install", "--upgrade", *(["--pre"] if prerelease else []), PACKAGE]
    raise GenerationError(f"nothing can be run to upgrade an install of kind {kind}")


def guidance(kind: str) -> str:
    """What to do by hand, for the two shapes nothing may be run for.

    An executable cannot be replaced while it is the process doing the replacing, and a checkout is a
    working tree that may hold local commits, a dirty index or a branch that is not `main` — pulling it
    unasked is somebody else's work rearranged. Both get the exact command or address instead.
    """
    if kind == "executable":
        return (
            f"This copy is the standalone executable at {Path(sys.executable).resolve()}, which cannot "
            f"replace itself while it is running.\n"
            f"Download the archive for this platform from {FORGE}/releases, check it against the .sha256 "
            f"published beside it, and put the `slipwai` inside it where this one is."
        )
    return (
        f"This copy is the checkout at {ROOT}, whose newest version arrives as a merge rather than as an "
        f"install.\n"
        f"Run `git -C {ROOT} pull` yourself — it is your working tree, and it may hold commits, uncommitted "
        f"changes or a branch that is not main."
    )


def main(argv: list[str]) -> None:
    """`slipwai upgrade`, from anywhere: this copy replaced by the newest the forge has."""
    parser = argparse.ArgumentParser(
        prog="slipwai upgrade",
        description="Upgrade this slipwai to the newest version published to the forge",
        epilog="Asks the registry what the newest version is, then runs the upgrade for an installed "
        "command; a standalone executable and a checkout cannot be upgraded from inside themselves, so "
        "those are told what to do instead.",
    )
    parser.add_argument(
        "--check", action="store_true", help="say what is installed and what is published, and change nothing"
    )
    parser.add_argument(
        "--pre", action="store_true",
        help="count the snapshot of main (1.3.0.dev7) as a version to upgrade to; implied when this copy "
        "is one",
    )
    args = parser.parse_args(argv)
    kind = how_installed()
    prerelease = following_snapshots(args.pre)
    print(f"slipwai {VERSION}, installed as: {kind}", flush=True)
    try:
        name, url = index_of(Path(sys.prefix) / RECEIPT)
        newest = published(name, url, prerelease)
        if newest is None:
            counted = "" if prerelease else " (releases only: --pre counts the snapshot of main too)"
            print(f"the registry at {url} has no {PACKAGE} published{counted}: nothing to upgrade to.")
            return
        print(f"newest published: {newest}" + (" (snapshots counted)" if prerelease else ""))
        if key(newest) <= key(VERSION):
            print("this is already the newest published version.")
            return
        if kind in ("executable", "checkout"):
            print(guidance(kind))
            return
        command = upgrade_command(kind, prerelease)
        if args.check:
            print(f"would run: {' '.join(command)}")
            return
        print(f"running: {' '.join(command)}", flush=True)
        completed = subprocess.run(command)
    except GenerationError as error:
        parser.error(str(error))
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

"""What a project maker is told where no installed language ships the browser app they asked for, from one helper.

A browser app is a family's: the keel ships none, and a language ships each one it offers (`npm_workspace.frontends`,
`docs/frontend-protocol.md`). The language index can say which would: a family release's entry records the optional
members it answers (`answers`, D122, ADR 0010) and its fragment the frontends it ships. So the refusal of `generate
--frontend <name>` and of `add-frontend`, `slipwai list`'s Frontends rows and the interview's unavailable reason
all ask it the same question and say the same thing: the install line of the language that ships one, or — installed
and refused — the loader's line for it, or why none can be named (FR-015, SC-004).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .assets import this_command
from .catalog import CATALOG
from .language_directory import VARIABLE, directory, reinstalling
from .language_index import Index, Release, Unreachable, offered, read_index, snapshots
from .language_install import installed
from .language_plan import SCHEMA
from .loaded import refusals
from .npm_workspace import BROWSER
from .versions import key

NONE = "or generate with --frontend none"
#: What an index entry says it answers where it ships a browser app (`package_release.entry_for`).
MEMBER = "browser_apps"


@dataclass(frozen=True)
class Answering:
    """What can be said of the languages that would write a browser app: the index's URL (None where it could not be
    read, and `unreachable` says why), what is said of one installed — refused, by the loader's line, or loaded without
    the answer its index release has — and those to install."""

    url: str | None = None
    unreachable: str | None = None
    refused: str | None = None
    installable: dict[str, Release] = field(default_factory=dict)


def answering(url: str | None, offer: dict[str, Release]) -> Answering:
    """`offer`'s family releases whose index entry says they ship a browser app (`answers`, D122): one installed
    and refused, named by the loader's line — never an install line, which would say "already installed" — or
    the rest, to install."""
    found = {name: release for name, release in offer.items()  # a family is what requires none, as the loader says
             if "requires" not in release.fragment and MEMBER in release.answers}
    have = installed(directory())
    for name in [name for name in found if name in have]:
        line = next((said for said in refusals() if said.startswith(f"language {name} (")), None)
        if line is not None:
            return Answering(url, refused=f"{name} is installed and the loader refused it — {line}")
        return Answering(url, refused=without_the_answer(have[name].version, found[name]))
    return Answering(url, installable={name: release for name, release in found.items() if name not in have})


def without_the_answer(version: str, release: Release) -> str:
    """A family installed and loaded that does not answer, whose index release does: the move that brings that
    release — its upgrade, or where that is the version installed, taking it out and putting it back — and none under
    `SLIPWAI_LANGUAGES`, a directory that is the person's own."""
    name = release.name
    said = f"{name} {version} is installed without that answer, and the language index's {name} {release.version} " \
           "answers it"
    if os.environ.get(VARIABLE):
        return said
    newer = key(release.version) > key(version)
    return f"{said}: " + (f"{this_command()} language upgrade {name}" if newer else reinstalling(name))


def asked_of_the_index() -> Answering:
    """`answering`, of what the index offers this keel; where it cannot be read, its own text, so where its address
    came from is said as the index says it."""
    try:
        found = read_index()
    except Unreachable as error:
        return Answering(unreachable=str(error))
    return answering(found.url, offered(found, SCHEMA, snapshots()))


def install_line(name: str) -> str:
    return f"{this_command()} language install {name}"


def refusal(asked: str, generate: bool) -> str:
    """The refusal of a browser app (`asked` is what the verb was asked for), `generate`'s with its way out."""
    said, way_out = f"{asked} {BROWSER}", f"; {NONE}" if generate else ""
    answer = asked_of_the_index()
    if answer.unreachable is not None:
        return f"{said}; the language index could not be reached to say which does: {answer.unreachable}{way_out}"
    if answer.refused is not None:
        return f"{said}; {answer.refused}{way_out}"
    names = answer.installable
    if len(names) > 1:  # D116 #6's shape: an indented install line each
        return "\n".join([said + (f" ({NONE})" if generate else "") + "; install one:",
                          *(f"  {name} {release.version} — {install_line(name)}" for name, release in names.items())])
    if not names:  # no command to name, for none exists (D116 #7)
        return f"{said} or offered by the language index at {answer.url}{way_out}"
    (name,) = names
    return f"{said}; {name} ships it: {install_line(name)}{way_out}"


def unavailable(answer: Answering) -> str:
    """Why a browser app cannot be had, as `list`'s row and the interview's menu say it: each language the index says
    ships one, with its install line, as `list`'s axes do; nothing more where it offers none or cannot be read, which
    the Languages section, or the language question, has said already."""
    would = [answer.refused] if answer.refused is not None else [
        f"{name} ships it: {install_line(name)}" for name in answer.installable]
    return "; ".join(["no installed language ships it", *would])


def shipped() -> list[str]:
    """The frontends an installed language ships, in catalogue order: every one but `none`."""
    return [name for name in CATALOG["frontends"] if name != "none"]


def from_the_index(answer: Answering) -> list[str]:
    """The frontends the index's installable releases would ship, by their `frontends` blocks, in order."""
    return list(dict.fromkeys(name for release in answer.installable.values()
                              for name in release.fragment.get("frontends", {})))


def frontend_rows(found: Index | None, offer: dict[str, Release]) -> list[str]:
    """`slipwai list`'s Frontends rows: `none` bare, each installed one with the language that ships it, and — where
    none is installed — each the index offers, or one line saying why none can be had."""
    rows = ["  none", *(f"  {name} — written in {CATALOG['frontends'][name]['family']}" for name in shipped())]
    if shipped():
        return rows
    answer = answering(found.url, offer) if found is not None else Answering(unreachable="")
    why = unavailable(answer)
    return [*rows, *(f"  {name} — {why}" for name in from_the_index(answer))] if from_the_index(answer) else [
        *rows, f"  (a browser app: {why})"]


def frontend_menu() -> tuple[list[str], str, dict[str, str]]:
    """The interview's frontends; with none installed, `none` and those the index offers shown unavailable (D116 #4)."""
    if shipped():
        return list(CATALOG["frontends"]), CATALOG["default"]["frontend"], {}
    answer = asked_of_the_index()
    why = unavailable(answer)
    return ["none"], "none", {name: why for name in from_the_index(answer)}


def no_browser(frontend: str) -> str | None:
    """`generate --frontend <f>` for a frontend no installed language ships: its refusal, or None."""
    if frontend in CATALOG["frontends"]:
        return None
    return refusal(f"--frontend {frontend}", generate=True)

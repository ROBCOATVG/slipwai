"""`slipwai adopt --confirm`: a candidate becomes an application, and everything the record drives follows.

Brownfield adoption (#74; experimental as `AGENTS.md` defines the word), under [ADR 0003](../../docs/adr/
0003-a-wrapped-application-begins-as-a-candidate.md). `adopt` records every buildable directory the survey
found as a candidate and wraps none of them, because which of them is an application — and what it is called,
and what it owns — are questions the code answers and a terminal cannot ask well. This is where the answer
arrives: from `/ground`, with the code in front of the agent, or from a person who already knows.

It is a command rather than an instruction to edit `project.json`, for the reason `add-service` is one. The
manifest is the thing every generated file reads, so an entry with a mistyped target or a `kind` the factory
does not know is a repository whose gate fails in a way nobody can see the cause of. Here the entry is built
by the factory from the candidate the survey recorded, validated, and then `resurvey.refresh` regenerates
everything that reads it — the Makefile with the application's build in the gate, CI, the docs, the map.

Declining is the other half and is deliberately plain: the candidate is dropped, nothing is recorded in its
place, and a later `/survey` reports the directory as one that builds and has no record, which is what it is.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import resurvey
from .adopt import wrapped_app
from .ecosystems import EXTRA, TARGETS
from .errors import GenerationError
from .manifest import read_manifest
from .origin import WRAPPED_KINDS, adoption_of
from .services import App


@dataclass(frozen=True)
class Confirmed:
    """What one run of `--confirm` settled."""

    confirmed: list[str] = field(default_factory=list)
    declined: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    # How many applications the record holds after this run, which is not the same as how many it confirmed:
    # a run that only declines leaves the count where it was, and the gate still refuses when that is nought.
    applications: int = 0
    refreshed: resurvey.Refreshed | None = None


def candidate_named(candidates: list[dict], name: str) -> dict:
    found = next((row for row in candidates if row.get("name") == name), None)
    if found is None:
        listed = ", ".join(sorted(str(row.get("name")) for row in candidates)) or "none"
        raise GenerationError(
            f"no candidate is named `{name}`; this repository's outstanding candidates are: {listed}. "
            "`slipwai adopt --next` lists them with what the survey found."
        )
    return found


def as_application(candidate: dict, overrides: dict) -> App:
    """One candidate as the application the record will carry, with whatever the confirmer changed.

    Provenance is the point of the exercise: a field taken as the survey found it is `confirmed`, because
    somebody has now looked at the directory and said so, and a field the confirmer changed is `overridden`.
    Neither is `detected`, which is what the record said while the directory was only a candidate.
    """
    kind = overrides.get("kind") or candidate.get("kind") or "application"
    if kind not in WRAPPED_KINDS:
        raise GenerationError(f"--kind takes one of {', '.join(WRAPPED_KINDS)}, not {kind!r}")
    commands = {**(candidate.get("commands") or {}), **(overrides.get("commands") or {})}
    language = overrides.get("language") or candidate["language"]
    name = overrides.get("name") or candidate["name"]
    provenance = {
        "language": "overridden" if overrides.get("language") else "confirmed",
        "commands": "overridden" if overrides.get("commands") else "confirmed",
        # Keeping `application` confirms only that nobody has established what the directory is for, so it
        # stays the open question it was rather than becoming an answer by being passed over.
        "kind": "unrecorded" if kind == "application" else ("overridden" if overrides.get("kind") else "confirmed"),
    }
    app = wrapped_app(
        name, candidate["path"], language, commands, dict(candidate.get("toolchain") or {}),
        overrides.get("purpose"), provenance, kind=kind,
    )
    return App(
        app.name, app.path, app.kind, app.language, None, 0, generated=False, commands=app.commands,
        toolchain=app.toolchain, purpose=app.purpose, structure=overrides.get("structure"),
        provenance=app.provenance,
    )


def check_commands(commands: dict[str, str | None]) -> None:
    unknown = sorted(set(commands) - set(TARGETS) - set(EXTRA))
    if unknown:
        raise GenerationError(
            f"--command names {', '.join(unknown)}, and a recorded command is one of: {', '.join((*TARGETS, *EXTRA))}"
        )


def confirm(root: Path, confirming: dict[str, dict], declining: list[str]) -> Confirmed:
    """Move each named candidate into `deployables`, drop each declined one, and regenerate what reads them."""
    document = read_manifest(root, "slipwai adopt --confirm")
    adoption = adoption_of(document)
    if adoption is None:
        raise GenerationError(
            "this project was generated, not adopted, so it has no candidates: every application a generated "
            "project has, the factory made, and `slipwai add-service` adds another"
        )
    candidates = list(adoption.candidates)
    if not candidates:
        raise GenerationError(
            "this repository has no outstanding candidates — every buildable directory the survey found has "
            "been confirmed or declined. `slipwai adopt --refresh` reports one that has appeared since."
        )
    resurvey.refuse_uncommitted(root)
    named = [*confirming, *declining]
    for name in named:
        candidate_named(candidates, name)
    overlap = sorted(set(confirming) & set(declining))
    if overlap:
        raise GenerationError(f"--confirm and --decline both name {', '.join(overlap)}; one of them is the answer")
    settled: list[App] = []
    for name, overrides in confirming.items():
        check_commands(overrides.get("commands") or {})
        settled.append(as_application(candidate_named(candidates, name), overrides))
    taken = set(document.get("deployables") or {})
    for app in settled:
        if app.name in taken:
            raise GenerationError(
                f"this project already has an application called `{app.name}`; confirm the candidate under "
                f"another name with `--as`"
            )
        taken.add(app.name)
    remaining = [row for row in candidates if row["name"] not in named]
    if not remaining and not (set(document.get("deployables") or {}) | {app.name for app in settled}):
        raise GenerationError(
            "declining every candidate would leave this repository with no application at all, and the method "
            "is installed around applications: confirm at least one, or undo the adoption with "
            "`git reset --hard HEAD^`"
        )
    for app in settled:
        document.setdefault("deployables", {})[app.name] = app.record()
    if remaining:
        document["candidates"] = remaining
    else:
        document.pop("candidates", None)
    (root / "project.json").write_text(json.dumps(document, indent=2) + "\n")
    return Confirmed(
        confirmed=[app.name for app in settled], declined=list(declining),
        remaining=[row["name"] for row in remaining], applications=len(document.get("deployables") or {}),
        refreshed=resurvey.refresh(root, clean_checked=True),
    )


def report(done: Confirmed) -> str:
    lines = ["confirmed (experimental): what the record now says is an application here"]
    for name in done.confirmed:
        lines.append(f"  confirmed: `{name}` is an application; its build joins the gate")
    for name in done.declined:
        lines.append(
            f"  declined: `{name}` is not an application, and nothing is recorded in its place — a later "
            "/survey reports the directory as one that builds and has no record, which is what it is"
        )
    if done.remaining:
        gate = (
            "The gate runs now that something is confirmed; it refuses only while nothing is, so these are a "
            "question still open and not a stop"
            if done.applications else
            "Nothing is confirmed as an application yet, so the gate still refuses: confirming one is what "
            "gives it a subject"
        )
        lines.append(
            f"  outstanding: {len(done.remaining)} candidate(s) nobody has answered for — "
            f"{', '.join(done.remaining)}. {gate}. /ground asks about each"
        )
    else:
        lines.append("  outstanding: none; every buildable directory the survey found has been answered for")
    if done.refreshed is not None:
        lines.append(f"  {len(done.refreshed.rewritten)} file(s) rewritten from the record; nothing committed.")
    lines.append("Then: make verify, and commit the result as one change.")
    return "\n".join(lines)

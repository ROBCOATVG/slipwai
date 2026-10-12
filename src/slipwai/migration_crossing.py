"""The version 1 crossing: an installed base, declared renames, and preserved work in flight.

Only the final merge writes the real project. Preparatory replays and claim renames live in temporary
repositories; their commits are fetched as immutable offers. Nothing is pushed.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .adopt_report import survey_page
from .assets import NOTES, VERSION
from .layout import layout_of
from .logs import deck_path
from .manifest import apps_from_manifest
from .migration_claims import ahead, prepare, update
from .migration_flight import Flight, read, settings
from .migration_legacy import runtime
from .migration_merge import Tree, git, install, merge, modes, tracked, validate
from .migration_renames import moved, renamed, table
from .migration_result import Migration
from .replay import Replay, replay
from .survey import survey
from .versions import parse


def version(document: dict) -> str | None:
    provenance = document.get("generator") or {}
    value = provenance.get("updatedWith") or provenance.get("generatedWith")
    match = parse(value) if isinstance(value, str) else None
    return value if match is not None and match.group(1) == "1" else None


def answers(files: Tree) -> Tree:
    """Version 1's eventSourced answer remains explicit after the write-model axis arrived."""
    result = dict(files)
    document = json.loads(result["project.json"])
    for record in document.get("deployables", {}).values():
        if record.get("kind") == "service":
            selection = record.setdefault("selection", {})
            selection.setdefault("write-model", "events" if record.get("eventSourced") is True else "state")
    result["project.json"] = (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    return result


def catch_up(name: str, recorded: str, used: str, flight: Flight, layout, branches: dict[str, str]) -> str:
    proposed, unplaced = flight.counts
    command = f"python3 {layout.place('scripts/check-migration.py')}"
    return (f"# {name}: crossing from slipwai {recorded} to {VERSION}\n\n"
            "## First: confirm the fairways\n\n"
            f"{proposed} fairways proposed, {unplaced} slices in `unplaced`. "
            "Nothing can be claimed in those fairways until you confirm.\n\n"
            f"Run `{command}`. Place every `unplaced` slice in a named context on its chart; "
            "on the standard profile run `/chart`. Confirm the chart with "
            f"`{command} --confirm`, then run `make verify`.\n\n"
            "## Installed base\n\n"
            f"The base was reconstructed by installed slipwai {used}; the project recorded {recorded}. "
            "Snapshot fallbacks use the nearest available stable release below the snapshot.\n\n"
            "## Renames\n\n" + "".join(f"- `{row['from']}` → `{row['to']}` ({row['kind']}).\n" for row in table()) +
            "\n## Release and preserved records\n\n"
            "Confirm `project.json`'s releaseMode and state. Existing decision/adversary ids were frozen "
            "under `fairways/main/<feature>/`; ADRs retain their paths and numbers. Implementation "
            "was reconciled from trunk's slice merges, not the model's status field.\n\n" +
            ("## Claims to rebase\n\n" + "".join(
                f"- `git switch {ref.removeprefix('refs/heads/')} && git rebase main`\n" for ref in branches
            ) if branches else ""))


def seed(root: Path, flight: Flight) -> None:
    for feature, fairway, line in flight.logs:
        destination = root / deck_path(feature, fairway)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(descriptor, line.line().encode("utf-8"))
        finally:
            os.close(descriptor)


def crossing(root: Path, document: dict, *, with_claims: bool = False, check: bool = False):
    """Prepare the entire crossing before its first working-tree write, or report its read-only check."""
    recorded = version(document)
    assert recorded is not None
    branches = ahead(root, with_claims=with_claims)
    rows = table()
    own = answers(renamed(tracked(root), rows))
    with runtime(recorded) as legacy, tempfile.TemporaryDirectory(prefix="slipwai-crossing-") as scratch:
        staging = Path(scratch)
        base = staging / "base"
        legacy.replay(root, base)
        before = answers(renamed(tracked(base), rows))
        flight = read(root, document, legacy)
        if document.get("origin") == "adopted":
            path = layout_of(document).place("survey/survey.md")
            flight.files[path] = survey_page(survey(root), apps_from_manifest(document)).encode("utf-8")
        clone = staging / "project"
        git(root, "clone", "--quiet", "--no-hardlinks", str(root), str(clone))
        (clone / "project.json").write_bytes(own["project.json"])
        git(clone, "fetch", "--quiet", str(base), "main")
        installed_base = git(clone, "rev-parse", "FETCH_HEAD").decode().strip()
        offered = replay(clone, staging / "offered", base=installed_base)
        theirs = answers(tracked(offered.destination))
        model_name = layout_of(document).place("docs/event-model/model.yaml")
        if model_name in flight.files:
            # The populated model is project data, not the factory's empty starter. Its reconciliation
            # is prepared separately; template prose changes cannot turn every live model into a conflict.
            theirs[model_name] = own[model_name]
        result = merge(before, own, theirs)
        # Derived migration data is project work. Keep it out of the offered factory commit, so the next
        # ordinary replay cannot interpret it as factory output and delete it.
        for name, content in flight.files.items():
            if name not in result.conflicts:
                result.files[name] = content
        if "project.json" not in result.conflicts:
            settings(root, document, result.files)
        validate(root, result.files)
        message = catch_up(document["name"], recorded, legacy.used, flight, layout_of(document), branches)
        if check:
            conflict_names = ", ".join(sorted(result.conflicts)) or "none"
            return f"{message}\nMerge conflicts to resolve: {conflict_names}. No project file or claim branch changed."
        prepared = prepare(root, branches, rows)
        git(root, "fetch", "--quiet", str(offered.destination), "main")
        tip = git(root, "rev-parse", "FETCH_HEAD").decode().strip()
        executable = {moved(name, rows): mode for name, mode in modes(root).items()} | modes(offered.destination)
        install(root, result, tip, f"Migrate {document['name']} from {recorded} to slipwai {VERSION}", executable)
        update(root, prepared)
        seed(root, flight)
        notes = root / NOTES
        notes.parent.mkdir(parents=True, exist_ok=True)
        notes.write_text(message, encoding="utf-8")
        reported = Replay(root, offered.destination, offered.name, offered.files, offered.generated_with,
                          offered.base, offered.base_is_factory, offered.languages)
    conflicts = tuple(sorted(result.conflicts))
    return Migration(reported, recorded, conflicts, f"crossed from installed {legacy.used}; "
                     f"{len(result.files)} files, {len(conflicts)} conflicts")

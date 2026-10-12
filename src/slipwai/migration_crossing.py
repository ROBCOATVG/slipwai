"""The version 1 crossing: an installed base, declared renames, and preserved work in flight.

Only the final merge writes the real project. Preparatory replays and claim renames live in temporary
repositories; their commits are fetched as immutable offers. Nothing is pushed.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from .adopt_report import survey_page
from .assets import NOTES, VERSION
from .layout import layout_of
from .logs import Entry, deck_path
from .manifest import apps_from_manifest
from .migration_claims import ahead, prepare, update
from .migration_flight import Flight, read
from .migration_legacy import runtime
from .migration_merge import Tree, git, install, merge, modes, tracked, validate
from .migration_renames import moved, renamed, table
from .migration_result import Migration
from .migration_settings import settings
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


def catch_up(name: str, recorded: str, used: str, flight: Flight, layout, branches: dict[str, str],
             notes: list[str]) -> str:
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
            "was reconciled upward from trunk's slice merges: a slice trunk could not prove keeps the "
            "status the model recorded for it.\n\n" +
            # What a conflict stopped the crossing writing. On the page rather than in the run's output
            # alone, because this is the page the person reads after the merge is finished.
            ("## What this crossing could not do\n\n" + "".join(f"- {note}\n" for note in notes) + "\n"
             if notes else "") +
            ("## Claims to rebase\n\n" + "".join(
                f"- `git switch {ref.removeprefix('refs/heads/')} && git rebase main`\n" for ref in branches
            ) if branches else ""))


#: What marks a deck line as this crossing's own. A crossing that conflicts leaves a merge in progress and
#: the report offers `git merge --abort`; the deck logs are gitignored, so they survive that abort while
#: `.slipwai/migration.json` — tracked, and staged by `install` — does not. Without a key in the line
#: itself, the re-run appends a second `told` per queued message, a second `merged` per shipped slice and a
#: second `claimed`, to a log that is append-only by design: the board would show the person their own
#: words twice for ever and nothing could tell which copy was real.
CROSSED = "crossed"


def crossed(line: Entry) -> str:
    """One line's identity across runs: its kind and its fields, plus its own instant where it has one.

    A `told` carries the instant version 1 recorded, which is the person's and is the same on every re-run,
    and two identical messages said at different times are two messages. Every other kind is stamped when
    it is written, so the clock is left out and the second run recognises what the first wrote.
    """
    body = {"kind": line.kind, **line.fields} | ({"t": line.t} if line.t else {})
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return digest.hexdigest()[:16]


def already(path: Path) -> set[str]:
    """The keys of the lines an earlier crossing of this project already wrote to this deck log.

    A line that is not this crossing's — a captain's, or one torn by something else — is left out rather
    than refused: the only thing being decided here is what has already been said once.
    """
    if not path.is_file():
        return set()
    found = set()
    for text in path.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
        try:
            body = json.loads(text)
        except ValueError:
            continue
        if isinstance(body, dict) and isinstance(body.get(CROSSED), str):
            found.add(body[CROSSED])
    return found


def seed(root: Path, flight: Flight) -> None:
    """Append what version 1 left behind, once per line however many times the crossing is re-run."""
    seen: dict[Path, set[str]] = {}
    for feature, fairway, line in flight.logs:
        destination = root / deck_path(feature, fairway)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination not in seen:
            seen[destination] = already(destination)
        key = crossed(line)
        if key in seen[destination]:
            continue
        seen[destination].add(key)
        stamped = replace(line, fields={**line.fields, CROSSED: key})
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(descriptor, stamped.line().encode("utf-8"))
        finally:
            os.close(descriptor)


def crossing(root: Path, document: dict, *, with_claims: bool = False, check: bool = False):
    """Prepare the entire crossing before its first working-tree write, or report its read-only check."""
    recorded = version(document)
    assert recorded is not None
    # A check writes nothing, so an open claim is reported rather than refused over: `--check` exists to
    # say what the crossing would do, and that is exactly what a project with a claim in flight needs.
    blocking: list[str] = []
    branches = ahead(root, with_claims=with_claims, notes=blocking if check else None)
    rows = table()
    own = answers(renamed(tracked(root), rows))
    with runtime(recorded) as legacy, tempfile.TemporaryDirectory(prefix="slipwai-crossing-") as scratch:
        staging = Path(scratch)
        base = staging / "base"
        legacy.replay(root, base)
        before = answers(renamed(tracked(base), rows))
        flight = read(root, document, legacy,
                      claims={ref.removeprefix("refs/heads/slice/") for ref in branches})
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
        # A conflicted `project.json` is unreadable, so the keys that live in it wait for the person. Every
        # other setting still applies: the `hoisted` dates the strike rule counts from, the model table's
        # review role, and the `.slipwai/logs/` ignore rule `seed` needs twelve lines below this.
        left = settings(root, document, result.files, contested="project.json" in result.conflicts)
        validate(root, result.files)
        message = catch_up(document["name"], recorded, legacy.used, flight, layout_of(document),
                           branches, left)
        if check:
            conflict_names = ", ".join(sorted(result.conflicts)) or "none"
            stopping = "".join(f"\n`slipwai migrate` would refuse: {note}" for note in blocking)
            return (f"{message}\nMerge conflicts to resolve: {conflict_names}. "
                    f"No project file or claim branch changed.{stopping}")
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

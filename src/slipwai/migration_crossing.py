"""The version 1 crossing: an installed base, declared renames, and preserved work in flight.

Only the final merge writes the real project. Preparatory replays and claim renames live in temporary
repositories; their commits are fetched as immutable offers. Nothing is pushed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from .adopt_report import survey_page
from .assets import NOTES, VERSION
from .catch_up_page import archive, set_up, stated
from .infra_check import check as infra_check
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


#: What a crossing never writes and never takes away. `infra/` is the one directory whose files are a map of
#: things that already exist: a Terraform resource address is state, and a factory that rewrites one is a
#: factory proposing to replace an account's user pool, its database or its network. Nothing the keel knows
#: about a project tells it which of those are real.
#:
#: It is not a hypothetical. A crossing restored one of the factory's own identity stacks under its 2.x
#: name — a file the project had deleted months before, having written its own beside it — because a rename
#: turns "ours deleted it" into a path the base and the offering share and the project does not. That deploy
#: stopped on a duplicate declaration, which is the harmless end of what this class of change can do: the
#: same merge could as easily have offered a plan that destroyed every account in a sign-in directory.
#:
#: So the project's own `infra/` crosses untouched, and what this version would have written there is named
#: in the catch-up notes for a person to take deliberately, or not.
INFRA = "infra"


def infrastructure(name: str) -> bool:
    """Whether this path is the project's infrastructure, which a crossing is not allowed to decide about.

    A prefix and not a layout question: `infra/` is not one of the delivery roots, so it sits at the root in
    every layout the keel writes (`layout.place`).
    """
    return name == INFRA or name.startswith(f"{INFRA}/")


def off_infrastructure(before: Tree, theirs: Tree) -> tuple[Tree, Tree, list[str]]:
    """The two factory sides of the merge with `infra/` taken out of both, and what that declined to do.

    Out of the offering, so nothing is written there; and out of the base, so a path the project deleted
    cannot come back as "theirs added a file" — which is precisely how a renamed one did.

    The project's own side is untouched and never passed here: with neither factory side holding an `infra/`
    path, `merge` sees the project's as the only version of it and keeps it, which is the whole rule.
    """
    declined = sorted(name for name in set(before) | set(theirs)
                      if infrastructure(name) and before.get(name) != theirs.get(name))
    return ({name: body for name, body in before.items() if not infrastructure(name)},
            {name: body for name, body in theirs.items() if not infrastructure(name)},
            declined)


#: What delimits a backing-service region, in the one spelling every copy of it uses: the generated
#: `scripts/backing-services.py` that prunes these, the files it prunes, and this. A region two features
#: both need names both, `keycloak|users-keycloak`, so the names are split on the bar.
MARKER = re.compile(rb"backing-service:([a-z0-9|-]+):begin")


def blocks(body: bytes) -> set[str]:
    """Which backing-service blocks this file implements, by the markers it carries."""
    return {name for found in MARKER.findall(body) for name in found.decode("ascii").split("|")}


def implemented_elsewhere(own: Tree, theirs: Tree) -> tuple[Tree, list[str]]:
    """The offering, with every file dropped whose blocks the project already implements under another name.

    A block is identified by its marker and never by the file it sits in. The factory's file and the
    project's replacement for it both say `backing-service:users-keycloak`, and that is the fact worth
    reading: one block, implemented twice, is not a merge — it is two of something there may only be one of.

    It matters because of *renames*. A file the project deleted, offered back under a 2.x name, is a path
    the project has never had: there is no delete to conflict with, so it merges clean as an addition and
    lands beside the project's own implementation. That happened, to a stack describing a sign-in
    directory, and the deploy stopped on a duplicate declaration. The rename table is what saves the
    ordinary case — it moves the project's own file to the new name first, so the offering meets it rather
    than joining it — and this is what saves the case where the project's answer is not the factory's file
    at all, under any name.

    Only additions, and only where *every* block the file carries is already implemented: a file that
    brings something new as well as something present is a question for a person, not a thing to drop.
    """
    mine = {name: blocks(body) for name, body in own.items()}
    kept, dropped = {}, []
    for name, body in theirs.items():
        carried = blocks(body)
        if name in own or not carried:
            kept[name] = body
            continue
        holders = sorted(where for where, found in mine.items() if where != name and carried <= found)
        if holders:
            dropped.append(f"`{name}` — `{'`, `'.join(sorted(carried))}` is already implemented by "
                           f"`{'`, `'.join(holders)}`")
            continue
        kept[name] = body
    return kept, dropped


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
             notes: list[str], infra: Sequence[str] = (), twice: Sequence[str] = (),
             conflicts: Sequence[str] = ()) -> str:
    proposed, unplaced = flight.counts
    command = f"python3 {layout.place('scripts/check-migration.py')}"
    # The same opening section an ordinary migration's page has: a crossing that conflicts leaves the same
    # three steps after the resolving commit, and this is the page the person reads once it is finished.
    return (f"# {name}: crossing from slipwai {recorded} to {VERSION}\n" + "\n".join(set_up(conflicts)) + "\n\n"
            "## Then: confirm the fairways\n\n"
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
            # What the crossing would have done to `infra/` and did not. Named rather than silently skipped:
            # a person who upgrades and later finds the factory's stack has moved on should find out here,
            # with the list in front of them, rather than from a plan that proposes to replace a database.
            ("## Infrastructure, left alone\n\n"
             "A crossing does not write `infra/`: those files describe resources that already exist, and "
             "which of them are real is not something this keel can know. This version would have changed "
             "the following, and yours are untouched — take any of it deliberately, reading `tofu plan` "
             "before you apply.\n\n" + "".join(f"- `{path}`\n" for path in infra) + "\n"
             if infra else "") +
            # A block this version writes that the project already answers its own way. Named for the same
            # reason: the factory's file is not gone from this version, and somebody may still want it.
            ("## Blocks you already implement\n\n"
             "These files were not taken: each carries a `backing-service:` block that this project already "
             "implements elsewhere, and two implementations of one block is not something a merge can "
             "resolve.\n\n" + "".join(f"- {line}\n" for line in twice) + "\n"
             if twice else "") +
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


def already(path: Path) -> Counter[str]:
    """How many lines carrying each key an earlier crossing of this project wrote to this deck log.

    Counted rather than collected, so that two lines version 1 really does hold twice — the same words at
    the same instant, which `cruise-told.jsonl` and `cruise-inbox.jsonl` between them can give — cross as
    two lines and are recognised as two on the re-run. A line that is not this crossing's is left out
    rather than refused: the only thing being decided here is what has already been said once.
    """
    found: Counter[str] = Counter()
    if not path.is_file():
        return found
    for text in path.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
        try:
            body = json.loads(text)
        except ValueError:
            continue
        if isinstance(body, dict) and isinstance(body.get(CROSSED), str):
            found[body[CROSSED]] += 1
    return found


def seed(root: Path, flight: Flight) -> None:
    """Append what version 1 left behind, once per line however many times the crossing is re-run."""
    seen: dict[Path, Counter[str]] = {}
    for feature, fairway, line in flight.logs:
        destination = root / deck_path(feature, fairway)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination not in seen:
            seen[destination] = already(destination)
        key = crossed(line)
        if seen[destination][key]:
            seen[destination][key] -= 1
            continue
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
        # Before anything is merged, and on both factory sides of it.
        before, theirs, untouched = off_infrastructure(before, theirs)
        theirs, twice = implemented_elsewhere(own, theirs)
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
        # A conflicted file is unreadable, so the keys that live in it wait for the person — the whole set
        # is passed rather than `project.json` alone, because the model table conflicts too. Every other
        # setting still applies: the `hoisted` dates the strike rule counts from, the model table's review
        # role, and the `.slipwai/logs/` ignore rule `seed` needs twelve lines below this.
        left = settings(root, document, result.files, conflicts=result.conflicts)
        validate(root, result.files)
        message = catch_up(document["name"], recorded, legacy.used, flight, layout_of(document),
                           branches, left, untouched, twice, tuple(sorted(result.conflicts)))
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
        # Last, and never a refusal: the merge is committed by the time this reads anything. The project's
        # own gate cannot run this — `make verify` has no provider plugins and no credential by design — so
        # a crossing is the one moment between a tree being rewritten and a runner finding out.
        for finding in infra_check(root):
            print(f"infra: {finding}")
        archive(root)
        notes = root / NOTES
        notes.parent.mkdir(parents=True, exist_ok=True)
        notes.write_text(f"{message}\n{stated(recorded, VERSION, datetime.now(UTC))}\n", encoding="utf-8")
        if not result.conflicts:
            from .project.intake_cleanup import write_proposal
            write_proposal(root)
        reported = Replay(root, offered.destination, offered.name, offered.files, offered.generated_with,
                          offered.base, offered.base_is_factory, offered.languages)
    conflicts = tuple(sorted(result.conflicts))
    return Migration(reported, recorded, conflicts, f"crossed from installed {legacy.used}; "
                     f"{len(result.files)} files, {len(conflicts)} conflicts")

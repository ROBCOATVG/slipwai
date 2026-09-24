"""`adopt --refresh`: survey an adopted repository again, and reconcile what is found with what was recorded.

Brownfield adoption (experimental as `AGENTS.md` defines the word) records facts, not answers, and code
changes: a build gains a linter, a runtime pin moves, a schema tool arrives, a directory starts building. So
the survey is re-run and its findings meet `project.json` under one rule, which is the rule provenance
exists for. A fact recorded as `detected` is the tree's own word and is refreshed in place — and every file
that reads it is regenerated, the way `add-service` regenerates what the manifest drives. A fact a person
`confirmed` or `overrode` is theirs: a detection that disagrees with it is *reported*, side by side with the
record, and never applied. A directory that builds and has no record is reported, not added — whether it is
part of this system is a decision.

Nothing is committed: like `add-service`, this writes and leaves the result to be read and committed as one
change, so it refuses an unclean tree.
"""
from __future__ import annotations

import dataclasses
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .adopt import STRUCTURE_PAGE, SURVEY_PAGE, facts
from .adopt_report import survey_page
from .convergence import reconciled
from .errors import GenerationError
from .layout import layout_of
from .manifest import apps_from_manifest, read_manifest, wrote_here
from .origin import Adoption, adoption_of
from .platform import with_platform
from .programme import expired
from .project.adopted import WRITTEN
from .project.structure_page import structure_page
from .scaffold import FACTORY_IDENTITY, project_files
from .services import App, wrapped_of
from .strategy import with_recommendation
from .structure import structure
from .survey import Survey, survey
from .toolkit import executable_paths
from .wrappers import wrapper_lines, write_wrappers


@dataclass(frozen=True)
class Refreshed:
    """What a re-survey changed, questioned and noticed."""

    refreshed: list[str] = field(default_factory=list)
    disagreements: list[str] = field(default_factory=list)
    unwrapped: list[str] = field(default_factory=list)
    rewritten: list[str] = field(default_factory=list)
    # Files the factory wrote that the record no longer drives — a gate for a forge the record left — and so removed.
    removed: list[str] = field(default_factory=list)
    # Files the factory wrote that a person took over by deleting their line from `.written`: left alone, and said.
    owned: list[str] = field(default_factory=list)
    # Build wrappers written where a Maven or Gradle build had none, as report lines (`wrappers.py`).
    wrappers: list[str] = field(default_factory=list)


def refuse_uncommitted(root: Path) -> None:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False)
    if status.returncode == 0 and status.stdout.strip():
        raise GenerationError(
            "this repository has uncommitted changes; commit or stash them first, so that `git checkout .` and "
            "`git clean -fd` undo exactly what the re-survey wrote and nothing else"
        )


def reconciled_app(app: App, found: Survey, done: Refreshed) -> App:
    """One wrapped application against the fresh survey: refreshed where detected, questioned where decided."""
    fresh = next((root for root in found.roots if root.path == app.path), None)
    if fresh is None:
        done.disagreements.append(
            f"{app.name}: nothing the survey recognises builds at `{app.path}` any more; its record stands as written"
        )
        return app
    changes: dict[str, object] = {}
    # The eight targets follow the tree; a `test-full` or any other key a person added stays.
    kept = {k: v for k, v in (app.commands or {}).items() if k not in fresh.found.commands}
    now = {"language": fresh.found.language, "commands": {**dict(fresh.found.commands), **kept}}
    for name, current in (("language", app.language), ("commands", dict(app.commands or {}))):
        if current == now[name]:
            continue
        if app.provenance.get(name, "detected") == "detected":
            changes[name] = now[name]
            done.refreshed.append(f"{app.name}: {name} refreshed from `{fresh.found.evidence}`")
        else:
            done.disagreements.append(
                f"{app.name}: {name} was {app.provenance[name]} as {json.dumps(current)}, and `{fresh.found.evidence}` "
                f"now says {json.dumps(now[name])}; the record stands until you decide"
            )
    toolchain = {**fresh.found.toolchain, "ecosystem": fresh.found.ecosystem}
    if fresh.found.packaging:
        toolchain["packaging"] = fresh.found.packaging
    recorded = dict(app.toolchain or {})
    # The ecosystem, kind and packaging are the tree's. The version is the one fact a person can know and the tree
    # not — the first real adoption's Spring 3.2 WAR pinned nothing, and every refresh reset a confirmed `8` to
    # nothing — so under `provenance.toolchain` it stands, and a tree that later pins another is a disagreement.
    if app.provenance.get("toolchain", "detected") != "detected":
        pinned = toolchain.get("version", "")
        toolchain["version"] = recorded.get("version", "")
        if pinned and pinned != toolchain["version"]:
            done.disagreements.append(
                f"{app.name}: toolchain.version was {app.provenance['toolchain']} as "
                f"{json.dumps(toolchain['version'])}, and `{fresh.found.evidence}` now pins {json.dumps(pinned)}; "
                "the record stands until you decide"
            )
    if recorded != toolchain:
        changes["toolchain"] = toolchain
        done.refreshed.append(f"{app.name}: toolchain refreshed from `{fresh.found.evidence}`")
    # What it is for: a file's word follows the tree, an unrecorded one is filled in the moment a file says, and a
    # person's word is theirs.
    provenance = dict(app.provenance)
    if fresh.role and fresh.role != app.kind and app.provenance.get("kind", "unrecorded") in ("detected", "unrecorded"):
        changes["kind"] = fresh.role
        provenance["kind"] = "detected"
        done.refreshed.append(f"{app.name}: kind refreshed to `{fresh.role}` from `{fresh.role_evidence}`")
    elif fresh.role and fresh.role != app.kind:
        done.disagreements.append(
            f"{app.name}: kind was {app.provenance['kind']} as `{app.kind}`, and `{fresh.role_evidence}` now says "
            f"`{fresh.role}`; the record stands until you decide"
        )
    if provenance != dict(app.provenance):
        changes["provenance"] = provenance
    return dataclasses.replace(app, **changes) if changes else app  # type: ignore[arg-type]


def platform_moves(was: dict, now: dict) -> list[str]:
    """Every product read for the same application under both records at a different version: `Spring Framework
    moved 3.2.8 → 4.3.30 for shop`. A product that appeared or went is not a move; the survey page says those."""
    def versions(record: dict) -> dict[tuple[str, str], tuple[str, str]]:
        return {(p.get("app", ""), p.get("product", "")): (p.get("title", p.get("product", "")), p.get("version", ""))
                for p in record.get("products") or []}

    before, after = versions(was), versions(now)
    return [
        f"{after[key][0]} moved {before[key][1]} → {after[key][1]} for {key[0]}"
        for key in sorted(before.keys() & after.keys()) if before[key][1] != after[key][1]
    ]


def reconciled_home(record: dict, key: str, proposed: str, what: str, done: Refreshed) -> dict:
    """The database, infrastructure, ci or release record against the fresh proposal, under the same rule — and
    an `unrecorded` fact is the tree's to fill the moment it can say, with `detected` provenance from then on."""
    if record.get(key) == proposed:
        return record
    if record.get("provenance", "detected") in ("detected", "unrecorded"):
        done.refreshed.append(f"{what}: {key} refreshed to `{proposed}`")
        provenance = "unrecorded" if proposed == "unknown" else "detected"
        return {**record, key: proposed, "provenance": provenance}
    done.disagreements.append(
        f"{what}: {key} was {record['provenance']} as `{record.get(key)}`, and the tree now proposes `{proposed}`; "
        "the record stands until you decide"
    )
    return record


def refresh(root: Path, clean_checked: bool = False) -> Refreshed:
    """Survey again, reconcile, regenerate what the record drives, and rewrite the survey page.

    `clean_checked` is for a caller that has already refused an unclean tree and has since written to it on
    purpose — `confirm`, which edits `project.json` and then needs every file the record drives to follow.
    """
    document = read_manifest(root, verb="adopt --refresh")
    adoption = adoption_of(document)
    if adoption is None:
        raise GenerationError("this project was generated, not adopted, so there is nothing to re-survey")
    if not clean_checked:
        refuse_uncommitted(root)
    apps = apps_from_manifest(document, allow_empty=True)
    layout = layout_of(document)
    found = survey(root)
    done = Refreshed()
    updated = [reconciled_app(app, found, done) if not app.generated else app for app in apps]
    done.wrappers.extend(wrapper_lines(write_wrappers(root, wrapped_of(updated)), updated))
    wrapped_paths = {app.path for app in wrapped_of(apps)}
    done.unwrapped.extend(
        f"`{root_.path}` builds ({root_.found.ecosystem}, {root_.found.language}, from `{root_.found.evidence}`) and "
        "has no record"
        for root_ in found.roots if root_.path not in wrapped_paths
    )
    database = reconciled_home(adoption.database, "schema", found.schema_home, "database", done)
    infrastructure = reconciled_home(adoption.infrastructure, "home", found.infrastructure_home, "infrastructure", done)
    # A record from before the forge and the release path were recorded proposes them fresh, as `adopt --yes` would.
    forge, release_path = found.forge[0], found.release_path or "unknown"
    recorded_ci = adoption.ci or {"forge": forge, "provenance": "detected"}
    # The survey leaves out what the factory wrote, so once the gate is the only CI in the tree a fresh reading says
    # `none` — and a `detected` forge then walked to `none`, which deleted the gate, and back when a workflow of the
    # repository's own appeared. The gate this factory wrote is CI configuration in the tree: the forge it was
    # written for stands while it is there.
    if forge == "none" and recorded_ci.get("gate") and recorded_ci.get("forge") not in (None, "none"):
        forge = recorded_ci["forge"]
    recorded_release = adoption.release or {
        "path": release_path, "provenance": "detected" if found.release_path else "unrecorded"
    }
    ci = reconciled_home(recorded_ci, "forge", forge, "ci", done)
    release = reconciled_home(recorded_release, "path", release_path, "release", done)
    # The evidence lists are the tree's own and follow it; the homes above are the answers.
    refreshed_facts = facts(found, _answers(document, database, infrastructure, ci, release), layout)
    # `candidates` and `agent` are carried, not re-derived: a re-survey reads the tree, and neither is a fact
    # about the tree. A candidate is a question nobody has answered yet and an answered one is gone from the
    # list; which agent gets the material is `./init`'s. Rebuilding the record without them left `project.json`
    # holding two candidates while the `/ground` it regenerated had dropped the section that asks about them —
    # a generated file disagreeing with the record it is generated from, which is the one thing this must not do.
    after_adoption = Adoption(
        adoption.why, refreshed_facts.database, refreshed_facts.infrastructure, refreshed_facts.survey,
        ci=refreshed_facts.ci, release=refreshed_facts.release,
        candidates=list(adoption.candidates), agent=dict(adoption.agent),
    )
    # Quick wins are read from the tree again: what was fixed is said, and what remains stays on the survey page.
    was = {w.get("where") for w in (adoption.survey or {}).get("quickWins") or []}
    now = {w.get("where") for w in refreshed_facts.survey.get("quickWins") or []}
    if was - now:
        done.refreshed.append(f"quick wins: {len(was - now)} fixed since the last survey; {len(now)} remain")
    elif now - was:
        done.refreshed.append(f"quick wins: {len(now - was)} new since the last survey; {len(now)} in all")
    # The platform is read against today, every time: a runtime that left support since the last survey is said. But
    # it is *dated* only when something moved — a product, a version, a status, the table — since a date that changed
    # on every run rewrote `project.json`, the architecture view and the map with no fact behind the change.
    after_adoption = with_platform(root, after_adoption, updated)
    was_platform, is_platform = adoption.platform or {}, after_adoption.platform or {}
    if was_platform.get("dated") and (was_platform.get("snapshot"), was_platform.get("products")) == (
        is_platform.get("snapshot"), is_platform.get("products")
    ):
        after_adoption = dataclasses.replace(after_adoption, platform={**is_platform, "dated": was_platform["dated"]})
    newly = {p["title"] + " " + p["version"] for p in expired(after_adoption.platform)} - {
        p["title"] + " " + p["version"] for p in expired(adoption.platform)
    }
    if newly:
        done.refreshed.append(f"platform: out of support since the last survey: {', '.join(sorted(newly))}")
    # A version that moved is a platform slice, and the Platform row's `planned` is where one is announced. The
    # second FoodDelivery adoption moved Spring 3.2 to 4.3 inside a slice titled "the application runs", and nothing
    # said so until a reviewer read the pom: now the survey does, as a disagreement until the row or an ADR owns it.
    planned = next((row.get("planned") for row in (adoption.convergence or [])
                    if isinstance(row, dict) and row.get("axis") == "platform"), None)
    for move in platform_moves(was_platform, is_platform):
        if planned:
            done.refreshed.append(f"platform: {move}, as the Platform row planned ({planned})")
        else:
            done.disagreements.append(
                f"platform: {move}, and the Platform row planned nothing — a platform move is a slice of its own on "
                "that row, never inside another; name it in the row's `planned` or an ADR, or put it back"
            )
    after_adoption = with_recommendation(root, layout, after_adoption, updated)
    after_adoption = dataclasses.replace(
        after_adoption, convergence=reconciled(adoption.convergence, after_adoption.convergence, done.refreshed)
    )

    arguments = (document["name"], document["profile"], document["target"])
    before = project_files(*arguments, apps, layout, adoption)
    after = project_files(*arguments, updated, layout, after_adoption)
    executables = {layout.place(path) for path in executable_paths(document["profile"], updated)}
    # A file the factory wrote before, still on disk and no longer listed in `.written`, is the repository's own from
    # then on: taking one over is deleting its line, and the factory leaves it alone and says so — the third real
    # adoption could not edit the gate's workflow for its own default branch and had to add a second one beside it.
    listing = root / layout.under(WRITTEN)
    listed = set(listing.read_text().split()) if listing.is_file() else set()
    owned = {
        relative for relative in after
        if listing.is_file() and relative in before and relative not in listed and relative != layout.under(WRITTEN)
        and (root / relative).is_file()
    }
    if owned:
        done.owned.extend(sorted(owned))
        after[layout.under(WRITTEN)] = "".join(
            f"{path}\n" for path in sorted(set(after[layout.under(WRITTEN)].split()) - owned)
        )
    # Rewritten wherever the disk differs from what the record now drives — not wherever the record moved, since a
    # person edits `project.json` by hand (a confirmed version, a row moved) and the files it drives have to follow.
    for relative, content in after.items():
        path = root / relative
        if relative == "project.json" or relative in owned or (path.is_file() and path.read_text() == content):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline="")
        path.chmod(0o755 if relative in executables else 0o644)
        done.rewritten.append(relative)
    # What the factory wrote before and does not write now is removed with its reason, not left in the tree: the
    # first real adoption's refresh dropped the gate from `.written` when the forge read `none`, and the next survey
    # found the orphaned workflow and took it for the repository's own CI.
    for relative in sorted((set(before) | listed) - set(after) - owned):
        path = root / relative
        if path.is_file():
            path.unlink()
            done.removed.append(f"`{relative}` — the factory wrote it, and the record no longer calls for it")
            parent = path.parent
            while parent != root and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    manifest = json.loads(after["project.json"])
    for app in wrapped_of(updated):
        document["deployables"][app.name] = manifest["deployables"][app.name]
    for key in ("database", "infrastructure", "ci", "release", "platform", "strategy", "convergence", "survey"):
        document[key] = manifest[key]
    document["generator"] = wrote_here(document.get("generator"))
    # Four files follow the record as it now stands rather than the assembly before: the manifest, the survey
    # page, the architecture view, and the map's page — a row a person moved by hand is what the page catches up with.
    convergence_page = layout.under("docs/convergence.md")
    shape = structure(root, updated, layout.delivery, FACTORY_IDENTITY["GIT_AUTHOR_EMAIL"])
    view = structure_page(shape, after_adoption, layout)
    for relative, content in (("project.json", json.dumps(document, indent=2) + "\n"),
                              (layout.under(SURVEY_PAGE), survey_page(found, updated)),
                              (layout.under(STRUCTURE_PAGE), view),
                              (convergence_page, after[convergence_page])):
        path = root / relative
        if path.is_file() and path.read_text() == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        done.rewritten.append(relative)
    return done


def _answers(document: dict, database: dict, infrastructure: dict, ci: dict, release: dict):
    """The re-survey's answers, for `facts`: the homes, forge and release path as reconciled, the rest as recorded."""
    from .adopt import Answers

    return Answers(
        document["name"], document["profile"], document["target"], layout_of(document).delivery,
        document.get("why"), [], database, infrastructure, ci, release,
        # Which coding agent the material is projected into is not a fact about the tree, so a re-survey does
        # not re-read it: it is carried exactly as recorded, and `./init --integration` is what changes it.
        agent=document.get("agent", {}),
    )


def report(done: Refreshed) -> str:
    lines = ["re-surveyed (experimental): what the tree says, against what project.json records"]
    lines += [f"  refreshed: {line}" for line in done.refreshed] or ["  refreshed: nothing; every detected fact stands"]
    lines += [f"  disagrees: {line}" for line in done.disagreements]
    lines += [f"  not wrapped: {line}" for line in done.unwrapped]
    lines += [f"  removed: {line}" for line in done.removed]
    lines += [f"  owned: `{line}` — not in .written, so it is yours and was left alone; a newer factory's change to it "
              "meets yours in slipwai migrate's three-way merge" for line in done.owned]
    lines += [f"  {line}" for line in done.wrappers]
    lines += [
        "",
        f"{len(done.rewritten)} file(s) rewritten; nothing committed. `git diff` shows the record and what it drives.",
    ]
    if done.disagreements:
        lines.append(
            "A disagreement is a decision: put both sides to the user, record the answer in project.json with honest "
            "provenance, and run this again so the files follow."
        )
    if done.unwrapped:
        lines.append(
            "A directory that builds and has no record is added only on purpose: a `\"generated\": false` record in "
            "project.json's deployables, then this command again."
        )
    lines.append("Then: make verify, and commit the result as one change.")
    return "\n".join(lines)

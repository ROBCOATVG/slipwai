"""The convergence map: where an adopted repository stands on each ladder a generated project sits at the top of.

A generated project starts at the top of every ladder and the method keeps it there. A repository the method was
installed around (brownfield adoption) starts wherever it is, and the loop's job is to climb one rung per slice until
the two are the same thing. This is the record of where it is: one row per axis — `rung`, the `target` a generated
project sits at, the `evidence`, where the row came from, and what slice is `planned` to move it. Written by `adopt`
from what the survey and the person established, refreshed by `adopt --refresh` under the provenance rule every other
fact follows, rendered as `docs/convergence.md`, and held by `scripts/check-convergence.py`, which fails a row the tree
contradicts.

Nothing here is a default that looks like an answer. A rung is claimed only from a fact the record holds — a
recorded test command, a declared layout, a release path a file or a person gave — and a rung nothing
establishes reads as the ladder's floor with `unrecorded` provenance, which the gate passes with a line and
`/sail` asks about. A person moves a row by editing `project.json`; the provenance then says so.
"""
from __future__ import annotations

from dataclasses import dataclass

from .origin import OLD_AXES, Adoption
from .services import App, wrapped_of


@dataclass(frozen=True)
class Axis:
    """One ladder: its rungs from the floor up, the rung a generated project sits at, and what each rung means."""

    key: str
    title: str
    rungs: tuple[str, ...]
    target: str
    means: dict[str, str]

    def index(self, rung: str) -> int:
        return self.rungs.index(rung)


AXES: tuple[Axis, ...] = (
    Axis("path-to-production", "Path to production",
         ("unknown", "manual", "scripted", "pipeline", "one-path", "pipeline-decides"), "pipeline-decides", {
             "unknown": "nobody has said how a change reaches production",
             "manual": "by hand: files copied, a console clicked, a package installed",
             "scripted": "somebody runs a script that deploys it",
             "pipeline": "a CI job deploys it, on some trigger",
             "one-path": "every change reaches production the same automated way, and no other",
             "pipeline-decides": "the pipeline decides releasability; artefacts immutable, rollback on demand, "
                                 "configuration shipped with the artefact",
         }),
    Axis("integration", "Integration", ("unknown", "branches", "trunk", "continuous"), "continuous", {
        "unknown": "nobody has said how work is integrated",
        "branches": "long-lived branches, merged when a feature is done",
        "trunk": "trunk-based: every branch lives less than a day",
        "continuous": "integrated at least daily, the build stops on red, CI runs on every commit on this forge",
    }),
    Axis("safety-net", "Safety net", ("none", "tests-exist", "tests-pass", "fast", "pinned", "mutation-measured"),
         "mutation-measured", {
             "none": "no test command is recorded for any application that was here",
             "tests-exist": "a test suite is recorded; whether it is green is not established",
             "tests-pass": "the suite is green in the gate, with no quarantine",
             "fast": "the suite is deterministic and fast enough to run on every change",
             "pinned": "the seams a slice touches are pinned by `/characterise` before they change",
             "mutation-measured": "the suite's strength is measured by mutation testing",
         }),
    Axis("structure", "Structure", ("as-found", "named", "laid-out", "hexagonal", "typed"), "typed", {
        "as-found": "at least one buildable directory's role — service, library, tool, tests — is not established",
        "named": "every application is recorded as what it is",
        "laid-out": "every application lives under `apps/`, the layout a generated project has — or at a Go module's "
                    "root, which is its import path and lives where it stands",
        "hexagonal": "every application declares the hexagonal layers and the import gate holds it to them",
        "typed": "every application has a type check the gate runs",
    }),
    # First whatever the strategy (`docs/strategies/build-floor.md`): nothing can be pinned, upgraded or replaced
    # against a build that only works on one machine.
    Axis("build", "Build", ("undeclared", "declared", "pinned", "reproducible", "inventoried"), "inventoried", {
        "undeclared": "a build does not declare what it depends on: committed jars or binaries, or a build tool with "
                      "no dependency manager (Ant)",
        "declared": "every dependency is declared by name and version and fetched, but a tool version or a compile "
                    "target is left to whatever is installed, or a lockfile is missing",
        "pinned": "tools through a wrapper or a pinned version, versions locked, every compile target stated",
        "reproducible": "nothing generated or built is committed, and CI runs the gate from a clean checkout",
        "inventoried": "every build also produces a bill of materials (an `sbom` command), which a dependency "
                       "audit reads",
    }),
    Axis("platform", "Platform", ("unknown", "inventoried", "supported", "audited"), "audited", {
        "unknown": "nothing an application runs on could be read from the tree: no runtime pin, no framework version, "
                   "no image",
        "inventoried": "what the applications run on is read and dated; something is out of support, or not in the "
                       "support table",
        "supported": "every runtime, framework and image read is within support on the day it was dated",
        "audited": "every runtime, framework and image is in support, and every application records an `audit` command "
                   "the gate can run",
    }),
    Axis("constitution", "Constitution", ("template", "ratified", "in-full"), "in-full", {
        "template": "`./init` has not run, or the constitution is still the template it installed",
        "ratified": "a constitution is ratified for the rungs this repository actually stands on",
        "in-full": "the floor a generated project ratifies is in force here, and `check-constitution` holds it",
    }),
    Axis("data", "Data", ("open", "recorded", "settled"), "settled", {
        "open": "where the schema is versioned is not recorded",
        "recorded": "the schema's home is recorded: `here`, `elsewhere`, `unmanaged` or `none`",
        "settled": "the schema is versioned in one place — here, in a named repository, or there is none",
    }),
    Axis("infrastructure", "Infrastructure", ("open", "recorded", "settled"), "settled", {
        "open": "where the infrastructure is described is not recorded",
        "recorded": "the infrastructure's home is recorded: `here`, `elsewhere`, `unmanaged` or `none`",
        "settled": "the infrastructure is described in one place — here, in a named repository, or there is none",
    }),
    Axis("release-mode", "Release mode", ("unrecorded", "recorded", "confirmed"), "confirmed", {
        "unrecorded": "the product has not recorded how actor-visible changes are held back",
        "recorded": "a release mode is recorded as evidence; a person has not confirmed it",
        "confirmed": "a person confirmed the release mode and what holds behaviour changes back",
    }),
    Axis("strategy", "Strategy", ("open", "why-recorded", "recommended", "decided", "done"), "done", {
        "open": "why this work is happening is not recorded",
        "why-recorded": "the business trigger is recorded; no strategy is recommended yet",
        "recommended": "a strategy is recommended from the trigger and this map — *leave it* included",
        "decided": "the strategy is decided and recorded as an ADR",
        "done": "the programme is finished: every retirement-ledger row reads *removed*, or the decision was to "
                "leave it",
    }),
)
BY_KEY = {axis.key: axis for axis in AXES}
Row = dict


def row(axis: Axis, rung: str, evidence: str, provenance: str, planned: str | None = None) -> Row:
    assert rung in axis.rungs, (axis.key, rung)
    return {
        "axis": axis.key, "rung": rung, "target": axis.target, "evidence": evidence, "provenance": provenance,
        "planned": planned,
    }


def laid_out(app: App) -> bool:
    """Whether an application lives where a generated one would: under `apps/` — or at a Go module's root, whose
    directory is its import path, so that moving it rewrites every importer for a layout and nothing else. The
    Go adoption's map flagged three module roots for not living under `apps/`, with no way to satisfy the rung
    short of a breaking move; a module root is laid out where it stands."""
    return app.path.startswith("apps/") or (app.toolchain or {}).get("ecosystem") == "go"


def settled(record: dict, key: str) -> bool:
    home = record.get(key)
    return home in ("here", "none") or (home == "elsewhere" and bool(record.get("repository")))


def detected(apps: list[App], adoption: Adoption) -> list[Row]:
    """Every axis, at the rung the record establishes and no higher, with the fact that establishes it."""
    wrapped = wrapped_of(apps)
    release, ci = adoption.release or {}, adoption.ci or {}
    path = release.get("path", "unknown")
    rows = [row(
        BY_KEY["path-to-production"], path if path in BY_KEY["path-to-production"].rungs else "unknown",
        "; ".join(release.get("evidence") or []) or "release.path in project.json",
        release.get("provenance", "unrecorded"),
    )]
    forge = ci.get("forge", "none")
    rows.append(row(
        BY_KEY["integration"], "unknown",
        f"CI on {forge}, gate {ci.get('gate')}" if ci.get("gate") else "no CI gate is written for this repository",
        "unrecorded",
    ))
    tests = [app.name for app in wrapped if (app.commands or {}).get("test")]
    rows.append(row(
        BY_KEY["safety-net"], "tests-exist" if tests else "none",
        f"test recorded for {', '.join(tests)}" if tests else "no application records a test command", "detected",
    ))
    structure, why_not = "as-found", ""
    if wrapped and all(app.kind != "application" for app in wrapped):
        structure = "named"
        if all(laid_out(app) for app in wrapped):
            structure = "laid-out"
            if all(app.structure == "hexagonal" for app in wrapped):
                structure = "hexagonal"
                if all((app.commands or {}).get("typecheck") for app in wrapped):
                    structure = "typed"
        else:
            why_not = "; not under apps/: " + ", ".join(app.path for app in wrapped if not laid_out(app))
    else:
        unnamed = [app.name for app in wrapped if app.kind == "application"] or ["nothing wrapped"]
        why_not = f"; role not established for {', '.join(unnamed)}"
    kinds = ", ".join(f"{app.name}: {app.kind}" for app in wrapped) or "no application was here"
    rows.append(row(BY_KEY["structure"], structure, kinds + why_not, "detected"))
    rows.append(build_row(adoption, wrapped))
    rows.append(platform_row(adoption, wrapped))
    rows.append(row(BY_KEY["constitution"], "template", ".specify/memory/constitution.md", "detected"))
    homes = (("data", "schema", adoption.database), ("infrastructure", "home", adoption.infrastructure))
    for key, field, what in homes:
        record = what or {}
        rung = "open" if not record or record.get("provenance") == "unrecorded" else (
            "settled" if settled(record, field) else "recorded"
        )
        rows.append(row(
            BY_KEY[key], rung, f"{field}: {record.get(field, 'unrecorded')}", record.get("provenance", "unrecorded")
        ))
    rows.append(row(BY_KEY["release-mode"], "unrecorded", "confirm project.json's releaseMode", "unrecorded"))
    rows.append(strategy_row(adoption))
    return rows


def build_row(adoption: Adoption, wrapped: list[App]) -> Row:
    """The build floor, read off the tree and the survey: the lowest rung any application's build stands on."""
    axis = BY_KEY["build"]
    if not wrapped:
        return row(axis, axis.target, "every application is generated, and comes with its build pinned", "detected")
    wins = [w for w in (adoption.survey or {}).get("quickWins") or [] if isinstance(w, dict)]
    kinds = {str(w.get("kind")) for w in wins}
    ant = [app.name for app in wrapped if (app.toolchain or {}).get("ecosystem") == "ant"]
    if ant or "archive-tracked" in kinds:
        said = [f"{name} builds with Ant, its jars committed" for name in ant]
        said += ["a binary archive is tracked"] if "archive-tracked" in kinds else []
        return row(axis, "undeclared", "; ".join(said), "detected")
    loose = [f"{app.name} states no compile target" for app in wrapped if not (app.toolchain or {}).get("version")]
    loose += ["a lockfile is missing"] if "no-lockfile" in kinds else []
    if loose:
        return row(axis, "declared", "; ".join(loose), "detected")
    if "ide-or-build-output-tracked" in kinds or not (adoption.ci or {}).get("gate"):
        said = ["build output is tracked"] if "ide-or-build-output-tracked" in kinds else []
        said += [] if (adoption.ci or {}).get("gate") else ["no CI runs the gate from a clean checkout"]
        return row(axis, "pinned", "; ".join(said), "detected")
    unlisted = [app.name for app in wrapped if not (app.commands or {}).get("sbom")]
    if unlisted:
        return row(axis, "reproducible", f"no `sbom` command recorded for {', '.join(unlisted)}", "detected")
    return row(axis, "inventoried", "every application builds pinned, from a clean checkout, with a bill of materials",
               "detected")


def platform_row(adoption: Adoption, wrapped: list[App]) -> Row:
    """`unknown` with nothing read; `inventoried` while anything read is out of support or not in the table, naming
    it — or while an application builds with Ant, whose committed jars nothing can audit; `supported` when everything
    read is in support; `audited` when every application also records an `audit`."""
    axis, record = BY_KEY["platform"], adoption.platform or {}
    products = [p for p in record.get("products") or [] if isinstance(p, dict)]
    if not products:
        return row(axis, "unknown", "no runtime pin, framework version or image the survey can date", "unrecorded")
    said = [
        f"{p.get('title')} {p.get('version')} left support on {p.get('eol')}" if p.get("status") == "end-of-life"
        else f"{p.get('title')} {p.get('version')} is not in the support table"
        for p in products if p.get("status") in ("end-of-life", "unknown")
    ]
    said += [f"{app.name} builds with Ant, whose committed jars nothing can audit — Maven or Gradle first"
             for app in wrapped if (app.toolchain or {}).get("ecosystem") == "ant"]
    if said:
        return row(axis, "inventoried", f"dated {record.get('dated')}: " + "; ".join(said), "detected")
    dated = "; ".join(f"{p.get('title')} {p.get('version')}" for p in products)
    unaudited = [app.name for app in wrapped if not (app.commands or {}).get("audit")]
    if unaudited:
        return row(axis, "supported", f"in support on {record.get('dated')}: {dated}; no audit command recorded for "
                                      f"{', '.join(unaudited)}", "detected")
    return row(axis, "audited", f"in support on {record.get('dated')}: {dated}; audit recorded for every application",
               "detected")


def strategy_row(adoption: Adoption) -> Row:
    """`open` with no trigger; `recommended` once `why` and the map have said what follows; `decided` when an
    accepted ADR names a strategy; `done` when it was to leave it, or the retirement ledger reads *removed*."""
    axis, record = BY_KEY["strategy"], adoption.strategy or {}
    if record.get("decided"):
        rung = "done" if record.get("finished") else "decided"
        return row(axis, rung, f"ADR {record.get('adr')}: {record['decided']}", "detected")
    if not adoption.why:
        return row(axis, "open", "no business trigger recorded", "unrecorded")
    if record.get("recommended"):
        return row(axis, "recommended", f"why: {adoption.why}; recommended: {record['recommended']}", "detected")
    return row(axis, "why-recorded", f"why: {adoption.why}", "detected")


def reconciled(recorded: list[Row], fresh: list[Row], refreshed: list[str]) -> list[Row]:
    """The recorded rows against a fresh detection: a row the tree or nobody placed follows the tree, a row a
    person placed stands — its `planned` slice with it — and every change is said."""
    # An axis renamed by a newer factory is read under the name the repository has, so that the rung a person
    # placed survives the rename: `kept` keyed by an unknown axis is a row silently dropped, and its `confirmed`
    # rung with it — the bug the comment below records, reached the other way round.
    named = [{**r, "axis": OLD_AXES.get(str(r.get("axis")), r.get("axis"))} for r in recorded if isinstance(r, dict)]
    kept = {r["axis"]: r for r in named if r.get("axis") in BY_KEY}
    result = []
    for new in fresh:
        old = kept.get(new["axis"])
        if old is None:
            result.append(new)
            continue
        # A resurvey cannot infer an actor-visible release choice from build files. Preserve the
        # crossing's recorded evidence until the person confirms it; check-convergence still refuses
        # it if project.json loses the mode that evidence names.
        if new["axis"] == "release-mode" and old.get("rung") == "recorded" and new["rung"] == "unrecorded":
            result.append(old)
            continue
        if old.get("provenance") in ("confirmed", "overridden"):
            # The person's words are the evidence for a row they placed — `/ground` writes them there — and the
            # tree's reading is not a correction of them. The first real adoptions lost every answer on the next
            # `/survey`, and recorded it as the bug it was.
            result.append({
                **new, "rung": old["rung"], "provenance": old["provenance"], "planned": old.get("planned"),
                "evidence": old.get("evidence") or new["evidence"], **asked_of(old),
            })
            continue
        if old.get("rung") != new["rung"]:
            refreshed.append(f"convergence: {new['axis']} refreshed from `{old.get('rung')}` to `{new['rung']}`")
        # A row asked on the board and not known keeps the asking and what was said, while the tree's reading
        # stays the same: the checklist would otherwise ask it again on every refresh.
        kept_words = {"evidence": old["evidence"]} if old.get("asked") and old.get("rung") == new["rung"] else {}
        result.append({**new, "planned": old.get("planned"), **kept_words, **asked_of(old)})
    return result


def asked_of(row: Row) -> Row:
    """The date a person was asked about the row, where one was — kept across every refresh."""
    return {"asked": row["asked"]} if row.get("asked") else {}


def summary(rows: list[Row]) -> tuple[int, int, int]:
    """How many rows sit at their target, below it, and are unrecorded — the report's one line about the map."""
    at = sum(1 for r in rows if r["rung"] == r["target"])
    unrecorded = sum(1 for r in rows if r["provenance"] == "unrecorded")
    return at, len(rows) - at - unrecorded, unrecorded

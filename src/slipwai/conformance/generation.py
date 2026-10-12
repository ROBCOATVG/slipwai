"""The `profiles` and `targets` checks: generate each backend the way a project maker would, and read what it needs.

A profile is answered when `slipwai generate --profile <p> --skip-checks` succeeds for the backend; where the profile
asks where events live, the backend must also offer an event store and answer its files, because generation skips a
feature the layout lacks and would pass with no store at all. Every profile is generated under the
backend's first target, and the richest profile once under every target it declares, with the event store that
target provisions where it offers one, so a backend with four targets costs five generations. `--frontend none`:
the suite checks a language, not a browser app.
"""
from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

from ..catalog import CATALOG, axis_options
from ..images import POSTGRES_SSLMODE_KINDS
from ..project.flag_route import transports_of
from ..registry import (
    EVENT_MODEL_PATHS,
    OPT_IN_FLAG_TRANSPORTS,
    POSTGRES_SSLMODE,
    READ_SIDE_FILES,
    WRITE_SIDE_FILES,
    Registry,
)
from ..rungs import STATE, WRITE_MODEL, rung_rows
from . import child

EVENT_STORE = "persistence"
# The one choice the state-stored run makes, and the paths a page about where code goes reads.
STATE_RUNG: tuple[tuple[str, str], ...] = ((WRITE_MODEL, STATE),)
MODEL_PATH_KEYS = ("events", "domain", "usecase", "test", "repository")
# How `slipwai` names the package a refusal is about: the finding names the backend already, so it is said once.
REFUSED = re.compile(r"^slipwai: language \S+ \(.*?\): ")
PROJECT = "conformance"


@dataclass(frozen=True)
class Run:
    """One generation: what was asked, and the project it wrote or the last line `generate` said instead."""

    backend: str
    profile: str
    target: str
    choices: tuple[tuple[str, str], ...]
    project: Path | None
    said: str


def targets_of(key: str) -> list[str]:
    """The targets the backend's own row declares, in its order: the loaded backend's row, so it is always there."""
    return list(CATALOG["backends"][key]["targets"])


def richest() -> str:
    """The profile of the highest tier: the one every target is generated under."""
    return max(CATALOG["profiles"], key=lambda name: CATALOG["profiles"][name].get("tier", 0))


def provisioned(backend: str, target: str) -> tuple[tuple[str, str], ...]:
    """The event store `target` provisions, as a choice, where the backend is offered one there; else the default."""
    for option in axis_options(EVENT_STORE, backend, target):
        if CATALOG["axes"][EVENT_STORE]["options"][option].get(target, {}).get("provisions"):
            return ((EVENT_STORE, option),)
    return ()


def generate(output: Path, backend: str, profile: str, target: str, choices: tuple[tuple[str, str], ...]) -> Run:
    """`slipwai generate` in a process of its own, as a project maker runs it, into a directory of its own."""
    parent = output / str(len(list(output.iterdir())))
    parent.mkdir()
    arguments = ["generate", PROJECT, "--profile", profile, "--backend", backend,
                 "--frontend", "none", "--target", target, "--output", str(parent), "--skip-checks"]
    for axis, option in choices:
        arguments += [f"--{axis}", option]
    done = child.run("slipwai", arguments)
    if done.returncode == 0 and (parent / PROJECT).is_dir():
        return Run(backend, profile, target, choices, parent / PROJECT, "")
    if done.returncode == 0:  # an exit the package forced, `os._exit(0)` included, writes nothing
        return Run(backend, profile, target, choices, None, "exit 0 with no project written")
    said = REFUSED.sub("", done.last_line(), count=1)
    return Run(backend, profile, target, choices, None, said or f"exit {done.returncode}")


def runs(output: Path, backend: str) -> list[Run]:
    """Every generation the two checks read for one backend: each profile at its first target, the richest profile
    at each other target it declares, and the richest profile once more on the state-stored rung.

    The rung is a run rather than a reading of the layout because the rung changes what is generated and not only
    what is declared: a backend whose `state` rows name an asset it has not committed, or a `name_service` that
    renames only what the log's files are called, is a project that does not generate — and nothing short of
    generating one finds that out. At the first target, because the rung is a per-service answer and has nothing
    to do with where the project is deployed; the targets are covered by the runs above.
    """
    targets = targets_of(backend)
    top = richest()
    plan = [(profile, targets[0], provisioned(backend, targets[0]) if profile == top else ())
            for profile in CATALOG["profiles"]]
    plan += [(top, target, provisioned(backend, target)) for target in targets[1:]]
    plan += [(top, targets[0], STATE_RUNG)] if WRITE_MODEL in CATALOG["axes"] else []
    return [generate(output, backend, profile, target, choices) for profile, target, choices in plan]


def event_store_findings(loaded: Registry, backend: str) -> list[str]:
    """Where a profile asks where events live: an event store offered, and every one offered answered with files."""
    axis = CATALOG["axes"][EVENT_STORE]
    targets = targets_of(backend)
    offered = list(dict.fromkeys(option for target in targets for option in axis_options(EVENT_STORE, backend, target)))
    if not offered:
        return [f"backend {backend} offers no event store, so it does not answer {profile} (FR-031)"
                for profile in CATALOG["profiles"] if profile in axis["profiles"]]
    findings: list[str] = []
    for option in offered:
        for feature in dict.fromkeys([*axis["options"][option]["features"], *axis["always"]]):
            for member in (WRITE_SIDE_FILES, READ_SIDE_FILES):
                if feature not in loaded.answer(backend, member):
                    findings.append(f"backend {backend} offers event store {option}, and {member.name} answers "
                                    f"nothing for {feature}")
    return list(dict.fromkeys(findings))


def asked(run: Run) -> str:
    """What the run asked for, as a finding names it: the profile, and the choices made beside it."""
    choices = ", ".join(f"{axis} {option}" for axis, option in run.choices)
    return f"{run.profile} at {choices}" if choices else run.profile


def rung_findings(loaded: Registry, backend: str) -> list[str]:
    """What the state-stored rung is owed: a `state` block answering every store the backend offers, and a
    `repository` path for the page that says where a slice's code lands.

    A backend that answers nothing for the rung generates a service with no persistence at all rather than
    failing, because core skips a feature the layout lacks — the same silence `event_store_findings` is here to
    break on the other rung. The `repository` key is read only on this rung too, and core fills it from the
    decision's path for one MINOR, so the gap is named here or nowhere.
    """
    axis = CATALOG["axes"][EVENT_STORE]
    offered = list(dict.fromkeys(option for target in targets_of(backend)
                                 for option in axis_options(EVENT_STORE, backend, target)))
    wanted = dict.fromkeys(feature for option in offered
                           for feature in (*axis["options"][option]["features"], *axis["always"]))
    rows = rung_rows(loaded.answer(backend, WRITE_SIDE_FILES), STATE)
    # Per feature rather than per option, because the feature is what owns the files: the store a project
    # chose and the in-memory one the axis always ships are the same kind of gap, said once each.
    findings = [f"backend {backend} offers persistence {feature}, and write_side_files answers nothing for it on "
                f"the state rung: a service answered write-model state would get no store"
                for feature in wanted if feature not in rows]
    try:
        paths = loaded.answer(backend, EVENT_MODEL_PATHS)(PROJECT, "apps/service")
    except Exception as error:  # noqa: BLE001 - the package's own code; whatever it raises is the finding
        return [*findings, f"backend {backend} answers event_model_paths with something that cannot be called "
                           f"for a service: {type(error).__name__}: {error}"]
    if not isinstance(paths, dict):
        return [*findings, f"backend {backend} answers event_model_paths with a callable returning "
                           f"{type(paths).__name__}, where the protocol wants a dict"]
    findings += [f"backend {backend} answers event_model_paths with no {key}, which the page that says where a "
                 f"slice's code lands reads" for key in MODEL_PATH_KEYS if key not in paths]
    return list(dict.fromkeys(findings))


def stopped(run: Run, named: Collection[str]) -> bool:
    """Whether the run stopped on a fault another check already named: a line of `named` in what it said."""
    return run.project is None and any(line in run.said for line in named)


def failed(run: Run, named: Collection[str]) -> bool:
    """Whether the run did not generate for a cause of its own: one that `stopped` is that check's finding, shown
    once there and not again per run."""
    return run.project is None and not stopped(run, named)


def read_by(backend: str, done: list[Run]) -> dict[str, list[Run]]:
    """The runs each check reads: `profiles` every profile at the first target, the state-stored rung among them,
    `targets` the richest profile at each target, `prune rows` all of them."""
    first, top = targets_of(backend)[0], richest()
    return {"profiles": [run for run in done if run.target == first],
            "targets": [run for run in done if run.profile == top],
            "prune rows": list(done)}


def profile_findings(loaded: Registry, backend: str, done: list[Run], named: Collection[str] = ()) -> list[str]:
    first = targets_of(backend)[0]
    findings = [f"backend {backend} does not generate under {asked(run)}: {run.said}"
                for run in done if run.target == first and failed(run, named)]
    return findings + event_store_findings(loaded, backend) + rung_findings(loaded, backend)


def target_findings(loaded: Registry, backend: str, done: list[Run], named: Collection[str] = ()) -> list[str]:
    """Each declared target generated once, and the members keyed by what a target provisions read for it."""
    first = targets_of(backend)[0]
    findings = [f"backend {backend} does not generate for target {run.target}: {run.said}"
                for run in done if run.target != first and failed(run, named)]
    modes = loaded.answer(backend, POSTGRES_SSLMODE)
    for run in done:
        for axis, option in run.choices:
            kind = CATALOG["axes"][axis]["options"][option].get(run.target, {}).get("provisions")
            if kind in POSTGRES_SSLMODE_KINDS and (not isinstance(modes, dict) or kind not in modes):
                findings.append(f"backend {backend} answers postgres_sslmode with no {kind}, which {run.target} "
                                f"provisions {option} as")
    # A backend may name only a target that *has* a second transport to opt into. Asked of each target
    # rather than read off a table, and only of the ones this keel has installed: a backend built against a
    # cloud nobody here installed is not a backend this keel can say anything about.
    findings += [f"backend {backend} names {target} in opt_in_flag_transports, which has no opt-in flag transport"
                 for target in sorted(loaded.answer(backend, OPT_IN_FLAG_TRANSPORTS))
                 if target in CATALOG["targets"] and transports_of(target)[1] is None]
    return list(dict.fromkeys(findings))

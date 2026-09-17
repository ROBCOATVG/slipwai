"""`target: existing`: what a project deploying to infrastructure it does not own is told, in every part that speaks of production.

The third target row (brownfield adoption; experimental as `AGENTS.md` defines the word) manages nothing
— no `infra/`, no pipeline, no `make deploy`, no flag mechanism — and turns on the documentation of where the
project goes and the release-constraint rung of `/drive` instead. Every sentence of that is here, beside the
page that carries what the adoption recorded about the infrastructure, so that the README, `AGENTS.md`, the
drive command and the docs cannot disagree about what an existing target is.
"""
from __future__ import annotations

from ..catalog import CATALOG
from ..origin import Adoption
from ..services import App
from ..targets import managed
from .flags import flag_stage

# The release-constraint rung for a project that deploys to infrastructure the factory does not manage: there
# is no flag mechanism here to decide about, and there is still a decision.
EXISTING_STAGE = """**Release constraint** — this project deploys to infrastructure the factory does not manage;
   `docs/deployment.md` records where, and how a release reaches it. Before the plan, decide and write down
   how this slice reaches production and what gates its release: releasable on merge because everything it
   adds is coherent and safe to an actor the moment it lands; held behind a toggle this repository already
   has, named; or a coordinated deploy, with who does what. Recommend the answer with its reason rather than
   asking an open question. If `docs/deployment.md` cannot yet say how a release reaches production, that is
   not a gap to work around — it is the first slice."""

# What a project going to infrastructure it does not own gets instead of `infra/`: the page that says where.
EXISTING_INCLUDED = (
    "- Where it deploys: `docs/deployment.md` records the infrastructure this project runs on but does not own "
    "(`target: existing`), where its description lives, and how a release reaches it\n"
)

EXISTING_GUIDANCE = """
- This project deploys to infrastructure the factory does not manage (`target: existing`): nothing under
  `infra/`, no deploy pipeline, no `make deploy`. `docs/deployment.md` records where it runs and how a release
  reaches it; read it before a slice that touches configuration, data or the release path, and say in the
  plan how the slice reaches production and what gates its release. Where that page says the infrastructure
  is `unmanaged`, describe before importing; never manage a resource in two places.
"""

EXISTING_README = """
## Production

This project deploys to infrastructure this factory does not manage (`--target existing`): nothing under
`infra/`, no deploy pipeline, no `make deploy`. [`docs/deployment.md`](docs/deployment.md) records where it
runs, who describes that, and how a release reaches it — written as soon as it is known, because `/drive`
asks every slice how it reaches production and what gates its release.
"""


def existing_deployment_page(project_name: str, adoption: Adoption | None) -> str:
    """`docs/deployment.md` for `target: existing`: where this runs and how a release reaches it, as recorded."""
    infrastructure = adoption.infrastructure if adoption else {}
    home = infrastructure.get("home", "unknown")
    described = infrastructure.get("describedBy") or []
    repository = infrastructure.get("repository")
    account = {
        "here": "Infrastructure code is in this repository"
        + (f" ({', '.join(described)})" if described else "")
        + ". The factory adds nothing to it and manages none of it: import or reference what exists — `tofu import`, "
        "data sources — and never let two places manage one resource.",
        "elsewhere": f"The infrastructure is owned by another repository{f', `{repository}`' if repository else ''}. "
        "That repository is the contract: what this one hands over — a tag, an image, a package, a ticket — and "
        "what it may assume about the environment belong written here, and a change to either is a change to both.",
        "unmanaged": "Nothing this survey could see describes the infrastructure: it was set up by hand, by a console "
        "or by a person who may have left. The first step is to describe it — what runs where, with what "
        "configuration, reached how — before anything imports or changes it. Describing is safe; importing what "
        "is not described is how two things end up managing one resource.",
        "none": "This project deploys nowhere the survey could see and nobody said otherwise: a library, a tool, or a "
        "deployment that has not been decided. Say which, here.",
        "unknown": "Not recorded yet. `slipwai adopt` records it from the survey and the person; a generated project "
        "given `--target existing` records it here, by hand: where this runs, who describes that, and how.",
    }[home if home in ("here", "elsewhere", "unmanaged", "none") else "unknown"]
    provenance = f" (recorded as `{infrastructure['provenance']}`)" if infrastructure.get("provenance") else ""
    return f"""# Where `{project_name}` deploys

This project goes to production on infrastructure this factory does not own (`target: existing`): nothing
under `infra/`, no deploy pipeline, no `make deploy`, nothing provisioned. What the factory owes it instead is
this page — where it runs, who describes that, and how a release reaches it — and the release-constraint rung
of `/drive`, which asks every slice how it reaches production and what gates its release.

## The infrastructure

Home: **`{home}`**{provenance}. {account}

## How a release reaches production

{release_recorded(adoption)}Write it here, in the order it happens: the artefact (an image, a package, a
WAR), who or what builds it, the environments in order, who applies it, and how it is undone. A release path
nobody can write down is the first thing to fix, because every slice `/drive` finishes ends by asking for it.

## Release constraints

No flag mechanism is installed here — that comes with a managed target — so each slice decides one of three
things and writes it in its plan: releasable on merge, because everything it adds is coherent and safe to an
actor the moment it lands; held behind a toggle this repository already has, named; or a coordinated deploy,
with who does what. `/drive` asks, and `AGENTS.md` asks for the same sentence in the turn that pushes.
"""


def release_recorded(adoption: Adoption | None) -> str:
    """The opening sentence of the release section: what `adopt` recorded about how a change reaches production,
    with its provenance — or that nothing is recorded, which is a fact and not a guess."""
    release = adoption.release if adoption else {}
    path = release.get("path", "unknown")
    provenance = release.get("provenance", "unrecorded")
    evidence = ", ".join(f"`{e}`" for e in release.get("evidence") or [])
    return {
        "pipeline": f"Recorded: **a pipeline deploys** (`{provenance}`{f', from {evidence}' if evidence else ''}). ",
        "scripted": f"Recorded: **somebody runs a script** (`{provenance}`{f', from {evidence}' if evidence else ''}). ",
        "manual": f"Recorded: **by hand** (`{provenance}`). ",
        "unknown": f"Recorded: **unknown** (`{provenance}`) — nothing in the tree says, and nobody has said. ",
    }[path if path in ("pipeline", "scripted", "manual") else "unknown"]


def release_stage(apps: list[App], target: str) -> list[str]:
    """The release-constraint rung of `/drive`: the flag decision under a managed target, the deployment decision
    under `existing`, and nothing under `none`, which has nothing to decide."""
    if managed(CATALOG, target):
        return [flag_stage(apps)]
    return [EXISTING_STAGE] if target == "existing" else []


def production_included_line(target: str) -> str:
    """What production adds to `docs/whats-included.md`: the path under a managed target, the page under `existing`."""
    if managed(CATALOG, target):
        return (
            "- A path to production: `infra/` (OpenTofu — one ECS service per application, deployed blue/green, and the "
        "database, identity and site the answers asked for), `.github/workflows/deploy.yml`, "
        "`.github/workflows/rollback.yml` (started by hand), `make build push deploy rollback smoke`, and "
        "`docs/deployment.md` drawing it for this project's services, and `docs/adr/0002-production-target.md` saying why\n"
        )
    return EXISTING_INCLUDED if target == "existing" else ""

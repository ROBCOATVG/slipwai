"""Prepare a deployment-shape transition without applying or replacing a data-holding project's files.

A provider may need a data transfer, not merely a DNS change. The candidate is a reviewable generation
beside the current infrastructure; the current manifest, state and database remain authoritative until a
person follows the package's cutover runbook. No forge or cloud command runs here.
"""
from __future__ import annotations

import json
from pathlib import Path

from .assets import contained
from .catalog import CATALOG
from .deployment_shapes import recorded, row, selected
from .errors import GenerationError
from .layout import layout_of
from .manifest import apps_from_manifest, read_manifest
from .origin import adoption_of
from .project.infra import target_files, target_scripts
from .scaffold import project_files
from .targets import managed


def transition(root: Path, requested: str) -> tuple[dict, dict, str]:
    document = read_manifest(root, "converge --shape")
    selected(requested)
    target = document["target"]
    if not managed(CATALOG, target):
        raise GenerationError(
            "this project has no managed deployment; choose a managed --target when generating a project"
        )
    current = recorded(document)
    if current == requested:
        raise GenerationError(
            f"this project already has shape {requested}; run slipwai converge --check to inspect its adoption"
        )
    destination = row(target, requested)
    if destination is None:
        raise GenerationError(f"target {target} has no shape transition contract; install an updated target package")
    return document, destination, current


def check(root: Path, requested: str) -> str:
    document, destination, current = transition(root, requested)
    return (f"{document['name']}: {current} → {requested}\n\n{destination['transition']}\n\n"
            f"Run slipwai converge --shape {requested} to prepare files and a runbook. No infrastructure is applied.\n")


def prepare(root: Path, requested: str) -> Path:
    document, destination, current = transition(root, requested)
    layout = layout_of(document)
    relative = f".slipwai/shape-transitions/{current}-to-{requested}"
    proposal = contained(root, relative)
    if proposal.exists():
        raise GenerationError(
            f"{relative} already holds a proposal; inspect it, then move it aside with "
            f"mv {relative} {relative}-saved before preparing another"
        )
    apps = apps_from_manifest(document)
    generated = project_files(document["name"], document["profile"], document["target"], apps,
                              layout, adoption_of(document), requested)
    # This proposal changes deployment material only; service code and the person's current files stay put.
    prefixes = (layout.place("infra/"),)
    exact = {layout.place(path) for path in (
        "Makefile", "README.md", "AGENTS.md", "docs/adr/0002-production-target.md", "docs/deployment.md",
        ".github/workflows/deploy.yml", ".github/workflows/production.yml", ".github/workflows/rollback.yml",
        *target_scripts(document["target"], requested),
    )}
    files = {path: content for path, content in generated.items()
             if path in exact or path.startswith(prefixes)}
    candidate = {**document, "shape": requested}
    files["project.json"] = json.dumps(candidate, indent=2) + "\n"
    before = target_files(document["name"], document["profile"], document["target"], apps, current)
    after = target_files(document["name"], document["profile"], document["target"], apps, requested)
    removed = sorted(layout.place(path) for path in before.keys() - after.keys())
    if requested == "skiff":
        removed.append(layout.place(".github/workflows/production.yml"))
    descriptor = {"from": current, "to": requested, "status": "prepared", "files": sorted(files), "remove": removed,
                  "applied": False, "cutoverConfirmed": False}
    files["transition.json"] = json.dumps(descriptor, indent=2) + "\n"
    files["RUNBOOK.md"] = runbook(relative, current, requested, destination)
    paths = {path: contained(proposal, path) for path in files}
    proposal.mkdir(parents=True)
    for relative_path, content in files.items():
        path = paths[relative_path]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
    return proposal


def runbook(proposal: str, current: str, requested: str, destination: dict) -> str:
    return f"""# Prepare {current} → {requested}

This directory is a proposal. The active project.json, infrastructure, state and database have not changed.
Nothing has been applied, destroyed, pushed or cut over. Do not install the candidate manifest before the
provider's data-preservation and cutover steps are complete: its deploy workflow uses the new shape.

{destination['transition']}

1. Back up the current state and database. Keep the original module and its state key/workspace intact.
   Record the current deployment's immutable images, database endpoint, migration version and row counts.
2. Compare this proposal with the active deployment files. Preserve local edits when installing a reviewed
   file; a candidate is not permission to overwrite them. `transition.json` also lists obsolete generated
   paths under `remove`; retire them only after preserving the old module and verified cutover.
   Validate the candidate's real provider module:
   `tofu -chdir={proposal}/infra/service init -backend=false -input=false` followed by
   `tofu -chdir={proposal}/infra/service validate`. Adjust the path when delivery lives in its own directory.
3. Read the provider's plan before any apply. It must preserve the existing database and every resource
   holding data. If the provider needs a different database, provision the destination under a separate
   state key, export/import over an authorised private connection, and verify counts/checksums and schema
   migration versions. Never enable public database access merely to make this step convenient.
4. Prove the candidate application against that database and the existing immutable images. Verify actor
   behaviour and smoke checks, then move DNS explicitly. Keep the old deployment available for rollback.
5. After verified cutover, install the reviewed deployment files and candidate manifest together. Record
   the confirmed platform transition in the convergence map; this prepared proposal is not that receipt.
   Keep the original database, snapshots and state until their retention and rollback requirements are met.

A downgrade is an explicit request, and never discards a data-holding rung or silently changes its store.
"""

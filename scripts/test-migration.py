#!/usr/bin/env python3
"""Prove the 1.x crossing with the last installed release, every backend/profile, and adopted trees.

Brought back by name from e1a9e43:scripts/test-migration.py. The old programme tested one TypeScript
scaffold and skipped absent tags. This programme uses the installed latest 1.x release, released language
archives, explicitly checkout-sourced targets, and refuses an absent prerequisite instead of exempting it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.errors import GenerationError  # noqa: E402
from slipwai.language_release import copy_directory, unpack  # noqa: E402
from slipwai.migration_legacy import published, runtime  # noqa: E402
from slipwai.versions import is_release, key  # noqa: E402

BACKENDS = ("typescript", "go", "python", "java-quarkus", "java-spring")
LANGUAGES = ("typescript", "go", "python", "java", "java-spring", "java-quarkus")


def run(arguments: list[str], cwd: Path, environment: dict[str, str]) -> str:
    done = subprocess.run(arguments, cwd=cwd, env=environment, capture_output=True, text=True,
                          encoding="utf-8", timeout=900)
    if done.returncode:
        raise GenerationError(f"{' '.join(arguments)} in {cwd} failed:\n{done.stdout}\n{done.stderr}")
    return done.stdout


def packages(destination: Path, environment: dict[str, str]) -> Path:
    """Released language assets, verified against GitHub's digest; targets explicitly from this checkout."""
    installed = destination / "packages"
    installed.mkdir()
    for name in LANGUAGES:
        repository = f"ROBCOATVG/slipwai-language-{name}"
        receipt = json.loads(run(["gh", "api", f"repos/{repository}/releases/tags/v1.0.0"], ROOT, environment))
        assets = [asset for asset in receipt["assets"] if asset["name"].endswith(".tar.gz")]
        if len(assets) != 1 or not str(assets[0].get("digest") or "").startswith("sha256:"):
            raise GenerationError(f"{repository} 1.0.0 has no unique checksummed archive; repair its release")
        asset = assets[0]
        run(["gh", "release", "download", "v1.0.0", "--repo", repository,
             "--pattern", asset["name"], "--dir", str(destination)], ROOT, environment)
        archive = destination / asset["name"]
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != asset["digest"].removeprefix("sha256:"):
            raise GenerationError(f"{archive} fails its published digest; download the release again")
        unpack(archive, installed / name, name)
    for name in ("aws", "azure"):
        copy_directory(ROOT / "packages" / name, installed / name)
    return installed


def git(root: Path, *arguments: str) -> str:
    return run(["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0", *arguments], root, dict(os.environ)).strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def feature(root: Path, backend: str, profile: str, delivery: str) -> None:
    """Two evidenced trunk slices, a stale optimistic status, an unmerged claim, and a run that stopped."""
    metadata = json.loads((root / "project.json").read_text(encoding="utf-8"))
    for record in metadata["deployables"].values():
        if record.get("kind") == "service":
            record["contexts"] = ["ordering"]
    write(root / "project.json", json.dumps(metadata, indent=2) + "\n")
    spec = root / "specs/ordering"
    write(spec / "story-split.md", "# Split\n\n| Slice | Capability |\n|---|---|\n"
          "| ORD-01 | create-order |\n| ORD-02 | cancel-order |\n| ORD-03 | dispatch-order |\n")
    write(spec / "decisions.md", "# Decisions\n\n## D1 — preserve the order id\n"
          "- **Stage:** plan · **Slice:** ORD-01 · **When:** 2026-01-01 · **Iteration:** 1\n"
          "- **Question:** Are ids stable?\n- **Options:** stable; replace them\n"
          "- **Decision:** order ids remain stable\n- **Why:** identity. **Read against:** the specification\n"
          "- **Decided by:** human\n- **Confidence:** high. **Would reverse if:** requirements change\n"
          "- **Written to:** `docs/decisions/0001-order-id.md`\n- **Status:** standing\n")
    write(spec / "adversary-log.md", "# Adversary\n\n"
          "## ORD-01 · accepted · 2026-01-01\n- Evidence: specs/ordering/slices/ORD-01/examples.md\n"
          "## ORD-02 · accepted · 2026-01-01\n- Evidence: specs/ordering/slices/ORD-02/examples.md\n")
    write(root / "docs/decisions/0001-order-id.md", "# 0001: stable ids\n")
    for number in range(1, 4):
        slice_id = f"ORD-{number:02}"
        write(spec / f"slices/{slice_id}/plan.md", "# Structure Decision\nContext: ordering\nService: service\n")
        write(spec / f"slices/{slice_id}/examples.md",
              "# Examples\n\nGiven an order, when requested, then retain its id.\n")
    events = '\"PlaceOrder\", \"OrderPlaced\", \"CancelOrder\", \"OrderCancelled\"'
    java = ("public final class MigrationFixture {\n"
            "  public static final String PLACE = \"PlaceOrder\";\n"
            "  public static final String PLACED = \"OrderPlaced\";\n"
            "  public static final String CANCEL = \"CancelOrder\";\n"
            "  public static final String CANCELLED = \"OrderCancelled\";\n"
            "\n  private MigrationFixture() {}\n}\n")
    code, text = {
        "typescript": ("src/migration-fixture.ts",
                       "export const migrationEvents = [" + events.replace(chr(34), chr(39)) + "];\n"),
        "go": ("migrationfixture/fixture.go", "package migrationfixture\n\nvar Events = []string{" + events + "}\n"),
        "python": ("src/migration_fixture.py", "EVENTS = (" + events + ")\n"),
        "java-quarkus": ("src/main/java/MigrationFixture.java", java),
        "java-spring": ("src/main/java/MigrationFixture.java", java),
    }[backend]
    code_path = "apps/service/" + code
    write(root / code_path, text)
    flags = root / "infra/service/flags.auto.tfvars"
    write(flags, 'create_order = "on"\ncancel_order = "off"\n')
    # A version 1 run a person stopped, with a word of theirs nobody took: both are work in flight, and
    # both stay at the root under an adopted layout because `specs/` and `.specify/` are not delivery.
    write(root / "specs/cruise-log.jsonl", json.dumps(
        {"iteration": 7, "started": "2026-01-01T09:00:00Z", "ended": "2026-01-01T09:30:00Z",
         "harness": "claude", "last_line": "cruise: stopped: human", "fingerprint": "abc"}) + "\n")
    write(root / ".specify/cruise-inbox.jsonl", json.dumps(
        {"at": "2026-01-01T10:00:00Z", "text": "dispatch needs the carrier id", "now": False}) + "\n")
    if profile == "event-modelling":
        source = root / delivery / "docs/event-model/model.yaml"
        slices = []
        for number, command, event in ((1, "PlaceOrder", "OrderPlaced"), (2, "CancelOrder", "OrderCancelled"),
                                        (3, "DispatchOrder", "OrderDispatched")):
            slices.append({"id": f"ORD-{number:02}", "name": command, "context": "ordering", "service": "service",
                           "capability": "manage-orders", "pattern": "state-change", "actor": "Operator",
                           "status": "implemented" if number == 3 else "planned", "stream": "order-{orderId}",
                           "folds": [], "gwt": f"specs/ordering/slices/ORD-{number:02}/examples.md",
                           "code": [code_path], "frames": [{"type": "pcr", "name": "OrderOperator"},
                                                            {"type": "cmd", "name": command},
                                                            {"type": "evt", "name": event}]})
        write(source, json.dumps({"version": 1, "slices": slices}, indent=2) + "\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "Implement two orders\n\nSlice-done: ORD-01\nSlice-done: ORD-02")
    git(root, "checkout", "-qb", "slice/ORD-03")
    write(root / "claim-person.txt", "unmerged person work\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "Unmerged dispatch claim")
    git(root, "checkout", "-q", "main")


def prove(root: Path, environment: dict[str, str], *, own_gate: bool = True) -> None:
    cli = [sys.executable, "-m", "slipwai", "migrate", "--no-install"]
    original = git(root, "rev-parse", "HEAD")
    refused = subprocess.run(cli, cwd=root, env=environment, text=True, capture_output=True, encoding="utf-8")
    if refused.returncode == 0 or "slice/ORD-03" not in refused.stderr:
        raise GenerationError(f"{root}: an ahead claim was not refused: {refused.stdout} {refused.stderr}")
    if git(root, "rev-parse", "HEAD") != original or git(root, "status", "--porcelain"):
        raise GenerationError(f"{root}: a refused crossing wrote to the project")
    run([*cli, "--with-claims", "--check"], root, environment)
    if git(root, "rev-parse", "HEAD") != original or git(root, "status", "--porcelain"):
        raise GenerationError(f"{root}: --check changed the project")
    output = run([*cli, "--with-claims"], root, environment)
    metadata = json.loads((root / "project.json").read_text(encoding="utf-8"))
    if metadata["generator"]["updatedWith"].startswith("1.") or metadata["state"] != "in-service":
        raise GenerationError(f"{root}: version or flag history was lost")
    if git(root, "rev-parse", "ORIG_HEAD") != original:
        raise GenerationError(f"{root}: undo does not point at the person's original commit")
    claim = json.loads(git(root, "show", "slice/ORD-03:project.json"))
    if "event-store" in claim["deployables"]["service"].get("selection", {}):
        raise GenerationError(f"{root}: the rename table did not reach the claim branch")
    merges = git(root, "rev-list", "--merges", f"{original}..HEAD").splitlines()
    if len(merges) != 1 or original not in git(root, "rev-list", "--parents", "-1", merges[0]).split()[1:]:
        raise GenerationError(f"{root}: the crossing did not preserve both merge parents")
    if git(root, "show", "slice/ORD-03:claim-person.txt") != "unmerged person work":
        raise GenerationError(f"{root}: the claim lost its own work")
    lines = [json.loads(line) for path in (root / ".slipwai/logs/ordering").glob("*.jsonl")
             for line in path.read_text(encoding="utf-8").splitlines()]
    if {line["slice"] for line in lines if line["kind"] == "merged"} != {"ORD-01", "ORD-02"}:
        raise GenerationError(f"{root}: trunk reconciliation trusted model status or missed real merges")
    if {line["slice"] for line in lines if line["kind"] == "claimed"} != {"ORD-03"}:
        raise GenerationError(f"{root}: the open claim did not cross as the slice still in flight")
    if [line["message"] for line in lines if line["kind"] == "told"] != ["dispatch needs the carrier id"]:
        raise GenerationError(f"{root}: a person's queued word was spent by the crossing")
    if not any(line["kind"] == "parked" and "person" in line["why"] for line in lines):
        raise GenerationError(f"{root}: a run a person stopped crossed as a fairway that never ran")
    if "## D1" not in (root / "specs/ordering/decisions.md").read_text(encoding="utf-8"):
        raise GenerationError(f"{root}: the grandfathered decision id no longer resolves")
    delivery = metadata["layout"]["delivery"]
    run([sys.executable, str(Path(delivery) / "scripts/check-migration.py")], root, environment)
    run([sys.executable, str(Path(delivery) / "scripts/render-fairways.py"), "--check"], root, environment)
    if own_gate:
        if metadata["profile"] == "event-modelling":
            run(["make", "-f", f"{delivery}/Makefile", "model-drawio"], root, environment)
        run(["make", "-f", f"{delivery}/Makefile", "verify"], root, environment)
    print(f"test-migration: {root.name} green — {output.splitlines()[0]}", flush=True)


def installed_home(area: Path, package_dir: Path, environment: dict[str, str]) -> None:
    """Load real releases through the old default directory, without altering the person's HOME."""
    home = area / "legacy-package-home"
    before = home / ".slipwai/languages"
    before.mkdir(parents=True)
    for name in (*LANGUAGES, "aws", "azure"):
        copy_directory(package_dir / name, before / name)
    program = ("import sys; from pathlib import Path; from unittest.mock import patch; "
               "context=patch('pathlib.Path.home', return_value=Path(sys.argv[1])); context.start(); "
               "from slipwai.language_directory import directory; from slipwai.registry import registry; "
               "where=directory(); assert where.name=='packages'; assert not (where.parent/'languages').exists(); "
               "assert {'typescript','go','python','java-quarkus','java-spring'} <= set(registry().backends); "
               "print('test-migration: real installed languages moved to packages and all backends loaded')")
    isolated = {name: value for name, value in environment.items() if name != "SLIPWAI_LANGUAGES"}
    print(run([sys.executable, "-c", program, str(home)], area, isolated).strip(), flush=True)


def adopted(area: Path, profile: str, legacy, environment: dict[str, str]) -> None:
    root = area / f"adopted-{profile}"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "migration proof")
    git(root, "config", "user.email", "proof@slipwai.invalid")
    write(root / "apps/service/package.json", json.dumps({"name": "service", "scripts": {
        "test": "node src/index.cjs", "lint": "node --check src/index.cjs",
        "typecheck": "node --check src/index.cjs", "build": "node --check src/index.cjs"}}) + "\n")
    write(root / "apps/service/src/index.cjs", "const assert = require('node:assert/strict');\n"
          "function placeOrder(id) { return { type: 'OrderPlaced', id }; }\n"
          "assert.deepEqual(placeOrder('order-1'), { type: 'OrderPlaced', id: 'order-1' });\n")
    write(root / "person-owned.md", "The repository owns this page.\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "Existing service with a pinned invariant")
    legacy.run(["-m", "slipwai", "adopt", "--yes", "--no-init", "--no-install", "--profile", profile,
                "--delivery", "delivery", "--target", "none", "--database", "none", "--infrastructure", "none",
                "--forge", "none", "--release", "manual", "--language", "service=typescript",
                "--kind", "service=service", "--purpose", "service=keeps stable order ids",
                "--hexagonal", "service"], root)
    original = (root / "apps/service/src/index.cjs").read_bytes()
    feature(root, "typescript", profile, "delivery")
    prove(root, environment)
    if (root / "apps/service/src/index.cjs").read_bytes() != original:
        raise GenerationError(f"{root}: adoption's person-owned implementation changed")
    if not (root / "delivery/survey/survey.md").is_file():
        raise GenerationError(f"{root}: the read-only resurvey was not retained under delivery")
    document = json.loads((root / "project.json").read_text(encoding="utf-8"))
    if not any(row["axis"] == "release-mode" for row in document.get("convergence", [])):
        raise GenerationError(f"{root}: no release-mode convergence row")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path,
                        help="already installed released language fixtures plus checkout targets")
    parser.add_argument("--legacy-python", type=Path, help="already installed latest version 1 release")
    parser.add_argument("--backend", choices=BACKENDS, action="append", help="restrict an explicit debugging run")
    parser.add_argument("--profile", choices=("standard", "event-modelling"), action="append")
    parser.add_argument("--output", type=Path, help="keep every generated project and gate artefact")
    args = parser.parse_args()
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1",
                   "PYTHONIOENCODING": "utf-8", "SLIPWAI_MIGRATE_RELAUNCHED": "1",
                   "npm_config_audit": "false", "npm_config_fund": "false"}
    for name in ("GITHUB_HEAD_REF", "CI_COMMIT_REF_NAME"):
        environment.pop(name, None)
    latest = max((version for version in published() if version.startswith("1.") and is_release(version)), key=key)
    with (tempfile.TemporaryDirectory(prefix="slipwai-migration-proof-") as scratch,
          runtime(latest, args.legacy_python) as legacy):
        area = args.output or Path(scratch)
        area.mkdir(parents=True, exist_ok=True)
        package_dir = args.package_dir or packages(area, environment)
        environment["SLIPWAI_LANGUAGES"] = str(package_dir.resolve())
        environment["SLIPWAI_LEGACY_PYTHON"] = str(legacy.python)
        installed_home(area, package_dir, environment)
        for profile in args.profile or ("standard", "event-modelling"):
            for backend in args.backend or BACKENDS:
                name = f"{profile}-{backend}"
                legacy.run(["-m", "slipwai", "generate", name, "--profile", profile, "--backend", backend,
                            "--target", "none", "--frontend", "none", "--event-store", "memory",
                            "--http", "none", "--auth", "none", "--users", "none",
                            "--no-init", "--skip-checks", "--output", str(area)], area)
                root = area / name
                feature(root, backend, profile, ".")
                prove(root, environment)
            adopted(area, profile, legacy, environment)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GenerationError as error:
        print(f"test-migration: {error}", file=sys.stderr)
        raise SystemExit(1) from None

"""Source siblings for package CI before those packages are published in a chandlery.

The package under test stays the checkout. Only explicitly named siblings from a pinned public source
checkout are exposed beside it; validation and the same setup run for conformance, matrix and tag builds.
This is CI topology, never an installer fallback or permission to weaken the catalogue's declarations.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
COMMIT = re.compile(r"[0-9a-fA-F]{40}\Z")
MANIFESTS = ("language.json", "target.json", "extension.json")


def declaration(repository: str, ref: str, packages: str, under_test: str) -> list[str]:
    """Validate structured workflow inputs before checkout; shell metacharacters are never evaluated."""
    if not REPOSITORY.fullmatch(repository) or any(part in {".", ".."} for part in repository.split("/")):
        raise ValueError("source repository must be owner/repository; set beside_source_repository")
    if not COMMIT.fullmatch(ref):
        raise ValueError("source ref must be a full commit SHA; set beside_source_ref to the tested commit")
    names = packages.split()
    if not names or any(not SLUG.fullmatch(name) for name in [under_test, *names]):
        raise ValueError("source packages must be package names; correct beside_source_packages")
    if len(set(names)) != len(names) or under_test in names:
        raise ValueError("source siblings must be unique and exclude the checkout; correct beside_source_packages")
    return names


def source_commit(source: Path) -> str:
    """Read actual checkout identity, so the recorded source cannot merely repeat an input claim."""
    try:
        done = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10, check=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("source checkout has no readable commit; checkout the declared full SHA again") from error
    return done.stdout.strip().lower()


def expose(source: Path, destination: Path, names: list[str], repository: str, ref: str) -> list[Path]:
    """Preflight every source and destination, then expose links without overwriting any checkout."""
    if len(set(names)) != len(names):
        raise ValueError("duplicate source siblings; correct beside_source_packages")
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=True)
    if source_commit(source) != ref.lower():
        raise ValueError("source checkout differs from the declared commit; checkout beside_source_ref again")
    pairs: list[tuple[Path, Path]] = []
    for name in names:
        if not SLUG.fullmatch(name):
            raise ValueError("invalid source package name; correct beside_source_packages")
        candidate = (source / "packages" / name).resolve(strict=True)
        if not candidate.is_relative_to(source) or not candidate.is_dir():
            raise ValueError(f"source package {name} escapes its checkout; fix the source package path")
        manifests = [candidate / filename for filename in MANIFESTS if (candidate / filename).is_file()]
        if len(manifests) != 1 or not (candidate / "VERSION").is_file():
            raise ValueError(f"source package {name} has no single package declaration and VERSION; fix its source")
        for declared in [manifests[0], candidate / "VERSION"]:
            if not declared.resolve(strict=True).is_relative_to(source):
                raise ValueError(f"source declaration for {name} escapes its checkout; fix the source package path")
        body = json.loads(manifests[0].read_text(encoding="utf-8"))
        if not isinstance(body, dict) or body.get("name") != name:
            raise ValueError(f"source package {name} has a different declared name; correct beside_source_packages")
        target = destination / name
        if target.exists() or target.is_symlink():
            raise ValueError(f"{target} already exists; remove the sibling collision before exposing source packages")
        pairs.append((candidate, target))
    for candidate, target in pairs:
        target.symlink_to(candidate, target_is_directory=True)
        print(f"source sibling {target.name}: {repository}@{ref.lower()}:packages/{target.name}", flush=True)
    return [target for _, target in pairs]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true", help="validate inputs before checkout, without writing")
    parser.add_argument("--source", type=Path, default=Path(".package-sources"))
    parser.add_argument("--destination", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    repository = os.environ.get("PACKAGE_SOURCES_REPOSITORY", "")
    ref = os.environ.get("PACKAGE_SOURCES_REF", "")
    try:
        names = declaration(repository, ref, os.environ.get("PACKAGE_SOURCES_NAMES", ""),
                            os.environ.get("PACKAGE_UNDER_TEST", ""))
        if not args.validate:
            expose(args.source, args.destination, names, repository, ref)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Check Spec Kit-owned files against the hashes recorded by native Spec Kit."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
MANIFESTS = ROOT / ".specify/integrations"
# Beside this script in both layouts — `<root>/scripts` and `<root>/<layout.delivery>/scripts` — which is where
# `check-agents` and the generated `.gitignore` read the harness directories from too.
REGISTRY = Path(__file__).resolve().parent / "agents/registry.json"
PRESETS = ROOT / ".specify/presets"
# The preset manifest is YAML, but a repository gate may not depend on a YAML parser being installed.
# Only one construct matters here — the `file:` values under `provides` — and those are always plain
# quoted scalars, so a line-oriented match reads them without pretending to parse the document.
PRESET_FILE_ENTRY = re.compile(r"""^\s*(?:-\s+)?file:\s*["']?([^"'\s#]+)["']?\s*(?:#.*)?$""", re.MULTILINE)


def profile_findings() -> list[str]:
    metadata_path = ROOT / "project.json"
    constitution_path = ROOT / ".specify/memory/constitution.md"
    if not metadata_path.is_file() or not constitution_path.is_file():
        return []
    metadata = json.loads(metadata_path.read_text())
    if metadata.get("profile") != "standard":
        return []

    constitution = constitution_path.read_text()
    normative_event_sourcing = (
        r"event[- ]sourced\s+(?:core|write model|architecture|system)",
        r"event sourcing\s+(?:is|must|shall)\s+(?:the\s+)?(?:premise|required|mandatory|core)",
        r"(?:must|shall)\b[^\n]{0,100}\bevent store\b",
        r"\bevent store\b[^\n]{0,100}\b(?:must|shall)\b",
    )
    if any(re.search(pattern, constitution, re.IGNORECASE) for pattern in normative_event_sourcing):
        return [
            ".specify/memory/constitution.md: mandates event sourcing, but project.json selects the "
            "standard profile; remove that mandate or scaffold with --profile event-modelling"
        ]
    return []


def preset_findings() -> list[str]:
    """Report a preset layer Spec Kit itself only complains about in its management commands.

    A preset missing its `preset.yml`, or declaring an override whose file is absent, still resolves:
    the templates that do exist keep applying and the missing ones fall through to core. Only
    `specify preset list` says "Corrupted preset", so drift here is invisible to the workflow that
    depends on it. This gate makes it a build failure instead.
    """
    if not PRESETS.is_dir():
        return []
    findings: list[str] = []
    registry_path = PRESETS / ".registry"
    if not registry_path.is_file():
        return [f"{registry_path.relative_to(ROOT)}: missing; the preset layer resolves off this file"]
    try:
        registry = json.loads(registry_path.read_text())
    except json.JSONDecodeError as error:
        return [f"{registry_path.relative_to(ROOT)}: not valid JSON ({error})"]
    presets = registry.get("presets")
    if not isinstance(presets, dict):
        return [f"{registry_path.relative_to(ROOT)}: no presets map"]
    for name, entry in sorted(presets.items()):
        if isinstance(entry, dict) and entry.get("enabled") is False:
            continue
        directory = PRESETS / name
        manifest = directory / "preset.yml"
        if not manifest.is_file():
            findings.append(
                f"{manifest.relative_to(ROOT)}: missing, so Spec Kit reports a corrupted preset "
                f"({name} is enabled in .registry)"
            )
            continue
        for declared in PRESET_FILE_ENTRY.findall(manifest.read_text()):
            if not (directory / declared).is_file():
                findings.append(
                    f"{(directory / declared).relative_to(ROOT)}: declared by "
                    f"{manifest.relative_to(ROOT)} but missing, so the override silently falls back "
                    "to the core template"
                )
    return findings


def projection_directories() -> list[Path]:
    """Every harness directory inside the repository, as `scripts/agents/registry.json` names them.

    The same reading as the generated `.gitignore` and `check-agents`: `skillsDir` and `commandsDir` of every
    harness, once each, leaving out one that projects outside the repository (`~/.hermes/skills`), which no
    clone is missing.
    """
    if not REGISTRY.is_file():
        return []
    harnesses = json.loads(REGISTRY.read_text()).get("harnesses", [])
    directories = [
        entry[key]
        for entry in harnesses
        if isinstance(entry, dict)
        for key in ("skillsDir", "commandsDir")
        if isinstance(entry.get(key), str) and not entry[key].startswith(("~", "/"))
    ]
    return [ROOT / directory.strip("/") for directory in dict.fromkeys(directories)]


def unprojected_directory(relative: str, directories: list[Path]) -> Path | None:
    """The absent projection directory a managed file sits inside, or None where the file is held to its hash.

    Native Spec Kit installs its own `speckit-*` skills and commands into the harness directory — `.claude/skills/`
    for Claude Code — and records their hashes in the manifest, and that directory is in `.gitignore` because
    the factory's projections of `skills/` and `commands/` land in it too. So a fresh clone has the manifest and
    none of the files it lists, the way `check-agents` reads an absent projection: not drift, a clone nobody
    has run `./init` in yet. Only the directory being absent says that. Where it exists, a listed file that is
    missing or edited is drift, and stays a failure.
    """
    path = ROOT / relative
    for directory in directories:
        if path == directory or directory in path.parents:
            return directory if not directory.exists() else None
    return None


def main() -> int:
    findings = profile_findings() + preset_findings()
    valid_presets = len(list(PRESETS.glob("*/preset.yml"))) if PRESETS.is_dir() else 0
    preset_note = f", {valid_presets} preset(s) valid" if valid_presets else ""
    if not MANIFESTS.is_dir():
        if findings:
            print("Spec Kit preset or profile contract violation:", file=sys.stderr)
            print("\n".join(f"  - {finding}" for finding in findings), file=sys.stderr)
            return 1
        print(f"check-speckit: not initialized; nothing managed yet{preset_note}")
        return 0
    manifests = sorted(MANIFESTS.glob("*.manifest.json"))
    directories = projection_directories()
    # Per absent projection directory: the integration whose manifest lists files there, and how many.
    unprojected: dict[Path, tuple[str, int]] = {}
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text())
        integration = manifest.get("integration", manifest_path.stem)
        files = manifest.get("files")
        if not isinstance(files, dict):
            findings.append(f"{manifest_path.relative_to(ROOT)}: invalid files map")
            continue
        for relative, expected in files.items():
            path = ROOT / relative
            directory = unprojected_directory(relative, directories)
            if directory is not None:
                _, count = unprojected.get(directory, (integration, 0))
                unprojected[directory] = (integration, count + 1)
                continue
            if not path.is_file():
                findings.append(f"{relative}: missing (managed by {integration})")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                findings.append(f"{relative}: edited in place (managed by {integration})")
    if findings:
        print("Spec Kit drift, preset or profile contract violation:", file=sys.stderr)
        print("\n".join(f"  - {finding}" for finding in findings), file=sys.stderr)
        print("Repair with: specify integration upgrade <integration>", file=sys.stderr)
        return 1
    for directory, (integration, count) in unprojected.items():
        print(
            f"check-speckit: {directory.relative_to(ROOT)}/: {count} file(s) managed by {integration} not projected "
            "here — the projections are ignored by Git; `./init` writes them"
        )
    print(f"check-speckit: {len(manifests)} manifest(s) match{preset_note}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"check-speckit failed: {error}", file=sys.stderr)
        raise SystemExit(1)

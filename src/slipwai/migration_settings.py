"""What version 1 recorded about the project itself, read once and brought up to version 2's shape.

Flags keep their values and gain the `hoisted` date the strike rule counts from; the release mode and the
product state are derived from what the project has, for a person to correct; the model table gains the
review role as `null`. Separate from the work in flight because these are the project's settings rather
than any slice's history, and because one conflicted `project.json` must not take the rest of them with it.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .convergence import BY_KEY, row
from .layout import layout_of
from .migration_flight import json_bytes
from .migration_merge import Tree, git
from .project.convergence_page import convergence_page


def settings(root: Path, document: dict, files: Tree) -> None:
    """Keep flag values and model choices; add only the newly required migration metadata."""
    today = datetime.now(UTC).date().isoformat()
    historical = git(root, "log", "main", "--diff-filter=AM", "--format=", "--name-only", "--",
                     "*flags.auto.tfvars").decode().splitlines()
    current = set(git(root, "ls-files", "-z", "--", "*flags.auto.tfvars").decode().split("\0")) - {""}
    names = current | {name for name in historical if name.endswith("flags.auto.tfvars")}
    ever_on = False
    for name in sorted(names):
        path = root / name
        history = git(root, "log", "main", "--diff-filter=AM", "--format=%H", "--", name).decode().splitlines()
        for commit in history:
            old = git(root, "show", f"{commit}:{name}").decode("utf-8")
            ever_on |= bool(re.search(r'(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:true\b|"on"(?:\s*(?:#.*)?$))', old))
        if name not in current:
            continue  # a struck/removed flag still establishes product history, but is not recreated
        text = path.read_text(encoding="utf-8")
        # check-flags reads inline notes. Start every existing flag's clock on the crossing day.
        text = re.sub(r"hoisted[:=]?\s*\d{4}-\d{2}-\d{2}", "", text)
        text = re.sub(r"(?m)^(\s*[\w-]+\s*=.*)$", rf"\1 # hoisted: {today}", text)
        files[name] = text.encode("utf-8")
    metadata = json.loads(files["project.json"])
    metadata["releaseMode"] = "open" if document.get("target") == "none" else "flagged"
    metadata["state"] = "in-service" if ever_on else "slipway"
    if document.get("origin") == "adopted":
        rows = [item for item in metadata.get("convergence", []) if item.get("axis") != "release-mode"]
        rows.append(row(BY_KEY["release-mode"], "recorded", f"releaseMode: {metadata['releaseMode']}", "detected"))
        metadata["convergence"] = rows
        layout = layout_of(document)
        files[layout.place("docs/convergence.md")] = convergence_page(document["name"], rows, layout).encode("utf-8")
    ignored = files.get(".gitignore", b"")
    if b".slipwai/logs/" not in ignored.splitlines():
        files[".gitignore"] = (ignored.rstrip(b"\n") +
                              b"\n\n# Deck logs sync through refs/slipwai/logs.\n.slipwai/logs/\n")
    files["project.json"] = json_bytes(metadata)
    for name in (".specify/models.json", "models.json"):
        source = root / name
        if source.is_file():
            models = json.loads(source.read_text(encoding="utf-8"))
            current = json.loads(files.get(name, json_bytes(models)))
            for harness, choices in (models.get("roles") or {}).items():
                if isinstance(choices, dict):
                    held = current.setdefault("roles", {}).setdefault(harness, {})
                    held.update({role: choice for role, choice in choices.items() if role != "skipper"})
                    if "skipper" in choices:
                        held["decide"] = choices["skipper"]
                    held["review"] = None
            files[name] = json_bytes(current)

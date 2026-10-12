"""Read version 1 work in flight once; preserve records and seed version 2's deck logs.

Status fields are not evidence of implementation. Only trunk's slice merge/trailer commits establish
that a slice shipped. Context proposals remain explicit until a person confirms them.
"""
from __future__ import annotations

import json
import re
import runpy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .assets import ROOT
from .convergence import BY_KEY, row
from .errors import GenerationError
from .layout import layout_of
from .logs import Entry, entry
from .migration_merge import Tree, git
from .project.convergence_page import convergence_page


class YAMLReader(Protocol):
    def yaml(self, source: Path) -> object: ...


STATE = ".slipwai/migration.json"
SLICE = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", value) or value in {".", ".."}:
        raise GenerationError(f"{value!r} cannot name a fairway or feature; "
                              "correct the context before `slipwai migrate`")
    return value


def shipped(root: Path, slice_id: str) -> str | None:
    """A committed slice merge or explicit trailer on trunk, never a model's optimistic status."""
    history = git(root, "log", "main", "--format=%H%x00%B%x00").decode("utf-8").split("\0")
    for at in range(0, len(history) - 1, 2):
        commit, body = history[at].strip(), history[at + 1]
        if re.search(rf"(?m)^Slice-done:\s*{re.escape(slice_id)}\s*$", body) or re.search(
            rf"(?m)^Merge .*['\"]slice/{re.escape(slice_id)}['\"]", body
        ):
            return commit
    return None


@dataclass
class Flight:
    files: Tree = field(default_factory=dict)
    logs: list[tuple[str, str, Entry]] = field(default_factory=list)
    features: dict[str, dict] = field(default_factory=dict)

    @property
    def counts(self) -> tuple[int, int]:
        return (sum(len(item["proposed"]) for item in self.features.values()),
                sum(len(item["unplaced"]) for item in self.features.values()))


def plan_context(text: str, contexts: list[str]) -> str:
    """Only an explicit Structure Decision context, or the project's single possible context."""
    decision = re.search(r"(?is)#+\s*Structure Decision\b(.*?)(?=\n#+ |\Z)", text)
    if decision:
        named = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?context(?:\*\*)?\s*:\s*[`\"']?([\w.-]+)",
                          decision[1])
        if named:
            return identifier(named[1])
    return contexts[0] if len(contexts) == 1 else "unplaced"


def frozen(flight: Flight, feature: Path) -> None:
    renderer = runpy.run_path(str(ROOT / "assets/toolkit/scripts/render-fairways.py"))
    for name in renderer["FOLDED"]:
        source = feature / name
        if source.is_file():
            original = source.read_bytes()
            flight.files[f"fairways/main/{feature.name}/{name}"] = original
            parts = renderer["ordered"](renderer["entries"](original.decode("utf-8")))
            text = renderer["BANNER"].format(name=name) + "\n" + "\n".join(parts)
            flight.files[f"specs/{feature.name}/{name}"] = text.encode("utf-8")


def model_bytes(source: Path, model: dict) -> bytes:
    """Reconcile fields without discarding the person's YAML comments or rendering settings."""
    original = source.read_text(encoding="utf-8")
    try:
        json.loads(original)
    except ValueError:
        for item in model.get("slices", []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            pattern = re.compile(r"(?m)^(?P<indent> *)- id: *[\"']?" + re.escape(str(item["id"])) +
                                 r"[\"']? *(?:#.*)?$")
            match = pattern.search(original)
            if match is None:
                raise GenerationError(f"{source}: slice {item['id']} has an inline or unreadable YAML id; "
                                      "put each slice's `- id:` on its own line before `slipwai migrate`") from None
            indent = match["indent"] + "  "
            following = re.search(r"(?m)^" + re.escape(match["indent"]) + r"- ", original[match.end():])
            end = match.end() + following.start() if following else len(original)
            block = original[match.start():end]
            for key in ("status", "context", "capability"):
                if key not in item:
                    continue
                field = re.compile(r"(?m)^" + re.escape(indent) + re.escape(key) + r": *[^\n#]*(?P<note>#[^\n]*)?$")
                replacement = indent + key + ": " + json.dumps(item[key])
                if field.search(block):
                    def substitute(found: re.Match[str], replacement: str = replacement) -> str:
                        return replacement + (" " + found["note"] if found["note"] else "")
                    block = field.sub(substitute, block)
                else:
                    block += "\n" + replacement + "\n"
            original = original[:match.start()] + block + original[end:]
        return original.encode("utf-8")
    return json_bytes(model)


def read(root: Path, document: dict, legacy: YAMLReader) -> Flight:
    """Immutable migrated data, prepared before any project file or branch is changed."""
    flight = Flight()
    layout = layout_of(document)
    deployables = document.get("deployables") or {}
    services = {name: record for name, record in deployables.items() if record.get("kind") == "service"}
    contexts = sorted({str(context) for record in services.values()
                       for context in (record.get("contexts") or [record.get("context") or ""])
                       if context})
    model_path = root / layout.place("docs/event-model/model.yaml")
    model = legacy.yaml(model_path) if model_path.is_file() else {}
    model = model if isinstance(model, dict) else {}
    items = [item for item in model.get("slices", []) if isinstance(item, dict) and item.get("id")]
    renderer = runpy.run_path(str(ROOT / "assets/toolkit/scripts/event-model/chart.py"))
    features = sorted((root / "specs").glob("*/story-split.md"))
    for split in features:
        feature = split.parent
        name = identifier(feature.name)
        frozen(flight, feature)
        found = sorted(set(SLICE.findall(split.read_text(encoding="utf-8"))) |
                       {path.name for path in (feature / "slices").glob("*") if path.is_dir()})
        local = [dict(item) for item in items if str(item["id"]) in found]
        if document["profile"] != "event-modelling":
            local = []
            for slice_id in found:
                plans = sorted((feature / "slices" / slice_id).glob("*plan*.md"))
                text = "\n".join(path.read_text(encoding="utf-8") for path in plans)
                local.append({"id": slice_id, "context": plan_context(text, contexts),
                              "capability": slice_id, "frames": [], "reads": []})
        recorded = {str(item["id"]) for item in local}
        local += [{"id": slice_id, "context": "unplaced", "capability": slice_id,
                   "frames": [], "reads": []} for slice_id in found if slice_id not in recorded]
        for item in local:
            item["context"] = identifier(str(item.get("context") or "unplaced"))
            item.setdefault("capability", str(item.get("name") or item["id"]))
        chart = renderer["render"]({"slices": local}, deployables,
                                    model_path.relative_to(root).as_posix())
        chart["feature"] = name
        unplaced = [str(item["id"]) for item in local if item["context"] == "unplaced"]
        fairways = sorted(chart["fairways"])
        proposed = fairways if len(fairways) > 1 or unplaced else []
        flight.features[name] = {"proposed": proposed, "unplaced": unplaced}
        flight.files[f"specs/{name}/chart.yaml"] = json_bytes(chart)
        for item in local:
            slice_id, fairway = str(item["id"]), str(item["context"])
            commit = shipped(root, slice_id)
            if commit:
                flight.logs.append((name, fairway, entry("merged", fairway=fairway, slice=slice_id, commit=commit)))
                for mark in chart["slices"][slice_id]["sets"]:
                    flight.logs.append((name, fairway, entry("mark-set", fairway=fairway, slice=slice_id, mark=mark)))
            for original in items:
                if original["id"] == slice_id:
                    original["status"] = "implemented" if commit else "planned"
                    original["context"] = item["context"]
                    original.setdefault("capability", item["capability"])
    if items:
        flight.files[model_path.relative_to(root).as_posix()] = model_bytes(model_path, model)
    old_log = root / "specs/cruise-log.jsonl"
    if old_log.is_file() and flight.features:
        lines = [json.loads(line) for line in old_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        last = lines[-1] if lines else {}
        reason = str(last.get("last_line") or "")
        if "parked:" in reason:
            active_feature = next(iter(flight.features))
            flight.logs.append((active_feature, "main", entry("parked", fairway="main",
                                                 why=reason.split("parked:", 1)[1].strip())))
    if flight.features:
        flight.files[STATE] = json_bytes({"v": 1, "features": flight.features})
    return flight


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

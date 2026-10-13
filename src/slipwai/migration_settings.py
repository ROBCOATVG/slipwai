"""What version 1 recorded about the project itself, read once and brought up to version 2's shape.

Flags keep their values and gain the `hoisted` date the strike rule counts from; the release mode and the
product state are derived from what the project has, for a person to correct; the model table gains the
review role as `null`. Separate from the work in flight because these are the project's settings rather
than any slice's history, and because one conflicted `project.json` must not take the rest of them with it.
"""
from __future__ import annotations

import json
import re
from collections.abc import Collection
from datetime import UTC, datetime
from pathlib import Path

from .convergence import BY_KEY, row
from .layout import layout_of
from .migration_flight import json_bytes
from .migration_merge import Tree, git
from .project.convergence_page import convergence_page


def settings(root: Path, document: dict, files: Tree, *, conflicts: Collection[str] = ()) -> list[str]:
    """Keep flag values and model choices; add only the newly required migration metadata.

    `conflicts` are the files the three-way merge left with conflict markers in them, which no reader can
    parse. Only the keys that live in those files are then left to the person — said out loud, on the
    catch-up page, rather than passed over in silence. Everything else here still applies, and two of them
    matter immediately: the `hoisted` date is what the strike rule counts from, so a flag that never gets
    one never starts counting; and `.slipwai/logs/` in `.gitignore` is what keeps the deck logs `seed`
    writes a few lines later out of the person's `git status`, where AGENTS.md says they are never
    committed from.

    It is the whole set and not `project.json` alone because the model table conflicts too, and parsing one
    that had is how a person's crossing ended in a `JSONDecodeError` out of the standard library — a
    traceback, on a real repository, at the point where the merge had already been done and nothing said
    which file it was about.
    """
    notes: list[str] = []
    contested = "project.json" in conflicts
    today = datetime.now(UTC).date().isoformat()
    # Every read of git here is surrogateescaped, as the rest of the crossing is: one commit message or
    # one blob that is not UTF-8 is not a reason a person's migration stops with a traceback.
    historical = git(root, "log", "main", "--diff-filter=AM", "--format=", "--name-only", "--",
                     "*flags.auto.tfvars").decode(errors="surrogateescape").splitlines()
    current = set(git(root, "ls-files", "-z", "--", "*flags.auto.tfvars")
                  .decode(errors="surrogateescape").split("\0")) - {""}
    names = current | {name for name in historical if name.endswith("flags.auto.tfvars")}
    ever_on = False
    for name in sorted(names):
        path = root / name
        history = git(root, "log", "main", "--diff-filter=AM", "--format=%H", "--",
                      name).decode(errors="surrogateescape").splitlines()
        for commit in history:
            old = git(root, "show", f"{commit}:{name}").decode("utf-8", errors="surrogateescape")
            ever_on |= bool(re.search(r'(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*(?:true\b|"on"(?:\s*(?:#.*)?$))', old))
        if name not in current:
            continue  # a struck/removed flag still establishes product history, but is not recreated
        text = path.read_text(encoding="utf-8")
        # check-flags reads inline notes. Start every existing flag's clock on the crossing day.
        text = re.sub(r"hoisted[:=]?\s*\d{4}-\d{2}-\d{2}", "", text)
        text = re.sub(r"(?m)^(\s*[\w-]+\s*=.*)$", rf"\1 # hoisted: {today}", text)
        files[name] = text.encode("utf-8")
    if contested:
        mode = "open" if document.get("target") == "none" else "flagged"
        state = "in-service" if ever_on else "slipway"
        extra = (" and the release-mode row of the convergence map, so `docs/convergence.md` still reads as "
                 "it did" if document.get("origin") == "adopted" else "")
        notes.append(f"`project.json` conflicted, so this crossing could not write its releaseMode, its "
                     f"state{extra}. Resolve the conflict, then set `\"releaseMode\": \"{mode}\"` and "
                     f"`\"state\": \"{state}\"` by hand and run `make verify`. Every flag's `hoisted` date, "
                     "the model table's review role and the `.slipwai/logs/` ignore rule were written.")
    else:
        metadata = json.loads(files["project.json"])
        metadata["releaseMode"] = "open" if document.get("target") == "none" else "flagged"
        metadata["state"] = "in-service" if ever_on else "slipway"
        if document.get("origin") == "adopted":
            rows = [item for item in metadata.get("convergence", []) if item.get("axis") != "release-mode"]
            rows.append(row(BY_KEY["release-mode"], "recorded",
                            f"releaseMode: {metadata['releaseMode']}", "detected"))
            metadata["convergence"] = rows
            layout = layout_of(document)
            files[layout.place("docs/convergence.md")] = convergence_page(
                document["name"], rows, layout).encode("utf-8")
        files["project.json"] = json_bytes(metadata)
    ignored = files.get(".gitignore", b"")
    if b".slipwai/logs/" not in ignored.splitlines():
        files[".gitignore"] = (ignored.rstrip(b"\n") +
                              b"\n\n# Deck logs sync through refs/slipwai/logs.\n.slipwai/logs/\n")
    for name in (".specify/models.json", "models.json"):
        source = root / name
        if source.is_file():
            if name in conflicts:
                # The roles are carried by rewriting the merged file, and a conflicted one cannot be read
                # to rewrite. Said rather than skipped: a review role that silently never arrived is a
                # stage that runs on the wrong model for as long as nobody looks.
                notes.append(f"`{name}` conflicted, so this crossing could not carry version 1's model "
                             f"roles into it. Resolve the conflict, then for each harness set `decide` to "
                             f"what `skipper` was and add `\"review\": null` beside it, and run `make "
                             f"check-agents` — every other setting here was written.")
                continue
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
    return notes

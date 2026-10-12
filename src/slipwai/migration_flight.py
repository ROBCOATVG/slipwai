"""Read version 1 work in flight once; preserve records and seed version 2's deck logs.

Status fields are not evidence of implementation. Only trunk's slice merge/trailer commits establish
that a slice shipped. Context proposals remain explicit until a person confirms them.
"""
from __future__ import annotations

import json
import re
import runpy
from collections.abc import Collection
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Protocol

from .assets import ROOT
from .errors import GenerationError
from .layout import layout_of
from .logs import Entry, entry
from .migration_merge import Tree, git


class YAMLReader(Protocol):
    def yaml(self, source: Path) -> object: ...


STATE = ".slipwai/migration.json"
SLICE = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")
#: What a fairway or a feature may be called: one path component, on every platform and in a git ref.
NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]*")
#: What version 1's runner — version 1's own word for what a captain replaced — left behind. All three
#: stay at the repository root under an adopted project's `layout.delivery`, because `specs/` and
#: `.specify/` are not delivery material and do not move.
#: `cruise-told.jsonl` is what an iteration was handed; `cruise-inbox.jsonl` is what nobody has taken
#: yet. Version 1 put the first back ahead of the second at the start of every run, because a person's
#: word is not spent by an iteration that died, and this reads them in that same order.
LEGACY_LOG = "specs/cruise-log.jsonl"
LEGACY_GIVEN = ".specify/cruise-told.jsonl"
LEGACY_QUEUED = ".specify/cruise-inbox.jsonl"


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def identifier(value: str) -> str:
    if not NAME.fullmatch(value) or value in {".", ".."}:
        raise GenerationError(f"{value!r} cannot name a fairway or feature; "
                              "correct the context before `slipwai migrate`")
    return value


def legacy_lines(path: Path) -> list[dict]:
    """One of version 1's JSONL files, or a refusal naming the line that stopped it.

    Never skipped past: a record missing the entries it could not parse reads exactly like a record of a
    run that did not have them, and this is the only account there is of what a person said.
    """
    unreadable = "is not one readable JSON object; repair or delete the file, then run `slipwai migrate` again"
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            body = json.loads(line)
        except ValueError as error:
            raise GenerationError(f"{path} line {number} {unreadable} ({error})") from None
        if not isinstance(body, dict):
            raise GenerationError(f"{path} line {number} {unreadable}")
        found.append(body)
    return found


def queued(root: Path) -> list[Entry]:
    """A person's words that no version 1 iteration finished acting on, as version 2's unanswered `told`s.

    Each keeps the instant it was said rather than the instant it was migrated, so the board puts them in
    the order the person said them. Nothing answers them here: a `read` receipt is a captain saying it has
    taken the message, and no captain has.
    """
    lines = []
    for name in (LEGACY_GIVEN, LEGACY_QUEUED):
        path = root / name
        if not path.is_file():
            continue
        for body in legacy_lines(path):
            message = " ".join(str(body.get("text") or "").split())
            if message:
                lines.append(replace(entry("told", fairway="main", message=message),
                                     t=str(body.get("at") or "")))
    return lines


def stopped(root: Path) -> str:
    """Why version 1's run is not running, in version 2's one shape for it, or "" where nothing is owed.

    Version 1 ended an iteration on one of four last lines, and version 2 has a single shape for every one
    of them that is not an ending: a `parked` with its reason. `cruise: done` is the one that owes nobody
    anything — every specification was satisfied — so it leaves no line, and a fairway with nothing parked
    on it is one a person is not asked about. `cruise: parked: <why>` keeps the person's own words.
    `cruise: stopped: human` recorded no reason beyond the person, so that is the reason, said rather than
    left to be guessed at. Everything else is a run that stopped without saying why — killed, ended for a
    message, or ended on a line version 1's runner did not recognise — and naming the iteration and the line it
    ended on is the most anybody can be told. None of them is silently dropped: a crossing that reads a
    stopped run as a finished one is one that loses the only record of why somebody stopped.
    """
    path = root / LEGACY_LOG
    if not path.is_file():
        return ""
    lines = legacy_lines(path)
    if not lines:
        return ""
    last = lines[-1]
    where = f" at iteration {last['iteration']}" if last.get("iteration") is not None else ""
    ending = str(last.get("last_line") or "").strip()
    if "parked:" in ending:
        return ending.split("parked:", 1)[1].strip() or f"version 1 parked{where} and recorded no reason"
    if ending == "cruise: done":
        return ""
    if ending == "cruise: stopped: human":
        return (f"a person stopped the version 1 run{where}; it recorded no reason beyond that, so confirm "
                "there is nothing left owed before this fairway is claimed")
    return (f"the version 1 run stopped{where} without recording an ending; its last line was "
            f"{ending or 'never written'}")


def shipped(root: Path, slice_id: str) -> str | None:
    """A committed slice merge or explicit trailer on trunk, never a model's optimistic status.

    A merge subject counts whenever it names the claim branch: Git's own default (`Merge branch
    'slice/X'`), GitLab's (`... into 'main'`) and a GitHub pull-request merge (`Merge pull request #12
    from acme/slice/X`). A *squash* merge through either forge keeps no branch name — its subject is the
    pull request's title — so there is nothing here to read, and reading a subject that merely mentions
    an id would call `Start slice/X` a merge. Hence no demotion above: unproven is unknown, not unstarted.
    """
    history = git(root, "log", "main", "--format=%H%x00%B%x00").decode("utf-8", errors="surrogateescape").split("\0")
    for at in range(0, len(history) - 1, 2):
        commit, body = history[at].strip(), history[at + 1]
        if re.search(rf"(?m)^Slice-done:\s*{re.escape(slice_id)}\s*$", body) or re.search(
            rf"(?m)^Merge\b[^\n]*\bslice/{re.escape(slice_id)}(?![\w./-])", body
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


def home(root: Path, flight: Flight) -> str:
    """Which feature's directory version 1's one loop writes its lines under.

    The first feature with a split, where there is one. A project that ran `/specify` and `/plan` but
    never `/split` has no such feature and still has every word somebody said, so the first feature
    directory it does have takes them, and a project with none of those puts them under `main`.
    """
    if flight.features:
        return next(iter(flight.features))
    for path in sorted((root / "specs").glob("*")):
        if path.is_dir() and NAME.fullmatch(path.name):
            return path.name
    return "main"


def read(root: Path, document: dict, legacy: YAMLReader, claims: Collection[str] = ()) -> Flight:
    """Immutable migrated data, prepared before any project file or branch is changed.

    `claims` are the slices whose version 1 claim branch is ahead of trunk, which only `--with-claims`
    reaches: without it the crossing refuses before any of this runs.
    """
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
            elif slice_id in claims:
                # A claim branch ahead of trunk is work in flight, and version 2 reads work in flight from
                # lines alone. Without this the migrated board draws the slice as never started while the
                # branch the catch-up page tells the person to rebase sits there holding their commits.
                # Never beside a `merged`: a slice trunk already has is finished, whatever a branch left
                # behind still points at, and `slice_now` is the last claim that has not merged.
                flight.logs.append((name, fairway, entry("claimed", fairway=fairway, slice=slice_id)))
            for original in items:
                if original["id"] == slice_id:
                    # Section 6 authorises one direction: a slice whose code is on `main` is
                    # `implemented`, whatever the field said. Nothing authorises the other. Writing
                    # `planned` over an unproven slice promoted a `proposed` one to a rung nobody
                    # modelled — `check-model` then asks it for the stream, guard, materialisation and
                    # live budget `planned` commits to, and the migrated project's own `make verify`
                    # goes red — and demoted every slice squash-merged through a forge default, which
                    # keeps no branch name for `shipped` to read.
                    if commit:
                        original["status"] = "implemented"
                    original["context"] = item["context"]
                    original.setdefault("capability", item["capability"])
    if items:
        flight.files[model_path.relative_to(root).as_posix()] = model_bytes(model_path, model)
    # Version 1 ran one loop over the whole project, so its messages and its stop belong to the `main`
    # fairway, beside the records frozen there. Carried whether or not any feature has a split: they are
    # the project's loop's, not any feature's, and the crossing is the moment that loop stops running —
    # after it nothing will ever surface those words or that reason again.
    where = home(root, flight)
    flight.logs += [(where, "main", line) for line in queued(root)]
    why = stopped(root)
    if why:
        flight.logs.append((where, "main", entry("parked", fairway="main", why=why)))
    if flight.features:
        flight.files[STATE] = json_bytes({"v": 1, "features": flight.features})
    return flight

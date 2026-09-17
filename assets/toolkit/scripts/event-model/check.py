#!/usr/bin/env python3
"""Validate the global event model. Rendering lives in the TypeScript pipeline (`make model`)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import importlib
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


ROOT = project_root(Path(__file__).resolve(), 2)
# The model sits beside this script's tree — `docs/` next to `scripts/`, wherever the two live.
MODEL = Path(__file__).resolve().parents[2] / "docs/event-model/model.yaml"
MANIFEST = ROOT / "project.json"
TOOLS = ROOT / ".delivery-tools"
#: What an attribute may say it identifies: a kind, lower case, because it becomes a tag's key.
IDENTIFIES = re.compile(r"[a-z][a-z0-9-]*")


def project_services() -> dict[str, list[str]]:
    """The services `project.json` lists, in order, each with the bounded contexts it holds — what a slice's
    `service` and `context` may name.

    Mirrors `workspace.ts`. A service's contexts are its `contexts`, or the one `context` an older manifest
    named, or itself. An unreadable manifest is an empty mapping rather than an error: the rules below then
    have nothing to require, and the manifest's own readers report it.
    """
    try:
        document = json.loads(MANIFEST.read_text())
    except (OSError, ValueError):
        return {}
    deployables = document.get("deployables") if isinstance(document, dict) else None
    if not isinstance(deployables, dict):
        return {}
    services: dict[str, list[str]] = {}
    for name, record in deployables.items():
        if not isinstance(record, dict) or record.get("kind") != "service":
            continue
        contexts = record.get("contexts")
        if not isinstance(contexts, list) or not contexts:
            context = record.get("context")
            contexts = [context if isinstance(context, str) and context else name]
        services[name] = [str(context) for context in contexts]
    return services


def load_yaml() -> object:
    sys.path.insert(0, str(TOOLS))
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                "--target",
                str(TOOLS),
                "-r",
                str(Path(__file__).with_name("requirements.txt")),
            ],
            check=True,
        )
        importlib.invalidate_caches()
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(MODEL.read_text())


def validate(model: object, services: dict[str, list[str]] | None = None) -> list[str]:
    if not isinstance(model, dict):
        return ["model root must be a mapping"]
    services = project_services() if services is None else services
    placed = {"modelled", "planned", "implemented"}
    findings: list[str] = []
    if model.get("version") != 1:
        findings.append("version must be 1")
    slices = model.get("slices")
    if not isinstance(slices, list):
        return findings + ["slices must be a list"]
    ids: set[str] = set()
    produced: dict[str, int] = {}
    allowed_status = {"proposed", "modelled", "planned", "implemented"}
    shapes = {
        "state-change": ({"ui", "pcr"}, "cmd", "evt"),
        "state-view": ("rmo",),
        "automation": ("rmo", "pcr", "cmd", "evt"),
        "translation": ("evt", "pcr", "cmd", "evt"),
    }
    for index, item in enumerate(slices):
        label = f"slices[{index}]"
        if not isinstance(item, dict):
            findings.append(f"{label} must be a mapping")
            continue
        slice_id = item.get("id")
        if not isinstance(slice_id, str) or not slice_id:
            findings.append(f"{label}.id must be a non-empty string")
            slice_id = label
        elif slice_id in ids:
            findings.append(f"{slice_id}: duplicate slice id")
        ids.add(slice_id)
        pattern = item.get("pattern")
        status = item.get("status")
        if pattern not in shapes:
            findings.append(f"{slice_id}: unknown pattern {pattern!r}")
        if status not in allowed_status:
            findings.append(f"{slice_id}: unknown status {status!r}")
        frames = item.get("frames")
        if not isinstance(frames, list) or not frames:
            findings.append(f"{slice_id}: frames must be a non-empty list")
            continue
        frame_types = [frame.get("type") if isinstance(frame, dict) else None for frame in frames]
        if pattern == "state-change":
            valid = len(frame_types) >= 3 and frame_types[0] in {"ui", "pcr"} and frame_types[1] == "cmd" and all(
                value == "evt" for value in frame_types[2:]
            )
        elif pattern == "state-view":
            valid = frame_types in (["rmo"], ["rmo", "ui"])
        elif pattern == "automation":
            valid = len(frame_types) >= 4 and frame_types[:3] == ["rmo", "pcr", "cmd"] and all(
                value == "evt" for value in frame_types[3:]
            )
        elif pattern == "translation":
            valid = len(frame_types) >= 4 and frame_types[0:3] == ["evt", "pcr", "cmd"] and all(
                value == "evt" for value in frame_types[3:]
            )
            first = frames[0] if isinstance(frames[0], dict) else {}
            valid = valid and first.get("external") is True
        else:
            valid = False
        if not valid:
            findings.append(f"{slice_id}: frames do not match the {pattern!r} pattern")
        reads = item.get("reads", [])
        if pattern in {"state-view", "automation"} and not reads:
            findings.append(f"{slice_id}: {pattern} requires reads")
        if isinstance(reads, list):
            for event in reads:
                if event not in produced:
                    findings.append(f"{slice_id}: reads {event!r}, which no earlier slice produces")
        # What an event carries, and which of it identifies something. The structured form of `data`,
        # and the only place the tag index can be derived from: a tag is `<kind>:<value>`, so an event
        # that marks which attributes identify a course or a seat is an event whose `tags_of` is
        # generated rather than typed. Tags themselves stay out of the model — they are a technical
        # index, not a fact about the business — and identity does not.
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            attributes = frame.get("attributes")
            if attributes is None:
                continue
            name = frame.get("name", "a frame")
            if not isinstance(attributes, list) or not attributes:
                findings.append(f"{slice_id}: {name}.attributes must be a non-empty list")
                continue
            if frame.get("type") != "evt":
                findings.append(
                    f"{slice_id}: {name} is a {frame.get('type')!r} box and carries `attributes`, which "
                    "only an event has — the tag index is derived from events, and marking identity "
                    "elsewhere implies a guard that does not exist"
                )
            if frame.get("data") is not None:
                findings.append(
                    f"{slice_id}: {name} carries both `data` and `attributes`, which are two places for "
                    "one list. Keep the attributes: they say which of them identify something, and the "
                    "diagram is rendered from them"
                )
            seen_attributes: set[str] = set()
            for attribute in attributes:
                if not isinstance(attribute, dict) or not isinstance(attribute.get("name"), str):
                    findings.append(f"{slice_id}: {name} has an attribute with no name")
                    continue
                attribute_name = attribute["name"]
                if attribute_name in seen_attributes:
                    findings.append(
                        f"{slice_id}: {name} names the attribute {attribute_name!r} twice. One entry per "
                        "attribute: an event carrying two of the same kind names them differently and "
                        "marks both, which is how `fromAccount` and `toAccount` both identify an account"
                    )
                seen_attributes.add(attribute_name)
                identifies = attribute.get("identifies")
                if identifies is not None and not IDENTIFIES.fullmatch(str(identifies)):
                    findings.append(
                        f"{slice_id}: {name}.{attribute_name} identifies {identifies!r}, which is not a "
                        "kind — lower case, like `course` or `seat`, because it becomes the tag's key"
                    )
        # What the append is guarded by, and a state-change slice declares one of the two: `stream`,
        # whose version the append carries, or `guard`, a boundary drawn over tags per decision. Both
        # are consistency boundaries and therefore concurrency ceilings, and both are unmigratable once
        # there is history — which is why the answer is owed at `planned` rather than at the first
        # conflict. Mirrors validate.ts's `guard-before-planning`, `one-guard-not-two` and
        # `guard-names-its-kinds`.
        guard = item.get("guard")
        if item.get("stream") and guard is not None:
            findings.append(
                f"{slice_id}: declares both `stream` and `guard`, which are two answers to one question. "
                "An append is checked against the version of one stream *or* against a query over tags"
            )
        if guard is not None:
            by = guard.get("by") if isinstance(guard, dict) else None
            because = guard.get("because") if isinstance(guard, dict) else None
            if not isinstance(by, list) or not by or any(
                not isinstance(kind, str) or not IDENTIFIES.fullmatch(kind) for kind in by
            ):
                findings.append(
                    f"{slice_id}: `guard.by` names the kinds the boundary is drawn over — lower case, like "
                    "`seat` or `hold`, because each becomes a tag key in the query the append is guarded "
                    "with"
                )
            if not isinstance(because, str) or not because.strip():
                findings.append(
                    f"{slice_id}: `guard.because` names the invariant this boundary protects, in one "
                    "sentence. Unstated, a boundary is a query somebody widened until the tests passed"
                )
        if (
            status in {"planned", "implemented"}
            and pattern == "state-change"
            and not item.get("stream")
            and guard is None
        ):
            findings.append(
                f"{slice_id}: a planned state change names what its append is guarded by — `stream`, whose "
                "version the append carries, or `guard`, a boundary drawn over tags"
            )
        # Where the read model lives. This is the read side's version of the question `stream` asks on the
        # write side, and it is required from `planned` for the same reason: one fixes the consistency
        # boundary, the other fixes what a query costs, and both are decided once and paid for afterwards. A
        # slice that reaches a plan with no answer gets the cheapest one by gravity — a fold over the log on
        # every query — because that is the only read path the skeleton already has, and nothing downstream
        # asks again.
        materialisation = item.get("materialisation")
        budget = item.get("liveBudget")
        if pattern in {"state-view", "automation"}:
            if materialisation is None:
                if status in {"planned", "implemented"}:
                    findings.append(
                        f"{slice_id}: a planned {pattern} names where its read model lives in "
                        "`materialisation` — `live` (folded per query, nothing stored), `inline` (written in "
                        "the append's transaction) or `async` (a catch-up subscription with a checkpoint)"
                    )
            elif materialisation not in {"live", "inline", "async"}:
                findings.append(
                    f"{slice_id}: unknown materialisation {materialisation!r} (live, inline or async)"
                )
            elif materialisation == "live" and pattern == "automation":
                findings.append(
                    f"{slice_id}: an automation's read model is its todo list, so it must be persisted — "
                    "`inline` or `async`. Folded per query it cannot be spawned standalone, and the work a "
                    "dead request abandoned is lost with nothing left recording that it was owed"
                )
        elif materialisation is not None:
            findings.append(
                f"{slice_id}: `materialisation` says where a read model lives, and a {pattern} slice has none"
            )
        # The budget is asked for only where `live` is an answer the pattern may give: a refused `live` has
        # been reported once already, and asking it to bound a fold it is not allowed to do in the first
        # place says nothing a reader can act on.
        if pattern == "state-view" and materialisation == "live":
            events = budget.get("events") if isinstance(budget, dict) else None
            because = budget.get("because") if isinstance(budget, dict) else None
            if isinstance(events, bool) or not isinstance(events, int) or events < 1:
                findings.append(
                    f"{slice_id}: materialisation `live` folds the log on every query, so it names the "
                    "ceiling one query may fold in `liveBudget.events`. Unbounded, a short stream is an "
                    "assumption nothing measures and no gate can fail"
                )
            if not isinstance(because, str) or not because.strip():
                findings.append(
                    f"{slice_id}: materialisation `live` names why that ceiling holds in "
                    "`liveBudget.because`, in terms of the stream's own lifetime"
                )
        elif budget is not None:
            findings.append(
                f"{slice_id}: `liveBudget` bounds the fold a `live` state-view does on every query, and this "
                + (
                    "read model is materialised, so its cost belongs to the subscription that maintains it"
                    if materialisation in {"inline", "async"}
                    else "slice does not declare one"
                )
            )
        # Which service owns the slice. Mirrors validate.ts's `service-named` and `service-exists`: with one
        # service there is nothing to decide, so the field is optional; with two or more, a modelled slice
        # that names none would land in the first service by gravity, which is the placement this exists
        # to make a decision rather than a default.
        service = item.get("service")
        if service is not None and (not isinstance(service, str) or service not in services):
            findings.append(
                f"{slice_id}: names service {service!r}, which project.json does not list"
                + (f" (it has {', '.join(services)})" if services else "")
            )
        elif service is None and len(services) > 1 and status in placed:
            findings.append(
                f"{slice_id}: this project has {len(services)} services ({', '.join(services)}); a modelled "
                "slice names the one that owns it in `service`, chosen against each service's purpose in "
                "project.json"
            )
        # Which bounded context inside that service. Mirrors validate.ts's `context-exists` and
        # `context-named`: a service holding one context has nothing to decide; one holding several is the
        # modular monolith this project starts as, and a slice placed in the service but in no context is
        # placed by gravity again — into whichever `src/<context>/` the implementer reaches for first.
        owner = service if service in services else next(iter(services)) if len(services) == 1 else None
        held = services.get(owner, []) if owner is not None else []
        context = item.get("context")
        if context is not None and owner is not None and context not in held:
            findings.append(
                f"{slice_id}: names context {context!r}, which service {owner} does not hold (it holds "
                f"{', '.join(held)})"
            )
        elif context is None and len(held) > 1 and status in placed:
            findings.append(
                f"{slice_id}: service {owner} holds {len(held)} bounded contexts ({', '.join(held)}); a "
                "modelled slice names the one it belongs to in `context`"
            )
        if status == "implemented":
            for key in ("gwt", "code"):
                value = item.get(key)
                paths = value if isinstance(value, list) else [value]
                if not value or any(not isinstance(path, str) or not (ROOT / path).exists() for path in paths):
                    findings.append(f"{slice_id}: implemented slice has missing {key} evidence")
        for frame in frames:
            if isinstance(frame, dict) and frame.get("type") == "evt" and frame.get("external") is not True:
                name = frame.get("name")
                if isinstance(name, str):
                    if name in produced:
                        findings.append(f"{slice_id}: event {name!r} is produced by more than one slice")
                    produced[name] = index
        page = model.get("render", {}).get("page") if isinstance(model.get("render"), dict) else None
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            mockups = frame.get("mockups")
            if mockups is None:
                continue
            frame_name = frame.get("name", "?")
            # Mirrors the pipeline's mockup rules (validate.ts), so `make verify` holds the mockups
            # process without Node: only a screen has mocks, one mock per state, relative mocks exist,
            # and a published page can only serve mocks that live beside it.
            if frame.get("type") != "ui":
                findings.append(f"{slice_id}: frame {frame_name!r} has mockups but is not a ui frame")
            if not isinstance(mockups, list) or not mockups:
                findings.append(f"{slice_id}: frame {frame_name!r} mockups must be a non-empty list")
                continue
            states: set[str] = set()
            for mockup in mockups:
                if not isinstance(mockup, dict) or not mockup.get("state") or not mockup.get("at"):
                    findings.append(f"{slice_id}: frame {frame_name!r} mockup entries need state and at")
                    continue
                state, at = str(mockup["state"]), str(mockup["at"])
                if state in states:
                    findings.append(f"{slice_id}: frame {frame_name!r} has two mockups for state {state!r}")
                states.add(state)
                if at.startswith(("http://", "https://")):
                    continue
                if not (ROOT / at).exists():
                    findings.append(f"{slice_id}: frame {frame_name!r} mockup {at!r} does not exist")
                if page and not at.startswith("docs/event-model/"):
                    findings.append(
                        f"{slice_id}: frame {frame_name!r} mockup {at!r} is outside docs/event-model/, "
                        "so the published page cannot serve it"
                    )
    findings += depends_on_findings(slices)
    findings += folds_match_their_guard(slices)
    return findings



def depends_on_findings(slices: list) -> list[str]:
    """Build-order deps are separate from timeline `reads`.

    `depends_on` is who must be *archived* before this slice may start. Reading events another slice
    produces is not a build dependency — Principle V says seed from synthetic events instead — so a
    `depends_on` set that is exactly the producers of this slice's `reads` is an artificial chain.
    """
    findings: list[str] = []
    by_id: dict[str, dict] = {}
    for item in slices:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            by_id[item["id"]] = item

    # Event → producing slice id (first producer wins, matching the reads-earlier rule).
    producers: dict[str, str] = {}
    for item in slices:
        if not isinstance(item, dict):
            continue
        slice_id = item.get("id")
        if not isinstance(slice_id, str):
            continue
        frames = item.get("frames") or []
        if not isinstance(frames, list):
            continue
        for frame in frames:
            if isinstance(frame, dict) and frame.get("type") == "evt" and isinstance(frame.get("name"), str):
                producers.setdefault(frame["name"], slice_id)

    for item in slices:
        if not isinstance(item, dict):
            continue
        slice_id = item.get("id")
        if not isinstance(slice_id, str):
            continue
        deps = item.get("depends_on", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            findings.append(f"{slice_id}: depends_on must be a list of slice ids")
            continue
        if not deps:
            continue
        dep_ids: list[str] = []
        for dep in deps:
            if not isinstance(dep, str) or not dep:
                findings.append(f"{slice_id}: depends_on entries must be non-empty strings")
                continue
            if dep == slice_id:
                findings.append(f"{slice_id}: depends_on cannot include itself")
                continue
            if dep not in by_id:
                findings.append(f"{slice_id}: depends_on names {dep!r}, which is not a slice id")
                continue
            dep_ids.append(dep)

        reads = item.get("reads") or []
        if isinstance(reads, list) and reads:
            read_producers = {producers[name] for name in reads if isinstance(name, str) and name in producers}
            if dep_ids and set(dep_ids) == read_producers:
                findings.append(
                    f"{slice_id}: depends_on {dep_ids} is exactly the producers of its reads — that is a "
                    "timeline fact, not a build dependency. Seed from synthetic events (Principle V) and "
                    "leave depends_on empty, or name a genuine code/contract dependency that is not only "
                    "those producers"
                )

    # Cycle detection on the depends_on DAG.
    graph = {sid: [] for sid in by_id}
    for sid, item in by_id.items():
        deps = item.get("depends_on") or []
        if isinstance(deps, list):
            graph[sid] = [d for d in deps if isinstance(d, str) and d in by_id and d != sid]

    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(node: str, stack: list[str]) -> None:
        if node in visiting:
            cycle_from = stack[stack.index(node) :] + [node]
            findings.append(
                f"{node}: depends_on cycle {' → '.join(cycle_from)}"
            )
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, []):
            walk(nxt, stack + [node])
        visiting.remove(node)
        visited.add(node)

    for sid in graph:
        walk(sid, [])

    return findings


def folds_match_their_guard(slices: list) -> list[str]:
    """What a decision folds must be what its append is guarded by.

    A second pass, because a Decider folds its *own* slice's events as well as earlier ones, so the
    producing frames are not all known while the first pass is still walking. Mirrors validate.ts's
    `folds-match-the-guard`.

    Only slices that draw their boundary out of tags are checked here: with `stream`, the guard is the
    stream and validate.ts's `folds-own-stream` is the same rule expressed against it. With `guard`, the
    boundary is a query over kinds, and a folded event the query cannot reach is a decision guarded
    against something it did not read — which the tests will not catch, because a Decider's unit test
    hand-feeds it events no append could have loaded under that guard.
    """
    findings: list[str] = []
    producing: dict[str, dict] = {}
    for item in slices:
        if not isinstance(item, dict):
            continue
        for frame in item.get("frames") or []:
            if not isinstance(frame, dict) or frame.get("type") != "evt":
                continue
            if frame.get("external") is True:
                continue
            name = frame.get("name")
            if isinstance(name, str) and name not in producing:
                producing[name] = frame

    for item in slices:
        if not isinstance(item, dict):
            continue
        guard = item.get("guard")
        by = guard.get("by") if isinstance(guard, dict) else None
        if not isinstance(by, list) or not by:
            continue
        slice_id = item.get("id", "?")
        for name in item.get("folds") or []:
            frame = producing.get(name) if isinstance(name, str) else None
            if frame is None:
                continue  # `folds-resolve` reports an event nothing produces.
            kinds = {
                attribute.get("identifies")
                for attribute in frame.get("attributes") or []
                if isinstance(attribute, dict) and attribute.get("identifies")
            }
            if not kinds & set(by):
                identified = ", ".join(sorted(str(kind) for kind in kinds)) or "nothing"
                findings.append(
                    f"{slice_id}: folds {name!r}, which identifies {identified} — none of the kinds this "
                    f"slice's boundary is drawn by ({', '.join(by)}). A conditional append is refused only "
                    "by events the query covers, so a decision folding this one is guarded against "
                    "something it did not read"
                )
    return findings


def main() -> int:
    model = load_yaml()
    findings = validate(model)
    if findings:
        print("Event model validation failed:", file=sys.stderr)
        print("\n".join(f"  - {finding}" for finding in findings), file=sys.stderr)
        return 1
    print("check-model: valid")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"check-model failed: {error}", file=sys.stderr)
        raise SystemExit(1)

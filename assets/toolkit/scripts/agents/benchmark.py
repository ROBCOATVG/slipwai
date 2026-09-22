#!/usr/bin/env python3
"""What each stage of `/drive`'s ladder cost a slice, and how well it did — recorded where the slice's other
artifacts are, so a project accumulates a history rather than a log that scrolls away.

One record per slice, `specs/<feature>/slices/<id>/benchmark.json`, and one per feature for the stages above the
slice loop, `specs/<feature>/benchmark.json`. `/drive` opens an entry before a stage and closes it after:

    python3 scripts/agents/benchmark.py start specs/shop/slices/S1 implement
    python3 scripts/agents/benchmark.py end   specs/shop/slices/S1 implement verify_failures=1
    python3 scripts/agents/benchmark.py close specs/shop/slices/S1        # the shape, once the slice is archived
    python3 scripts/agents/benchmark.py                                   # the aggregate; `make benchmark`
    python3 scripts/agents/benchmark.py overview [shop]                   # writes specs/<feature>/benchmark.md; `/benchmark`
    python3 scripts/agents/benchmark.py --json
    python3 scripts/agents/benchmark.py cut-off "<why>"                   # close what an iteration left open; the runner's
    python3 scripts/agents/benchmark.py check                             # the gate: nothing open, every done slice recorded

Everything that a transcript, `tasks.md`, git or the record itself can say is read from there, never asked:
wall time; the agent type each delegate ran as, where the transcript attributes one; tokens by model, from the
harness's own transcript between the two cursors — Claude Code's
`~/.claude/projects/<slug>/<session>.jsonl` and the sub-agent transcripts beside it, Codex's rollout under
`~/.codex/sessions/` — where `scripts/agents/registry.json` records one for the running harness, and `null`
with the reason where it does not; which model ran, from the same lines; the tasks `tasks.md` gained during a
converge pass; how many times converge ran; a stage re-entered after implementation; files and lines from
`git diff`. What nothing on disk can supply is passed to `end` as `key=value`: `gaps=N`, `findings=N`,
`seams=N`, `mutation_score=…` copied from the tool's line, `verify_failures=N`, `outcome=accepted|behaviour|implementation`,
`delegate=<boundary>` and `cycle=<unit>` for how an implement entry was delegated and driven with `split=N` for
how many groups its delegate fanned out into, and `model=` or `agent=` only where no transcript could say. A number that was not read is not written.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json` (see models.py)."""
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 2)
REGISTRY = Path(__file__).with_name("registry.json")
MODELS = Path(__file__).with_name("models.py")
INTEGRATION = ROOT / ".specify/integration.json"
RECORD = "benchmark.json"
OVERVIEW = "benchmark.md"
# The ladder, in order, plus the stages an adopted repository adds; a stage outside it is accepted and sorted last.
LADDER = (
    "ground", "principles", "specify", "event-model", "split", "example-map", "gaps", "release-constraint", "plan",
    "tasks", "pin", "implement", "converge", "demo", "adversary", "mutation", "skipper", "hand", "bosun",
)
OUTCOMES = ("accepted", "behaviour", "implementation")
# Converge passes beyond which the overview says something: one pass to find work and one to confirm it
# closed is the shape of a slice that converged, so the third is the first that is worth reading about.
REPEATED = 3
COUNTS = ("gaps", "findings", "seams", "verify_failures", "split")
WORDS = ("mutation_score", "outcome", "model", "agent", "note", "delegate", "cycle", "driver")
COMMENT = (
    "What each stage of /drive cost this slice and how well it did, one entry per stage run, appended by "
    "scripts/agents/benchmark.py at the stage's start and end. Tokens come from the harness's own transcript or are "
    "null with the reason; signals are what the stage reported. `make benchmark` reads every record. "
    "docs/agent-harnesses.md says what the numbers can and cannot be compared with."
)
USAGE_KEYS = ("input", "output", "cache_read", "cache_creation")
# Which stage a delegate type's lines belong to, whatever bracket was open when they were written: a skipper round
# opened while the implementers run must not count their tokens, and the implement entry must not lose them to it.
OWNERS = {"drive-implement": ("implement",), "drive-converge": ("converge",), "drive-gaps": ("gaps",),
          "drive-adversary": ("adversary",), "drive-mutation": ("mutation",), "drive-tasks": ("tasks",),
          "drive-hand": ("demo", "hand"), "drive-skipper": ("skipper",), "drive-bosun": ("bosun",)}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def moment(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def git(*arguments: str) -> str | None:
    result = subprocess.run(["git", *arguments], cwd=ROOT, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


# --- the record -------------------------------------------------------------------------------------------------

def load(directory: Path) -> dict[str, Any]:
    path = directory / RECORD
    if path.is_file():
        record: dict[str, Any] = json.loads(path.read_text())
        return record
    parts = directory.relative_to(ROOT).parts
    feature = parts[1] if len(parts) > 1 and parts[0] == "specs" else directory.name
    slice_ = parts[-1] if len(parts) > 3 and parts[-2] == "slices" else None
    return {"_comment": COMMENT, "feature": feature, "slice": slice_, "from": git("rev-parse", "HEAD"), "stages": []}


def save(directory: Path, record: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / RECORD).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")


def tasks_file(directory: Path) -> Path | None:
    """The slice's `tasks.md`: beside the record from the day it is planned — or, in a project from before the
    canonical slot became a link, still Spec Kit's under the feature while the work is on."""
    for candidate in (directory / "tasks.md", ROOT / "specs" / str(load(directory)["feature"]) / "tasks.md"):
        if candidate.is_file():
            return candidate
    return None


def task_counts(directory: Path) -> dict[str, int] | None:
    path = tasks_file(directory)
    if path is None:
        return None
    text = path.read_text()
    open_, done = len(re.findall(r"^\s*- \[ \]", text, re.M)), len(re.findall(r"^\s*- \[[xX]\]", text, re.M))
    return {"open": open_, "done": done}


def planned(stage: str) -> str | None:
    """The line `models.py` gives before the stage — what was meant to run it."""
    result = subprocess.run(["python3", str(MODELS), stage], cwd=ROOT, text=True, capture_output=True)
    return result.stdout.strip().splitlines()[-1] if result.returncode == 0 and result.stdout.strip() else None


# --- the transcripts ------------------------------------------------------------------------------------------

def installed() -> list[str]:
    if not INTEGRATION.is_file():
        return []
    state = json.loads(INTEGRATION.read_text())
    keys = state.get("installed_integrations")
    if isinstance(keys, list) and keys:
        return [key for key in keys if isinstance(key, str)]
    default = state.get("default_integration")
    return [default] if isinstance(default, str) else []


def registry() -> dict[str, dict[str, Any]]:
    return {entry["key"]: entry for entry in json.loads(REGISTRY.read_text())["harnesses"]}


def sizes(paths: list[Path]) -> dict[str, int]:
    return {str(path): path.stat().st_size for path in paths}


def claude_transcripts(session: str) -> tuple[Path | None, list[Path]]:
    projects = Path.home() / ".claude/projects"
    main = next(iter(sorted(projects.glob(f"*/{session}.jsonl"))), None)
    subagents = sorted(projects.glob(f"*/{session}/subagents/*.jsonl"))
    return main, subagents


def codex_rollout(thread: str) -> Path | None:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return next(iter(sorted(home.glob(f"sessions/*/*/*/rollout-*{thread}*.jsonl"))), None)


def cursor() -> dict[str, Any]:
    """Where the running harness's transcript stands now, or why it cannot be read — decided by what the harness
    put in the environment, which is the only way to name *this* session rather than the newest file."""
    table = registry()
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    thread = os.environ.get("CODEX_THREAD_ID")
    if session and isinstance(table.get("claude", {}).get("usage"), dict):
        main, subagents = claude_transcripts(session)
        if main is None:
            return {"source": None, "reason": f"Claude Code session {session} has no transcript under ~/.claude/projects"}
        return {"source": "claude", "session": session, "files": sizes([main]), "subagents": sizes(subagents)}
    if thread and isinstance(table.get("codex", {}).get("usage"), dict):
        rollout = codex_rollout(thread)
        if rollout is None:
            return {"source": None, "reason": f"Codex thread {thread} has no rollout under ~/.codex/sessions"}
        return {"source": "codex", "session": thread, "files": sizes([rollout]), "subagents": {},
                "total": codex_total(rollout, 0)}
    keys = installed()
    if not keys:
        return {"source": None, "reason": "no harness installed (`./init --integration <agent>`) and none in the environment"}
    named = ", ".join(table[key]["name"] if key in table else key for key in keys)
    if any(isinstance(table.get(key, {}).get("usage"), dict) for key in keys):
        return {"source": None, "reason": f"{named} is installed but did not name this session in the environment "
                                          "(CLAUDE_CODE_SESSION_ID, CODEX_THREAD_ID), so its transcript cannot be found"}
    return {"source": None, "reason": f"the registry records no transcript to read for {named}"}


def lines_with_offsets(path: Path, offset: int) -> list[tuple[int, dict[str, Any]]]:
    """Each JSON line after `offset` with the byte offset it starts at — the coordinate a bracket's window is in."""
    if not path.is_file():
        return []
    with path.open("rb") as handle:
        handle.seek(offset)
        raw = handle.read()
    items = []
    position = offset
    for line in raw.split(b"\n"):
        start, position = position, position + len(line) + 1
        try:
            item = json.loads(line.decode("utf-8", errors="replace"))
        except ValueError:
            continue
        if isinstance(item, dict):
            items.append((start, item))
    return items


def lines_after(path: Path, offset: int) -> list[dict[str, Any]]:
    return [item for _, item in lines_with_offsets(path, offset)]


class Window:
    """Where one bracket sits in the transcripts: a byte range per file, open-ended while the entry is. A line is
    counted by the innermost bracket covering it, except that a delegate's lines go to the bracket whose stage owns
    the type that ran them, so two brackets open at once — a skipper round during implementation — never both
    count the same request, and neither loses what is its own."""

    def __init__(self, stage: str, started: str, from_: dict[str, int], to: dict[str, int] | None) -> None:
        self.stage, self.started, self.from_, self.to = stage, started, from_, to
        # Which of two brackets started later: the clock, then — two starts in one second — where the transcripts
        # stood, which only ever grows.
        self.order = (started, sum(from_.values()))

    def later_than(self, other: "Window") -> bool:
        return self.order > other.order

    def covers(self, path: str, offset: int) -> bool:
        if offset < self.from_.get(path, 0):
            return False
        return self.to is None or offset < self.to.get(path, 0)

    def owns(self, agent: str | None) -> bool:
        return self.stage in OWNERS.get(agent or "", ())

    def counts(self, path: str, offset: int, agent: str | None, others: list["Window"]) -> bool:
        covering = [other for other in others if other.covers(path, offset)]
        if agent is not None and self.owns(agent) and not any(other.owns(agent) and other.later_than(self)
                                                                for other in covering):
            return True
        if any(other.owns(agent) for other in covering):
            return False
        return not any(other.later_than(self) for other in covering)


def window_of(entry: dict[str, Any]) -> Window | None:
    """An entry's window, from its closed `span` or, while it is open, its start cursor; none for an entry from
    before spans were recorded, which is not held against any other."""
    span = entry.get("span")
    if isinstance(span, dict):
        return Window(entry["stage"], entry.get("started", ""), dict(span.get("from", {})), dict(span.get("to", {})))
    mark = entry.get("cursor")
    if isinstance(mark, dict) and mark.get("source"):
        return Window(entry["stage"], entry.get("started", ""), {**mark.get("files", {}), **mark.get("subagents", {})},
                      None)
    return None


def other_windows(except_path: Path, except_index: int) -> list[Window]:
    """Every other bracket in the project's records, open or closed, that could overlap this one."""
    found = []
    for path, record in records():
        for index, entry in enumerate(record.get("stages", [])):
            if path == except_path and index == except_index:
                continue
            window = window_of(entry)
            if window is not None:
                found.append(window)
    return found


def empty_usage() -> dict[str, int]:
    return dict.fromkeys(USAGE_KEYS, 0)


def add_usage(into: dict[str, int], usage: dict[str, Any], mapping: dict[str, str]) -> None:
    for key, field in mapping.items():
        value = usage.get(field)
        if isinstance(value, int):
            into[key] += value


CLAUDE_FIELDS = {"input": "input_tokens", "output": "output_tokens", "cache_read": "cache_read_input_tokens",
                 "cache_creation": "cache_creation_input_tokens"}
CODEX_FIELDS = {"input": "input_tokens", "output": "output_tokens", "cache_read": "cached_input_tokens",
                "cache_creation": "cache_write_input_tokens"}


def claude_usage(items: list[dict[str, Any]], by_model: dict[str, dict[str, int]], seen: set[str],
                 agents: set[str] | None = None, keep: Callable[[int, str | None], bool] | None = None,
                 offsets: list[int] | None = None) -> None:
    """One API response is written as one line per content block, each carrying the same usage: count a
    request once (592 of 1090 assistant lines on this machine's transcripts were repeats).

    An assistant line in a sub-agent's transcript also names the *type* that ran it, in `attributionAgent` —
    `drive-adversary` where the stage delegated to a type, `general-purpose` where it delegated to nothing in
    particular. That is read rather than asked, the way the model is, so a record can only claim a type that
    actually ran (the transcripts Claude Code 2.1.268 wrote on this machine, read 2026-09-15).
    """
    for position, item in enumerate(items):
        if item.get("type") != "assistant":
            continue
        message = item.get("message") or {}
        usage = message.get("usage")
        key = item.get("requestId") or message.get("id") or item.get("uuid")
        if not isinstance(usage, dict) or not key or key in seen:
            continue
        agent = item.get("attributionAgent") if isinstance(item.get("attributionAgent"), str) else None
        if keep is not None and offsets is not None and not keep(offsets[position], agent):
            continue
        seen.add(str(key))
        if agents is not None and agent is not None:
            agents.add(agent)
        add_usage(by_model.setdefault(str(message.get("model") or "unknown"), empty_usage()), usage, CLAUDE_FIELDS)


def codex_total(path: Path, offset: int) -> dict[str, int] | None:
    """The cumulative usage the last `token_count` event after `offset` reports, for the delta an older rollout
    without `token_usage_record` lines still allows."""
    total = None
    for item in lines_after(path, offset):
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else item
        if item.get("type") == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info") or {}
            if isinstance(info.get("total_token_usage"), dict):
                total = empty_usage()
                add_usage(total, info["total_token_usage"], CODEX_FIELDS)
    return total


def codex_usage(path: Path, offset: int, start_total: dict[str, int] | None,
                keep: Callable[[int], bool] | None = None, shared: bool = False) -> tuple[dict[str, dict[str, int]], str]:
    by_model: dict[str, dict[str, int]] = {}
    seen: set[str] = set()
    model = "unknown"
    records_seen = False
    for position, item in lines_with_offsets(path, offset):
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else item
        if item.get("type") == "turn_context" and isinstance(payload.get("model"), str):
            model = payload["model"]
        if item.get("type") == "token_usage_record" and isinstance(payload.get("usage"), dict):
            key = str(payload.get("response_id") or len(seen))
            if key in seen:
                continue
            seen.add(key)
            records_seen = True
            if keep is not None and not keep(position):
                continue
            add_usage(by_model.setdefault(model, empty_usage()), payload["usage"], CODEX_FIELDS)
    if records_seen:
        return by_model, "token_usage_record lines, one per response"
    end_total = codex_total(path, offset)
    if start_total is None or end_total is None:
        return {}, "no token_count event either side of the stage"
    return ({model: {key: end_total[key] - start_total[key] for key in USAGE_KEYS}},
            "the difference between token_count totals"
            + (", which a bracket open at the same time shares" if shared else ""))


def span_now(mark: dict[str, Any]) -> dict[str, dict[str, int]]:
    """The window this bracket closes with: from its cursor to the transcripts' present ends."""
    from_ = {**mark.get("files", {}), **mark.get("subagents", {})}
    if mark.get("source") == "claude":
        main, subagents = claude_transcripts(mark["session"])
        to = sizes([path for path in [main, *subagents] if path is not None])
    elif mark.get("source") == "codex":
        rollout = codex_rollout(mark["session"])
        to = sizes([rollout]) if rollout is not None else {}
    else:
        to = {}
    return {"from": from_, "to": to}


def usage_since(mark: dict[str, Any], own: Window | None = None, others: list[Window] | None = None) -> dict[str, Any]:
    """Tokens by model between the cursor and now, split host/sub-agents, or why there are none. With the bracket's
    own window and every other bracket's, a line another bracket owns — one nested inside this one, or one whose
    stage owns the delegate type that wrote it — is left to that bracket."""
    if mark.get("source") is None:
        return {"source": None, "reason": mark.get("reason", "no transcript")}
    overlapping = [other for other in (others or []) if own is not None]
    if mark["source"] == "claude":
        if os.environ.get("CLAUDE_CODE_SESSION_ID") != mark["session"]:
            return {"source": None, "reason": f"the session changed since the stage started ({mark['session']})"}
        main, subagents = claude_transcripts(mark["session"])
        host: dict[str, dict[str, int]] = {}
        delegated: dict[str, dict[str, int]] = {}
        seen: set[str] = set()
        types: set[str] = set()
        shared = 0

        def reader(path: Path) -> Callable[[int, str | None], bool]:
            def keep(offset: int, agent: str | None) -> bool:
                nonlocal shared
                kept = own is None or own.counts(str(path), offset, agent, overlapping)
                shared += not kept
                return kept
            return keep

        for path in [main] if main else []:
            lines = lines_with_offsets(path, mark["files"].get(str(path), 0))
            claude_usage([item for _, item in lines], host, seen, keep=reader(path), offsets=[o for o, _ in lines])
        for path in subagents:
            lines = lines_with_offsets(path, mark["subagents"].get(str(path), 0))
            claude_usage([item for _, item in lines], delegated, seen, types, keep=reader(path),
                         offsets=[o for o, _ in lines])
        read = "message.usage on each assistant line, once per requestId"
        if shared:
            read += f"; {shared} request(s) left to a bracket open at the same time"
        return {"source": "claude", "session": mark["session"], "read": read, "host": host, "subagents": delegated,
                "agents": sorted(types)}
    if os.environ.get("CODEX_THREAD_ID") != mark["session"]:
        return {"source": None, "reason": f"the thread changed since the stage started ({mark['session']})"}
    rollout = codex_rollout(mark["session"])
    if rollout is None:
        return {"source": None, "reason": "the rollout disappeared"}
    keep_codex = (lambda offset: own.counts(str(rollout), offset, None, overlapping)) if own is not None else None
    shared = any(other.covers(str(rollout), mark["files"].get(str(rollout), 0)) or other.later_than(own)
                 for other in overlapping) if own is not None else False
    by_model, how = codex_usage(rollout, mark["files"].get(str(rollout), 0), mark.get("total"), keep_codex, shared)
    return {"source": "codex", "session": mark["session"], "read": how, "host": by_model, "subagents": {}}


def models_that_ran(usage: dict[str, Any]) -> list[str]:
    return sorted({model for part in ("host", "subagents") for model, tokens in (usage.get(part) or {}).items()
                   if any(tokens.values())})


def types_that_ran(usage: dict[str, Any]) -> list[str]:
    """The agent types the transcript attributed this stage's delegates to, where the harness records them."""
    named = usage.get("agents")
    return sorted(name for name in named if isinstance(name, str)) if isinstance(named, list) else []


# --- the commands ----------------------------------------------------------------------------------------------

def parse_signals(arguments: list[str]) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    for argument in arguments:
        key, separator, value = argument.partition("=")
        if not separator or not value:
            raise RuntimeError(f"a signal is key=value, not {argument!r}; known: {', '.join(COUNTS + WORDS)}")
        if key in COUNTS:
            if not value.isdigit():
                raise RuntimeError(f"{key} takes a count, not {value!r}")
            signals[key] = int(value)
        elif key == "outcome":
            if value not in OUTCOMES:
                raise RuntimeError(f"outcome is one of {', '.join(OUTCOMES)}, not {value!r}")
            signals[key] = value
        elif key in WORDS:
            signals[key] = value
        else:
            raise RuntimeError(f"`{key}` is not a signal; known: {', '.join(COUNTS + WORDS)}")
    return signals


def start(directory: Path, stage: str) -> None:
    record = load(directory)
    left_open = [entry["stage"] for entry in record["stages"] if "ended" not in entry]
    mark = cursor()
    record["stages"].append({"stage": stage, "started": now(), "planned": planned(stage),
                             "tasks": {"start": task_counts(directory)}, "cursor": mark})
    save(directory, record)
    where = f"usage from {mark['source']}" if mark.get("source") else f"no usage: {mark.get('reason')}"
    note = f"; left open: {', '.join(left_open)}" if left_open else ""
    print(f"benchmark: {stage} started ({(directory / RECORD).relative_to(ROOT)}; {where}{note})")


def end(directory: Path, stage: str, arguments: list[str], clock: Callable[[], str] = now) -> None:
    """Close the open entry for `stage`. `clock` is a seam, not a setting: it is how a test can put the
    start and the end in the same moment on purpose, without a mocking framework replacing this module."""
    record = load(directory)
    signals = parse_signals(arguments)
    index = next((index for index in range(len(record["stages"]) - 1, -1, -1)
                  if record["stages"][index]["stage"] == stage and "ended" not in record["stages"][index]), None)
    if index is None:
        raise RuntimeError(f"no open `{stage}` entry in {(directory / RECORD).relative_to(ROOT)}; `start` it first")
    entry = record["stages"][index]
    entry["ended"] = clock()
    entry["seconds"] = int((moment(entry["ended"]) - moment(entry["started"])).total_seconds())
    mark = entry.pop("cursor", {"source": None, "reason": "no cursor was recorded"})
    own = None
    if mark.get("source"):
        entry["span"] = span_now(mark)
        own = Window(stage, entry["started"], entry["span"]["from"], entry["span"]["to"])
    usage = usage_since(mark, own, other_windows(directory / RECORD, index))
    entry["usage"] = usage
    ran = models_that_ran(usage)
    entry["ran"] = ran or ([signals["model"]] if "model" in signals else None)
    types = types_that_ran(usage)
    entry["agents"] = types or ([signals["agent"]] if "agent" in signals else None)
    entry["delegated"] = any(any(tokens.values()) for tokens in (usage.get("subagents") or {}).values())
    entry["tasks"]["end"] = task_counts(directory)
    entry["signals"] = signals
    save(directory, record)
    if is_unbracketed(entry):
        print(
            f"benchmark: warning: {stage} was not bracketed around its work — start and end were called "
            "in the same moment",
            file=sys.stderr,
        )
    print(f"benchmark: {summary_line(entry)}")


def summary_line(entry: dict[str, Any]) -> str:
    usage = entry.get("usage") or {}
    if is_unbracketed(entry):
        tokens = "tokens unknown — stage was not bracketed around its work"
    elif usage.get("source"):
        total = totals(entry)
        tokens = f"in {compact(total['input'] + total['cache_read'] + total['cache_creation'])} · out {compact(total['output'])}"
    else:
        tokens = f"tokens unknown — {usage.get('reason')}"
    ran = ", ".join(entry.get("ran") or []) or ("no transcript lines since start" if usage.get("source") else "model unknown")
    types = ", ".join(entry.get("agents") or [])
    delegated = f", delegated to {types}" if types else ", delegated" if entry.get("delegated") else ""
    return f"{entry['stage']}: {stage_wall(entry)} · {tokens} · {ran}{delegated}"


def close(directory: Path) -> None:
    record = load(directory)
    start_sha = record.get("from")
    shape: dict[str, Any] = {"tasks": None, "files": None, "added": None, "removed": None, "from": start_sha,
                             "to": git("rev-parse", "HEAD")}
    counts = task_counts(directory)
    if counts is not None:
        shape["tasks"] = counts["open"] + counts["done"]
    stat = git("diff", "--shortstat", start_sha) if start_sha else None
    if stat is not None:
        files = re.search(r"(\d+) files? changed", stat)
        added = re.search(r"(\d+) insertions?", stat)
        removed = re.search(r"(\d+) deletions?", stat)
        shape.update(files=int(files.group(1)) if files else 0, added=int(added.group(1)) if added else 0,
                     removed=int(removed.group(1)) if removed else 0)
        # `git diff` never sees a file nobody has added yet; the slice's own new files are part of its shape.
        for untracked in (git("ls-files", "--others", "--exclude-standard") or "").splitlines():
            path = ROOT / untracked
            if path.is_file() and path.name != RECORD:
                shape["files"] += 1
                shape["added"] += len(path.read_text(errors="replace").splitlines())
    record["shape"] = shape
    save(directory, record)
    print(f"benchmark: {record['slice'] or record['feature']} closed — {shape['tasks']} tasks, {shape['files']} files, "
          f"+{shape['added']}/-{shape['removed']}")
    for page in overview(str(record["feature"])):
        print(f"benchmark: {page.relative_to(ROOT)} redrawn")
    print()
    print(aggregate())


def cut_off(reason: str) -> None:
    """Close every entry still open in any record, with the reason and no usage: the session that opened it is
    gone — the runner's iteration ended, or was ended — so nothing will `end` it, and an entry left open reads
    as a stage still running. Its wall is real; its tokens and signals were never recorded, and the record says
    so rather than guessing. The window is still kept, so a bracket that enclosed it leaves it its lines."""
    for path, record in records():
        changed = False
        for entry in record.get("stages", []):
            if "ended" in entry:
                continue
            entry["ended"] = now()
            entry["seconds"] = int((moment(entry["ended"]) - moment(entry["started"])).total_seconds())
            mark = entry.pop("cursor", {"source": None})
            if mark.get("source"):
                entry["span"] = span_now(mark)
            entry["usage"] = {"source": None, "reason": f"cut off — {reason}"}
            entry.update(ran=None, agents=None, delegated=False, signals={}, cut_off=reason)
            entry.setdefault("tasks", {})["end"] = task_counts(path.parent)
            changed = True
            print(f"benchmark: {record.get('slice') or '(feature)'} {entry['stage']}: cut off — {reason}")
        if changed:
            save(path.parent, record)


def done_slices(feature: Path) -> set[str]:
    """The slices this feature has finished, as the ladder marks them: a row in the register at
    `slices/README.md`, or `status: implemented` in the event model (`commands/drive.md`, *Ready-set selection*)."""
    done: set[str] = set()
    register = feature / "slices/README.md"
    if register.is_file():
        for line in register.read_text().splitlines():
            if not line.strip().startswith("|"):
                continue
            first = line.strip().strip("|").split("|")[0].strip().strip("`")
            found = re.match(r"([A-Za-z]+\d+)\b", first)
            if found:
                done.add(found.group(1))
    model = ROOT / "docs/event-model/model.yaml"
    if model.is_file():
        for block in re.split(r"^\s*- id:\s*", model.read_text(), flags=re.M)[1:]:
            ident = block.split("\n", 1)[0].strip().strip("'\"")
            if ident and re.search(r"^\s*status:\s*implemented\s*$", block, re.M):
                done.add(ident)
    return done


def check() -> list[str]:
    """What the gate holds: no entry left open, a record for every slice the ladder calls done, that record
    closed, and a feature record once any slice is done — because a delivered slice with no benchmark cannot say
    what it cost, and the brackets can only be taken at the time."""
    findings = []
    for path, record in records():
        for entry in record.get("stages", []):
            if "ended" not in entry:
                findings.append(f"{path.relative_to(ROOT)}: `{entry['stage']}` has been open since {entry['started']} — "
                                "`benchmark.py end` closes it, and the runner cuts an entry off when its iteration ends")
    specs = ROOT / "specs"
    for feature in sorted(specs.iterdir()) if specs.is_dir() else []:
        if not (feature / "slices").is_dir():
            continue
        done = done_slices(feature)
        for ident in sorted(done):
            record_path = feature / "slices" / ident / RECORD
            where = f"specs/{feature.name}/slices/{ident}"
            if not record_path.is_file():
                findings.append(f"{where} is done but has no {RECORD}: no stage of it was bracketed "
                                "(commands/drive.md, *What each stage costs*)")
            elif "shape" not in json.loads(record_path.read_text()):
                findings.append(f"{where} is done but its record was never closed — "
                                f"`python3 scripts/agents/benchmark.py close {where}`")
        if done and not (feature / RECORD).is_file():
            findings.append(f"specs/{feature.name}/{RECORD} is missing while {len(done)} slice(s) are done: the stages "
                            "above the slice loop were not bracketed")
    return findings


# --- the aggregate ---------------------------------------------------------------------------------------------

def totals(entry: dict[str, Any]) -> dict[str, int]:
    total = empty_usage()
    for part in ("host", "subagents"):
        for tokens in (entry.get("usage") or {}).get(part, {}).values():
            for key in USAGE_KEYS:
                total[key] += tokens.get(key, 0)
    return total


def compact(number: int) -> str:
    for limit, suffix in ((10 ** 9, "G"), (10 ** 6, "M"), (10 ** 3, "k")):
        if number >= limit:
            return f"{number / limit:.1f}{suffix}".replace(".0", "")
    return str(number)


def wall(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}h{minutes:02d}m" if hours else f"{minutes}m{secs:02d}s" if minutes else f"{secs}s"


def is_unbracketed(entry: dict[str, Any]) -> bool:
    """A same-moment start and end did not surround the work; derive this so old records improve too."""
    return "ended" in entry and entry.get("seconds") == 0


def stage_wall(entry: dict[str, Any]) -> str:
    if "ended" not in entry:
        return "open"
    return "unbracketed" if is_unbracketed(entry) else wall(entry.get("seconds", 0))


def summary_wall(summary: dict[str, Any]) -> str:
    measured = wall(summary["seconds"])
    return f"{measured}+" if summary.get("unbracketed") else measured


def order(stage: str) -> int:
    return LADDER.index(stage) if stage in LADDER else len(LADDER)


def usage_unread(entry: dict[str, Any]) -> bool:
    """Whether this ended stage contributes no attributable tokens to the aggregate.

    Unbracketed (same-moment start/end) and missing harness source are unread. So is a bracketed
    stage whose harness answered but recorded no model running — that is "no transcript lines
    since start", and counting it as known zero made the unread total depend on whether the clock
    ticked between start and end.
    """
    if is_unbracketed(entry):
        return True
    usage = entry.get("usage") or {}
    if not usage.get("source"):
        return True
    return not (entry.get("ran") or [])


def summarise(record: dict[str, Any]) -> dict[str, Any]:
    """One row's worth of a record: what the entries add up to, and what they show by their sequence."""
    stages = record.get("stages", [])
    ended = [entry for entry in stages if "ended" in entry]
    total = empty_usage()
    for entry in ended:
        if is_unbracketed(entry):
            continue
        for key in USAGE_KEYS:
            total[key] += totals(entry)[key]
    unknown = sum(1 for entry in ended if usage_unread(entry))
    converge = [entry for entry in ended if entry["stage"] == "converge"]
    appended = sum(
        sum(entry["tasks"]["end"].values()) - sum(entry["tasks"]["start"].values())
        for entry in converge if entry.get("tasks", {}).get("start") and entry.get("tasks", {}).get("end")
    )
    # The record is append-only, so its order is the order things happened — finer than the timestamps.
    first_converged = next((index for index, entry in enumerate(ended) if entry["stage"] == "converge"), len(ended))
    gaps_before = sum(entry["signals"].get("gaps", 0) for index, entry in enumerate(ended)
                      if entry["stage"] == "gaps" and index < first_converged)
    gaps_after = sum(entry["signals"].get("gaps", 0) for index, entry in enumerate(ended)
                     if entry["stage"] == "gaps" and index > first_converged)
    first_implemented = next((index for index, entry in enumerate(ended) if entry["stage"] == "implement"), len(ended))
    # The post-converge `/gaps` pass is the ladder, not rework; a stage above it, re-entered, is.
    rework = [entry["stage"] for index, entry in enumerate(ended)
              if index > first_implemented and order(entry["stage"]) < order("gaps")]
    last = {key: next((entry["signals"][key] for entry in reversed(ended) if key in entry.get("signals", {})), None)
            for key in ("mutation_score", "outcome")}
    return {
        "feature": record.get("feature"), "slice": record.get("slice"),
        "stages": [entry["stage"] for entry in stages], "open": [entry["stage"] for entry in stages if "ended" not in entry],
        "seconds": sum(entry.get("seconds", 0) for entry in ended),
        "unbracketed": any(is_unbracketed(entry) for entry in ended),
        "tokens": total, "usage_unknown": unknown,
        "models": sorted({model for entry in ended for model in (entry.get("ran") or [])}),
        "sessions": len({
            (usage.get("source"), usage.get("session"))
            for entry in ended
            if (usage := entry.get("usage") or {}).get("source") and usage.get("session")
        }),
        "converge_passes": len(converge), "tasks_appended": appended, "gaps": {"before": gaps_before, "after": gaps_after},
        "mutation_score": last["mutation_score"], "outcome": last["outcome"],
        "findings": sum(entry["signals"].get("findings", 0) for entry in ended),
        "seams": sum(entry["signals"].get("seams", 0) for entry in ended),
        "verify_failures": sum(entry["signals"].get("verify_failures", 0) for entry in ended),
        # How each implement entry was delegated and driven, `delegate/cycle`: one shape is a comparable slice,
        # two is a slice that ran as both and compares with neither (`commands/drive.md`, *How implementation
        # is delegated*).
        "delegation": sorted({
            f"{entry['signals'].get('delegate', '?')}/{entry['signals'].get('cycle', '?')}"
            for entry in ended if {"delegate", "cycle"} & set(entry.get("signals", {}))
        }),
        "split": sum(entry["signals"].get("split", 0) for entry in ended),
        "rework": rework, "shape": record.get("shape"),
    }


def records() -> list[tuple[Path, dict[str, Any]]]:
    specs = ROOT / "specs"
    return [(path, json.loads(path.read_text())) for path in sorted(specs.rglob(RECORD))] if specs.is_dir() else []


COLUMNS = ("slice", "delegate/cycle", "wall", "in", "out", "models", "sessions", "converge", "+tasks", "gaps", "mutation",
           "adversary", "demo", "verify✗", "rework", "tasks", "files", "±lines")


def row(summary: dict[str, Any]) -> list[str]:
    tokens = summary["tokens"]
    shape = summary.get("shape") or {}
    unknown = f" (+{summary['usage_unknown']} unread)" if summary["usage_unknown"] else ""
    return [
        summary["slice"] or "(feature)", ", ".join(summary["delegation"]) or "—", summary_wall(summary),
        compact(tokens["input"] + tokens["cache_read"] + tokens["cache_creation"]) + unknown, compact(tokens["output"]),
        ", ".join(summary["models"]) or "—", str(summary["sessions"]) or "—",
        str(summary["converge_passes"]), str(summary["tasks_appended"]),
        f"{summary['gaps']['before']}/{summary['gaps']['after']}", summary["mutation_score"] or "—",
        str(summary["findings"]), summary["outcome"] or "—", str(summary["verify_failures"]),
        str(len(summary["rework"])), str(shape.get("tasks", "—")), str(shape.get("files", "—")),
        f"+{shape['added']}/-{shape['removed']}" if shape.get("added") is not None else "—",
    ]


def table(rows: list[list[str]]) -> str:
    widths = [max(len(line[index]) for line in [list(COLUMNS), *rows]) for index in range(len(COLUMNS))]
    return "\n".join("  " + "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(line))
                     for line in [list(COLUMNS), *rows])


LEGEND = ("delegate/cycle = how implementation was delegated and driven; in = input + cache read + cache creation tokens; gaps = before/after converge; +tasks = tasks converge "
          "appended; sessions = harness sessions read; a stage's tokens are a floor (the turn that ends it is partly "
          "uncounted); a trailing + makes wall a floor because an unbracketed stage is missing; tokens are not prices")
READING = """These numbers compare the slices of this project on this harness, and one slice before and after a change
to a prompt, a skill or the layout. They are tokens, not prices. They do not compare harnesses, whose transcripts
count different things, or projects, whose slices are not the same size — the shape columns normalise, they do not
equate. A stage's tokens are a floor: the turn that closes the entry is still being written when it is read. A
number the script could not read is written as unknown with its reason, never estimated. A stage whose start and end
were called in the same moment is unbracketed: its wall and tokens are missing, not zero, and a slice containing one
shows its measured wall as a floor with a trailing `+`. Host context grows through a session, so otherwise identical
slices spanning different numbers or lengths of sessions are not directly comparable on host tokens."""


def by_feature() -> dict[str, list[tuple[Path, dict[str, Any]]]]:
    grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, record in records():
        grouped.setdefault(str(record.get("feature")), []).append((path, record))
    return grouped


def notes(summaries: list[dict[str, Any]], records_: list[dict[str, Any]]) -> list[str]:
    lines = [f"{summary['slice'] or '(feature)'}: still open — {', '.join(summary['open'])}"
             for summary in summaries if summary["open"]]
    # Converge is append-only and safe to repeat, so a high count is never a failure — but it is the cheapest
    # signal there is that a slice was too large, or that each pass closed the instance a finding was found at
    # and left its siblings for the next one (`commands/drive.md`, *Convergence*). The column already carries
    # the number; this says out loud when it is worth a look, since nothing else in the table interprets it.
    lines += [f"{summary['slice']}: converge ran {summary['converge_passes']} times, appending "
              f"{summary['tasks_appended']} task(s) — a slice too large, or fixes too narrow to close the "
              "class of what they found"
              for summary in summaries if summary["slice"] and summary["converge_passes"] >= REPEATED]
    lines += [f"{summary['slice']}: re-entered {', '.join(summary['rework'])} after implementation"
              for summary in summaries if summary["slice"] and summary["rework"]]
    lines += [f"{summary['slice']}: implemented as {' and '.join(summary['delegation'])} — its wall compares with "
              "neither" for summary in summaries if summary["slice"] and len(summary["delegation"]) > 1]
    for record in records_:
        for entry in record.get("stages", []):
            usage = entry.get("usage")
            if "ended" in entry and usage is not None and not usage.get("source"):
                lines.append(f"{record.get('slice') or '(feature)'} {entry['stage']}: tokens unknown — {usage.get('reason')}")
            if entry.get("cut_off"):
                lines.append(f"{record.get('slice') or '(feature)'} {entry['stage']}: cut off — {entry['cut_off']}; "
                             "its wall is real, its tokens and signals were never recorded")
            if is_unbracketed(entry):
                lines.append(
                    f"{record.get('slice') or '(feature)'} {entry['stage']}: not bracketed around its work — "
                    "start and end were called in the same moment, so this stage's wall and tokens are missing, not zero."
                )
    return lines


def aggregate() -> str:
    grouped = by_feature()
    if not grouped:
        return "benchmark: no record yet — /drive writes specs/<feature>/slices/<id>/benchmark.json from its next stage"
    blocks = []
    for feature, entries in grouped.items():
        summaries = [summarise(record) for _, record in entries]
        slices = [summary for summary in summaries if summary["slice"]]
        total = {"seconds": sum(s["seconds"] for s in summaries),
                 "unbracketed": any(s["unbracketed"] for s in summaries)}
        head = f"{feature} — {len(slices)} slice(s) recorded, {summary_wall(total)} in all"
        blocks.append("\n".join([head, table([row(summary) for summary in summaries]),
                                 *(f"  {line}" for line in notes(summaries, [record for _, record in entries]))]))
    return "\n\n".join(blocks) + f"\n\n{LEGEND}"


def markdown(rows: list[list[str]], columns: tuple[str, ...]) -> str:
    cell = lambda text: text.replace("|", "\\|")  # noqa: E731
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(cell(value) for value in line) + " |" for line in rows]
    return "\n".join(lines)


def stage_rows(record: dict[str, Any]) -> list[list[str]]:
    rows = []
    for entry in record.get("stages", []):
        total = totals(entry)
        usage = entry.get("usage") or {}
        reported = ", ".join(f"{key}={value}" for key, value in (entry.get("signals") or {}).items()) or "—"
        rows.append([
            entry["stage"], entry.get("started", "")[:16].replace("T", " "),
            stage_wall(entry),
            compact(total["input"] + total["cache_read"] + total["cache_creation"])
            if usage.get("source") and not is_unbracketed(entry) else "unknown",
            compact(total["output"]) if usage.get("source") and not is_unbracketed(entry) else "unknown",
            ", ".join(entry.get("ran") or []) or "—", ", ".join(entry.get("agents") or []) or "—",
            "yes" if entry.get("delegated") else "no", reported,
        ])
    return rows


STAGE_COLUMNS = ("stage", "started (UTC)", "wall", "in", "out", "model", "agent", "delegated", "reported")


def overview(feature: str | None = None) -> list[Path]:
    """`specs/<feature>/benchmark.md`, redrawn from the records: the table, every stage of every slice, the notes,
    and how to read it. A page, not a source — the records are; it is written whole each time and never edited."""
    grouped = by_feature()
    if feature is not None:
        if feature not in grouped:
            raise RuntimeError(f"no record under specs/{feature}/; known: {', '.join(grouped) or 'none'}")
        grouped = {feature: grouped[feature]}
    pages = []
    for name, entries in grouped.items():
        records_ = [record for _, record in entries]
        summaries = [summarise(record) for record in records_]
        slices = [summary for summary in summaries if summary["slice"]]
        parts = [
            f"# Benchmark — {name}",
            f"Drawn {now()} at `{(git('rev-parse', '--short', 'HEAD') or 'no commit')}` from {len(entries)} record(s) "
            f"under `specs/{name}/` by `scripts/agents/benchmark.py overview`; `/benchmark` redraws it, and so does closing "
            f"a slice. Regenerated whole, never edited: the records beside each slice are the source.",
            f"## Slices\n\n{len(slices)} slice(s) recorded, "
            f"{summary_wall({'seconds': sum(s['seconds'] for s in summaries), 'unbracketed': any(s['unbracketed'] for s in summaries)})} "
            "in all.\n\n"
            + markdown([row(summary) for summary in summaries], COLUMNS) + f"\n\n{LEGEND}.",
            "## Stages\n\n" + "\n\n".join(
                f"### {record.get('slice') or 'The feature, above the slice loop'} — {summary_wall(summary)}\n\n"
                + markdown(stage_rows(record), STAGE_COLUMNS)
                for record, summary in zip(records_, summaries, strict=True)
            ),
        ]
        found = notes(summaries, records_)
        parts.append("## Notes\n\n" + ("\n".join(f"- {line}" for line in found) if found else "Nothing open, no rework, "
                                                                                          "every stage's tokens read."))
        parts.append(f"## Reading these numbers\n\n{READING}")
        page = ROOT / "specs" / name / OVERVIEW
        page.write_text("\n\n".join(parts) + "\n")
        pages.append(page)
    return pages


def main() -> None:
    arguments = sys.argv[1:]
    if not arguments or arguments == ["--json"]:
        if arguments:
            print(json.dumps([{"path": str(path.relative_to(ROOT)), **summarise(record)} for path, record in records()],
                             indent=2, ensure_ascii=False))
        else:
            print(aggregate())
        return
    command, *rest = arguments
    if command == "overview":
        for page in overview(rest[0] if rest else None):
            print(f"benchmark: {page.relative_to(ROOT)} written")
        return
    if command == "cut-off":
        if not rest:
            raise RuntimeError("cut-off takes the reason, in words")
        cut_off(" ".join(rest))
        return
    if command == "check":
        findings = check()
        if findings:
            print("\n".join(f"check-benchmark: {finding}" for finding in findings), file=sys.stderr)
            raise SystemExit(1)
        held = records()
        print(f"check-benchmark: {len(held)} record(s), nothing open, every done slice recorded and closed"
              if held else "check-benchmark: no record and no done slice yet — nothing to hold")
        return
    if command not in ("start", "end", "close") or not rest:
        raise RuntimeError("usage: benchmark.py start|end <dir> <stage> [key=value ...] | close <dir> | overview "
                           "[feature] | cut-off <why> | check | [--json]")
    directory = (ROOT / rest[0]).resolve()
    if ROOT not in directory.parents:
        raise RuntimeError(f"{rest[0]} is outside the repository")
    if command == "close":
        close(directory)
        return
    if len(rest) < 2:
        raise RuntimeError(f"{command} takes <dir> <stage>")
    if command == "start":
        if rest[2:]:
            raise RuntimeError("start takes no signals; pass them to end")
        start(directory, rest[1])
    else:
        end(directory, rest[1], rest[2:])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"benchmark: {error}", file=sys.stderr)
        raise SystemExit(1) from None

"""What the harbour has spent, in thousands of work tokens, read from where the spending is recorded.

The board's *Tokens today* and the harbourmaster's bunker both summed a `tokens` field on deck-log lines, and
no line ever carried one, so the tile read 0 all day while three slices worked. What is recorded is each
stage's usage, in its slice's `benchmark.json` (`benchmark.py`), read from the harness's own transcripts:
on trunk for a merged slice, and in the slice's berth while it works. This reads those.

**Work tokens** are uncached input plus output, the unit `bunker_per_day` is set in (`telegraph.py`). They are
not the context re-read on every turn, which would spend a day's bunker in an hour of nothing.

A stage is counted once, by the slice, the stage and when it started, wherever its record is found: a berth
merged to trunk carries the same entries as the berth. A stage counts on the day it **ended**, because that
is when its tokens were read.

**One number is a pace, not a cost.** Work tokens are what the bunker paces the fleet by, and they move when
the agents do something. They are not what a day costs: the context re-read from cache every turn is tens of
millions of tokens a day, priced lower than input but not at nothing, and a token of one model is not priced
as one of another. So the board also shows the day by model and kind (`by_model`), and an estimate in money
where `harbour.json` says what each model costs (`cost`). No prices are shipped: they change, and they are an
account's own.

Standard library only: `make shared` carries this module into every project, where the harbourmaster reads it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: Where a slice's record lies, under a checkout.
RECORDS = "specs/*/slices/*/benchmark.json"
USAGE_KEYS = ("input", "output", "cache_read", "cache_creation")


def work(entry: dict[str, Any]) -> int:
    """One stage's work tokens: uncached input plus output, host and sub-agents together. A Codex record
    written before `benchmark.py` normalised the read still carries its cache reads inside `input`."""
    usage = mapping(entry.get("usage"))
    legacy_codex = usage.get("source") == "codex" and usage.get("counts") != "uncached"
    total = 0
    for part in ("host", "subagents"):
        for tokens in mapping(usage.get(part)).values():
            if not isinstance(tokens, dict):
                continue
            uncached = number(tokens.get("input"))
            if legacy_codex:
                uncached -= min(uncached, number(tokens.get("cache_read")))
            total += uncached + number(tokens.get("output"))
    return total


def mapping(value: object) -> dict[str, Any]:
    """A record's part where it is one, and an empty one where a file said something else."""
    return value if isinstance(value, dict) else {}


def number(value: object) -> int:
    return int(value) if isinstance(value, int | float) and not isinstance(value, bool) else 0


def checkouts(root: Path) -> list[Path]:
    """The project's checkout and every berth git knows of, the project's own first. Read from the files git
    keeps for each worktree (`<common dir>/worktrees/<name>/gitdir`, the path of that worktree's `.git`), not by
    running `git worktree list`: the board folds this on every poll, and a process started each time made the
    fold slow enough to lose its kept read to a person's action landing in between."""
    found = [Path(root)]
    common = common_dir(Path(root))
    # Asked from a berth: the main checkout is the folder that holds the shared `.git`, listed by no file.
    if common is not None and common.name == ".git" and common.parent.resolve() != Path(root).resolve():
        found.append(common.parent)
    listed = sorted((common / "worktrees").iterdir()) if common is not None and (common / "worktrees").is_dir() else []
    for one in listed:
        try:
            pointer = Path((one / "gitdir").read_text(encoding="utf-8").strip())
        except (OSError, UnicodeDecodeError):
            continue
        path = pointer.parent if pointer.name == ".git" else pointer
        if path.is_dir() and path.resolve() != Path(root).resolve() and path not in found:
            found.append(path)
    return found


def common_dir(root: Path) -> Path | None:
    """The repository's own folder: `.git` where it is one, or what a worktree's `.git` file points back to."""
    dot = root / ".git"
    if dot.is_dir():
        return dot
    try:
        said = dot.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not said.startswith("gitdir:"):
        return None
    own = Path(said[len("gitdir:"):].strip())
    own = own if own.is_absolute() else root / own
    try:
        back = (own / "commondir").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return own
    shared = Path(back)
    return (shared if shared.is_absolute() else own / shared).resolve()


#: Each benchmark record as last read, against its size and when it was written: the board asks for every
#: record three times a request, and on manda that was some 24,000 opens of files that had not changed.
#: Standard library only, as everything in this module is: a project carries it with no slipwai to import.
_RECORDS: dict[str, tuple[int, int, Any]] = {}


def _record(path: Path) -> Any:
    """One record's JSON, read again only where the file has changed since it was last read."""
    stat = path.stat()
    held = _RECORDS.get(str(path))
    if held and held[0] == stat.st_mtime_ns and held[1] == stat.st_size:
        return held[2]
    found = json.loads(path.read_text(encoding="utf-8"))
    if len(_RECORDS) > 50_000:
        _RECORDS.clear()
    _RECORDS[str(path)] = (stat.st_mtime_ns, stat.st_size, found)
    return found


def stages(root: Path) -> list[tuple[str, dict[str, Any]]]:
    """Every ended stage the project's records hold, each once: (`ended`, the entry)."""
    seen: set[tuple[str, str, str, str]] = set()
    found: list[tuple[str, dict[str, Any]]] = []
    for checkout in checkouts(root):
        for path in sorted(checkout.glob(RECORDS)):
            try:
                record = _record(path)
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            entries = record.get("stages") if isinstance(record, dict) else None
            for entry in entries if isinstance(entries, list) else []:
                if not isinstance(entry, dict) or not isinstance(entry.get("ended"), str):
                    continue
                key = (str(record.get("feature", "")), str(record.get("slice", path.parent.name)),
                       str(entry.get("stage", "")), str(entry.get("started", "")))
                if key not in seen:
                    seen.add(key)
                    found.append((entry["ended"], entry))
    return found


def spent(root: Path, day: str = "") -> int | None:
    """Thousands of work tokens the project's stages spent — those that ended on `day` (`YYYY-MM-DD`, UTC),
    where given — or None where no record of any stage exists."""
    ended = stages(root)
    if not ended:
        return None
    return sum(work(entry) for when, entry in ended if when.startswith(day)) // 1000


def by_model(root: Path, day: str = "") -> dict[str, dict[str, int]]:
    """Each model's tokens, by kind, over the stages that ended on `day`: input meaning uncached input."""
    totals: dict[str, dict[str, int]] = {}
    for when, entry in stages(root):
        if not when.startswith(day):
            continue
        usage = mapping(entry.get("usage"))
        legacy_codex = usage.get("source") == "codex" and usage.get("counts") != "uncached"
        for part in ("host", "subagents"):
            for model, tokens in mapping(usage.get(part)).items():
                if not isinstance(tokens, dict) or str(model).startswith("<"):
                    continue  # `<synthetic>`: a harness's own placeholder, which no model ran
                held = totals.setdefault(str(model), dict.fromkeys(USAGE_KEYS, 0))
                for key in USAGE_KEYS:
                    held[key] += number(tokens.get(key))
                if legacy_codex:
                    held["input"] -= min(number(tokens.get("input")), number(tokens.get("cache_read")))
    return {model: kinds for model, kinds in totals.items() if any(kinds.values())}


def cost(models: dict[str, dict[str, int]], prices: object) -> tuple[float | None, list[str]]:
    """What those tokens cost, from `prices` — `harbour.json`'s `prices`, per model the price of a million
    tokens of each kind — and the models it has no price for. None where any model that ran has no price: an
    estimate that left out what it could not price would read as the whole of it."""
    table = prices if isinstance(prices, dict) else {}
    total, unpriced = 0.0, []
    for model, kinds in sorted(models.items()):
        row = table.get(model)
        if not isinstance(row, dict) or not all(isinstance(row.get(key), int | float) for key in USAGE_KEYS):
            unpriced.append(model)
            continue
        total += sum(kinds[key] * float(row[key]) for key in USAGE_KEYS) / 1_000_000
    return (None if unpriced else round(total, 2)), unpriced


def day(root: Path, on: str, prices: object) -> dict[str, Any]:
    """The board's account of one day beside its work tokens: each model's tokens by kind, the estimate, and
    the models the estimate could not price."""
    models = by_model(root, on)
    estimate, unpriced = cost(models, prices)
    return {"models": models, "cost": estimate, "unpriced": unpriced}

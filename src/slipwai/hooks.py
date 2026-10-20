"""The moments an extension may attach to: a closed set the keel owns, declared once.

Version 1's extension did three things at three moments — it installed at `./init`, it re-projected its
`AGENTS.md` block on `make agents`, and it contributed a gate to `make verify` — and each was a convention
rather than a declaration. The cost showed in `codegraph`, which wanted to sync after every delegate and
could only get there through Claude Code's own hooks, so it worked on one harness and silently did nothing
on the others. A convention is a thing each extension rediscovers and each harness breaks differently.

**The set is closed, like the axes.** An extension attaches to a point; it does not invent one. A point is
a promise the keel keeps about when something runs and what it is given, and a point an extension could add
would be a promise nobody made.

Three rules make this safe to have, and they are what keep a hook from becoming a second control plane.

**The captain depends on no hook.** Its controls — the last line, the controlled-files diff, the bounded
waits, the inbox receipt — all work with every hook removed. A hook is a second belt. That is already the
rule for the harnesses' own hooks and it holds for these.

**A hook is never fatal to the rung.** It is reported, as a `hook` line naming the extension, the point and
the last thing it printed, and the rung completes. An extension that could fail a stage is an extension
that can stop a delivery loop it was added to help.

**The resolved registry is a controlled file.** `.slipwai/hooks.json` is written from the elected
extensions' manifests, and an iteration that edits it is refused like one that edits a gate — so a run
cannot register a hook on itself.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Where the resolved registry is written. A controlled file: the control guard refuses an iteration that
#: edits it, for the same reason it refuses an edit to a gate or a Makefile.
REGISTRY = ".slipwai/hooks.json"
#: What an extension's manifest declares its hooks under.
BLOCK = "hooks"
#: How long one hook may take before it is ended, where its declaration does not say.
DEFAULT_BUDGET = "30s"
#: Where a point's work is longer than a moment. `check` is a gate in `make verify`, and an extension's gate
#: renders, builds or runs a browser: ux-gates' 53 render gates in hr-test-2 took minutes, and 30 seconds
#: ended them every time though every shard passed. A hook ended for time is a gate that says nothing.
POINT_BUDGETS = {"check": "600s"}


def budget_of(point: str) -> str:
    """How long a hook at this point may take where its declaration does not say."""
    return POINT_BUDGETS.get(point, DEFAULT_BUDGET)
#: The two points whose script every extension has anyway, so the manifest need not say it.
#:
#: These were run by *convention* until slice 6.1e: `./init --extension` executed a file called `init.py`
#: and `make agents` imported it and called a function called `project_guidance()`, so an extension that
#: declared a different script at either point was ignored — the convention-not-declaration failure this
#: module opens by describing, with the keel's own name on it. A default declaration closes it without
#: making every manifest repeat what every extension already does: the point is fired through the registry
#: like the other eight, and an extension that wants another script says so and is obeyed.
#:
#: Both default to the entry point because that is the one file an extension is guaranteed to have. What
#: tells the two apart is `SLIPWAI_POINT`, which the firing script sets: at `init` an entry point installs
#: whatever it installs and projects its block; at `project` it projects and installs nothing, because a
#: re-projection happens on every `make agents` and is not an election.
DEFAULTS = {"init": "init.py", "project": "init.py"}


@dataclass(frozen=True)
class Point:
    """One moment the keel fires, what it hands over, and where it came from."""

    name: str
    when: str
    given: tuple[str, ...]
    was: str


#: In firing order where several fire around one thing, which is the order `slipwai hooks` lists them in.
POINTS: tuple[Point, ...] = (
    Point("init", "`./init --extension <key>`, once per election", ("root",), "`init.py`"),
    Point("project", "every re-projection: `make agents`, `migrate`, `./init --integration`",
          ("root", "harnesses"), "`project_guidance()`"),
    Point("check", "`make verify`, as one more gate", ("root",), "`scripts/check-<key>.py`"),
    # The four below are new. Version 1 had no way to reach a rung at all, which is why `codegraph` went
    # through one harness's own hooks and did nothing on the rest.
    Point("before-stage", "before each rung of the ladder", ("stage", "slice", "fairway", "berth"), "nothing"),
    Point("after-stage", "after each rung of the ladder", ("stage", "slice", "fairway", "berth"), "nothing"),
    Point("boundary", "every captain boundary, after the inbox is read",
          ("slice", "fairway", "lines"), "nothing"),
    Point("before-merge", "on the rebased branch, before the full gate", ("slice", "fairway", "diff"),
          "nothing"),
    # And the three below on 2026-10-08, with 7.7b. `before-merge` had no partner, so an extension with
    # something to do once a slice is actually on trunk — re-index it, publish it, tell something — had to
    # guess from a gate that passed, which is not the same event. The compaction pair were verbs inside the
    # runner: the keel wrote a harness hook row naming one script, so they worked on Claude Code and
    # nowhere else, which is the shape this file exists to replace.
    Point("after-merge", "after the slice is on trunk and pushed", ("slice", "fairway", "commit"), "nothing"),
    Point("before-compact", "a delegate's context is about to be compacted",
          ("stage", "slice", "fairway"), "`cruise.py compacting`"),
    Point("after-compact", "a delegate's session has resumed from a compacted context",
          ("stage", "slice", "fairway"), "`cruise.py resume`"),
)
NAMES = tuple(point.name for point in POINTS)


def point(name: str) -> Point:
    """One point by name, or a refusal listing the set.

    A point the keel has not got is refused rather than ignored: an extension that declared one would have
    its hook silently never run, which is the failure that is hardest to notice — the extension is
    installed, the manifest is valid, and nothing happens, for ever.
    """
    for declared in POINTS:
        if declared.name == name:
            return declared
    raise KeyError(f"`{name}` is not a point the keel fires. There are {len(POINTS)}, in firing order: "
                   f"{', '.join(NAMES)}. An extension attaches to one; it does not add one")


def declared(manifest: dict) -> dict[str, dict]:
    """An extension's hooks, normalised: `{"check": "hooks/check.py"}` and the long form both read the same.

    The short form is a path, because most hooks are "run this here" and a manifest that made every one of
    them a four-key object would be mostly punctuation.

    `DEFAULTS` are filled in last, so a manifest that names its own script at either is obeyed and one that
    names neither still has both fired through the registry. Every extension is therefore attached to at
    least two points, which is what it means for an extension to exist at all: something that installs, and
    something that tells the agent it is there.
    """
    written = manifest.get(BLOCK)
    block: dict = written if isinstance(written, dict) else {}
    found: dict[str, dict] = {}
    for name, body in block.items():
        point(name)
        if isinstance(body, str):
            found[name] = {"run": body, "budget": budget_of(name)}
        elif isinstance(body, dict) and body.get("run"):
            found[name] = {"budget": budget_of(name), **body}
        else:
            raise ValueError(f"the `{name}` hook names no script to run. A hook is a path, or an object "
                             f"with `run` and optionally `stages` and `budget`")
    for name, script in DEFAULTS.items():
        found.setdefault(name, {"run": script, "budget": budget_of(name)})
    return found


def registry(manifests: dict[str, dict]) -> dict:
    """`.slipwai/hooks.json`: every elected extension's hooks, by point, in firing order.

    Several extensions on one point run in name order and independently, so one failing does not stop the
    next — and the order is written down rather than being whatever the manifests happened to be read in.
    """
    by_point: dict[str, list[dict]] = {name: [] for name in NAMES}
    for extension in sorted(manifests):
        for name, body in sorted(declared(manifests[extension]).items()):
            by_point[name].append({"extension": extension, **body})
    return {"v": 1, "points": {name: by_point[name] for name in NAMES if by_point[name]}}

#!/usr/bin/env python3
"""Whether this project's delivery state is coherent, or only looks it.

    python3 scripts/check-crossing.py            # every question, one line each
    python3 scripts/check-crossing.py --json

**A project that crossed a version is not the same as a project generated on it.** The merge carries the
files; it cannot carry the state those files are about. One repository migrated cleanly and twenty minutes
later had: one chart covering the first of its two features, eleven slices still marked `modelled` that
were built and merged, a deck-log ref the design names and nothing had ever created, and a derived command
page a hundred and thirty-two lines behind its source. Every gate it had passed.

So these are the questions the merge leaves open, asked out loud:

1. **A chart per feature.** `clearance.py` answers for one feature. A second feature with no chart is not
   half-scheduled, it is invisible — and a `/sail <feature>` on it gets the charted feature's answer.
2. **Marks for what already shipped.** A slice that merged before the mark log existed sets nothing, so
   everything steering by it reads as blocked for ever. `clearance.py --baseline-marks` records them once.
3. **Statuses that match what merged.** `status: modelled` on a slice that is in trunk is the field the
   chart exists not to need, and a reader that believes it plans the work again.
4. **Somewhere for the logs to travel.** The deck logs are git-ignored and travel as `refs/slipwai/logs/*`.
   Where nothing has ever pushed one, every other machine and every cloud runner reads this project as one
   where nothing has been started.
5. **Hooks pointed at the project's own.** `core.hooksPath` is per-checkout config and no clone inherits it.

**It is a report, not a gate, unless asked.** `--strict` exits 1 on anything unresolved, which is what a
migration's own follow-up wants; bare, it exits 0 and says what is owed, because a project mid-crossing is
not a broken project and a command that refused to run would be one nobody ran twice.

Standalone and dependency-free, like everything under `scripts/`.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.resolve().parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.resolve().parents[1]


ROOT = project_root(Path(__file__))
SPECS = ROOT / "specs"
MODEL = ROOT / "docs/event-model/model.yaml"
LOG_REFS = "refs/slipwai/logs"
HOOKS = ".githooks"


def git(*argv: str) -> str:
    try:
        done = subprocess.run(["git", *argv], cwd=ROOT, capture_output=True, text=True, check=False)
    except OSError:  # pragma: no cover - a checkout that is not in a repository
        return ""
    return done.stdout if done.returncode == 0 else ""


def asked(name: str, ok: bool | None, what: str, fix: str = "") -> dict:
    """One line of the report. `ok` None is *nothing to ask here* — said, never counted either way."""
    return {"check": name, "ok": ok, "what": what, "fix": fix}


def features() -> list[Path]:
    return sorted(path for path in SPECS.iterdir() if path.is_dir()) if SPECS.is_dir() else []


def charts() -> list[dict]:
    found = features()
    if not found:
        return [asked("charts", None, "there are no features under specs/ yet")]
    without = [path.name for path in found if not (path / "chart.yaml").is_file()]
    if not without:
        return [asked("charts", True, f"all {len(found)} feature(s) under specs/ have a chart")]
    return [asked("charts", False,
                  f"{len(without)} of {len(found)} feature(s) have no chart.yaml: {', '.join(without)}",
                  "run `make chart` for each — clearance answers for charted features only, so a `/sail` "
                  "on one of these gets another feature's schedule")]


def slices_of(feature: Path) -> set[str]:
    return {path.name for path in (feature / "slices").iterdir() if path.is_dir()} \
        if (feature / "slices").is_dir() else set()


def charted_slices(feature: Path) -> set[str]:
    path = feature / "chart.yaml"
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    block = re.split(r"^slices:\s*$", text, flags=re.M)
    if len(block) < 2:
        return set()
    return set(re.findall(r"^  ([A-Za-z]+\d+[A-Za-z]*):\s*$", block[1], re.M))


def covered() -> list[dict]:
    """A slice with a folder and no row in its feature's chart is one no scheduler will ever name."""
    missing: list[str] = []
    for feature in features():
        if not (feature / "chart.yaml").is_file():
            continue
        missing += [f"{feature.name}/{one}" for one in sorted(slices_of(feature) - charted_slices(feature))]
    if not missing:
        return [asked("covered", True, "every slice folder is named in its feature's chart")]
    return [asked("covered", False,
                  f"{len(missing)} slice folder(s) are in no chart: {', '.join(missing[:5])}"
                  f"{'…' if len(missing) > 5 else ''}",
                  "add them to the model and run `make chart`, or they are work the schedule cannot see "
                  "and `check-dispatch` refuses a commit naming them")]


def statuses() -> list[dict]:
    """`status: modelled` on a slice whose branch has merged. The field the chart exists not to need."""
    if not MODEL.is_file():
        return [asked("statuses", None, "there is no docs/event-model/model.yaml to read")]
    merged = set()
    for feature in features():
        merged |= {one for one in slices_of(feature)
                   if git("rev-parse", "--verify", "--quiet", f"slice/{one}").strip()
                   and not git("branch", "--list", "--no-merged", f"slice/{one}").strip()}
    stale = []
    for block in re.split(r"^\s*- id:\s*", MODEL.read_text(encoding="utf-8", errors="replace"), flags=re.M)[1:]:
        ident = block.split("\n", 1)[0].strip().strip("'\"")
        if ident in merged and re.search(r"^\s*status:\s*['\"]?modelled", block, re.M):
            stale.append(ident)
    if not stale:
        return [asked("statuses", True, "no slice in the model is marked modelled with its branch merged")]
    return [asked("statuses", False,
                  f"{len(stale)} slice(s) are `modelled` in the model and merged in trunk: "
                  f"{', '.join(stale[:5])}{'…' if len(stale) > 5 else ''}",
                  "reconcile them — a status written at plan time and never corrected is what the mark log "
                  "replaced, and a reader that believes it plans the work again")]


def marks() -> list[dict]:
    """Whether anything has recorded a mark for work that shipped before the log existed."""
    logs = ROOT / ".slipwai/logs"
    lines = []
    for path in sorted(logs.rglob("*.jsonl")) if logs.is_dir() else []:
        lines += [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                  if '"mark-set"' in line]
    if not features():
        return [asked("marks", None, "there are no features under specs/ yet")]
    if lines:
        return [asked("marks", True, f"{len(lines)} mark-set line(s) are recorded in this checkout")]
    return [asked("marks", False, "no mark-set line exists in .slipwai/logs/",
                  "run `python3 scripts/agents/clearance.py --baseline-marks` once — until a mark is set, "
                  "every slice steering by one reads as blocked")]


def travelling() -> list[dict]:
    """Whether the deck logs have anywhere to go. The design names the refs; nothing may have made one."""
    if not git("remote").strip():
        return [asked("travel", None, "this project has no remote, so nothing travels off this machine")]
    refs = [line for line in git("for-each-ref", "--format=%(refname)", LOG_REFS).splitlines() if line.strip()]
    if refs:
        return [asked("travel", True, f"{len(refs)} log ref(s) exist under {LOG_REFS}")]
    return [asked("travel", False, f"nothing has ever pushed a log to {LOG_REFS}",
                  "run `make depart` once — until then this project's own history is on one machine, and "
                  "every clone and cloud runner reads it as a project where nothing has been started")]


def hooked(fix: bool = False) -> list[dict]:
    """Whether this checkout is pointed at the hooks it carries — and, asked, point it.

    `--fix-hooks` is what `make hooks` runs and what `make dispatch` depends on, because *every clone and
    worktree needs it once* is a sentence nobody acts on in a loop nobody is watching. Setting it is safe
    to automate for the same reason the baseline is: it is idempotent, and it never takes a path somebody
    else owns.
    """
    if not (ROOT / HOOKS).is_dir():
        return [asked("hooks", None, f"{HOOKS}/ is not in this checkout")]
    where = git("config", "--get", "core.hooksPath").strip()
    if where == HOOKS:
        return [asked("hooks", True, f"core.hooksPath is {HOOKS}")]
    if where:
        # Never taken. An adopted repository on husky or lefthook keeps what it has, and is told how to
        # chain rather than finding its own hooks quietly turned off by a factory.
        return [asked("hooks", False, f"core.hooksPath is `{where}`, not {HOOKS}",
                      f"chain {HOOKS}/pre-push from it, or `git config core.hooksPath {HOOKS}`")]
    if fix:
        # `git config <key> <value>` prints nothing either way, so the answer is read back rather than
        # taken from the call: a set that silently did not happen is the one outcome worth catching.
        git("config", "core.hooksPath", HOOKS)
        if git("config", "--get", "core.hooksPath").strip() == HOOKS:
            return [asked("hooks", True, f"core.hooksPath set to {HOOKS} by this run")]
        return [asked("hooks", False, "core.hooksPath could not be set", "run `make hooks`")]
    return [asked("hooks", False, "core.hooksPath is unset in this checkout",
                  "run `make hooks` — it is per-checkout config, so every clone and worktree needs it once")]


def crossing(fix_hooks: bool = False) -> list[dict]:
    return [*charts(), *covered(), *statuses(), *marks(), *travelling(), *hooked(fix_hooks)]


def main(argv: list[str]) -> int:
    if "--fix-hooks" in argv and "--json" not in argv:
        # What `make hooks` runs: the one question, answered and fixed, without the other five.
        for row in hooked(fix=True):
            print(f"check-crossing: {row['what']}")
            if row["ok"] is False and row["fix"]:
                print(f"                {row['fix']}")
        return 0
    found = crossing("--fix-hooks" in argv)
    owed = [row for row in found if row["ok"] is False]
    if "--json" in argv:
        print(json.dumps({"v": 1, "root": str(ROOT), "checks": found, "owed": len(owed)}))
        return 1 if owed and "--strict" in argv else 0
    for row in found:
        word = {True: "ok  ", False: "OWED", None: "none"}[row["ok"]]
        print(f"check-crossing: {word} {row['check']}: {row['what']}")
        if row["ok"] is False and row["fix"]:
            print(f"                     {row['fix']}")
    if owed:
        print(f"check-crossing: {len(owed)} thing(s) this crossing still owes. None of them is a broken "
              f"project; each is state the merge could not carry")
        return 1 if "--strict" in argv else 0
    print(f"check-crossing: {len(found)} question(s), nothing owed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

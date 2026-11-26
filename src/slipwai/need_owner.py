"""Who acts on a need, and why, in words a person reads: the trunk mender, the slice's own merge, whoever
decides, or a person.

manda's board showed seven things *Waiting on you* and one of them needed a person. The others were the
fleet's own work, stranded: a flaky test in a folder no open slice touched, a merged slice's demo story, a
model patch asked as a decision, and every card offered *Have the mender try again*, which did nothing for
the five the mender would never take. The rule for what the mender takes lived in `mender.py`, which the
board cannot import, so the board guessed — and guessed that every need the fleet ticks was the mender's.

So the rule is here, carried into the toolkit beside the harbourmaster (`make shared`), and both ask it: the
mender before it starts an attempt, and the board before it says who acts. Standard library only, like every
module carried that way.

**Where a need's change may land** is everywhere but four things: a gate (`NEVER`); the cloud under `infra/`
(`PERSONS`), but for a flag's declaration; a slice's own folder while that slice is still being built; and
source and tests that an open slice's branch is changing. A merged slice's folder, and code no open slice
touches, are nobody else's, so the mender takes them and the full gate stays the guard. Where nothing can
say which paths the open slices touch, code is still a slice's — the rule as it was.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import Any

#: Never the mender's, whatever the job. A gate passes on its own merits, so nothing that is a gate, runs
#: one, or decides what an agent may do is a file it may edit.
NEVER = ("scripts/", "tools/", ".githooks/", ".slipwai/", ".specify/", "agents/", "commands/", "skills/",
         "Makefile", "harbour.json", "project.json", ".github/")
#: The skill that says how this project's app is run is the project's own record, kept up as the app
#: changes, so it is the one thing under `skills/` a need may change.
KEPT_UP = ("skills/run-the-app/",)
#: A flag's declaration is the one file under `infra/` a need may change: additive, and seeded `off`.
FLAGS = "infra/service/flags.auto.tfvars"
#: The cloud, which is a person's because a change there spends money and reaches production.
PERSONS = ("infra/",)
#: A slice's own record, by the slice it belongs to.
SLICE_FOLDER = re.compile(r"^specs/[^/]+/slices/([^/]+)/")
#: Code: `src/` and the test folders, wherever a deployable keeps them.
CODE = re.compile(r"(?:^|/)(?:src|test|tests|__tests__)/")
#: A hand-back patch a slice carries in its own record, named by the need it lands: its slice is the group.
PATCH = re.compile(r"specs/[^/\s]+/slices/([^/\s]+)/handback/[^/\s]+\.patch")
#: A need only a person can meet because it needs something only a person holds.
SECRET = re.compile(r"\b(?:secrets?|credentials?|passwords?|tokens?|(?:api|access|signing|sending|private) keys?)\b",
                    re.IGNORECASE)
#: Used where `harbour.json` names no `attempts`.
DEFAULT_ATTEMPTS = 3
#: Who acts: the mender will; the mender tried every attempt it had; it lands with its slice's merge; whoever
#: decides answers it; a person does.
MENDER, SPENT, MERGE, DECIDE, PERSON = "mender", "spent", "merge", "decision", "person"
#: Each open slice branch's changed paths, by (trunk commit, branch commit): a board read asks every pass.
SEEN: dict[tuple[str, str], list[str]] = {}


def never(path: str) -> bool:
    """Whether a path is one no mend may change: a gate, what runs one, or what decides what an agent may do."""
    return any(path == one.rstrip("/") or path.startswith(one) for one in NEVER)


def path_refusal(path: str, busy: Mapping[str, str] | None = None, merged: Collection[str] = ()) -> str:
    """Why a need's change may not land on this path, in a sentence a person reads, or `""` where it may.

    `busy` is each path an open slice's branch changes, against that slice; None where nothing could say,
    and then code is a slice's. `merged` is the slices that have merged, whose own folders are nobody's."""
    if any(path.startswith(one) for one in KEPT_UP) or path == FLAGS:
        return ""
    if never(path):
        return "It changes one of the checks the fleet runs on, and no agent may edit those."
    if any(path.startswith(one) for one in PERSONS):
        return "It changes the cloud set-up, which spends money and reaches production, so a person makes it."
    folder = SLICE_FOLDER.match(path)
    if folder:
        if folder.group(1) in merged:
            return ""
        return (f"It is in the record of slice {folder.group(1)}, which is still being built, so that slice "
                f"writes it.")
    if CODE.search(path):
        if busy is None:
            return "It is code or a test, and nothing could say whether a slice in flight is changing it."
        holder = busy.get(path, "")
        return f"Slice {holder} is changing this file on its own branch, so the change is that slice's." \
            if holder else ""
    return ""


def whose(need: object, decision: bool, cruising: bool, busy: Mapping[str, str] | None = None,
          merged: Collection[str] = ()) -> tuple[str, str]:
    """Who acts on a need that is not met yet, and why where it is not the mender: (`MENDER` and `""`, or one
    of `MERGE`, `DECIDE`, `PERSON` and a sentence). `decision` is `logs.asks_a_decision(need)`, asked by the
    caller because this module imports nothing of the keel's. Attempts spent are `spent`'s to say."""
    if not isinstance(need, dict):
        return PERSON, "Nothing on trunk can show it is done, so only you can say so."
    patch = PATCH.search(str(need.get("what", "")))
    if patch and patch.group(1) not in merged:
        return MERGE, f"It is a patch slice {patch.group(1)} carries, and it lands with that slice's merge."
    if patch and decision:
        return DECIDE, (f"Slice {patch.group(1)} merged without this patch, because it changes what the model "
                        f"records rather than bringing it in line with the code, so it is yours to decide.")
    if decision:
        return DECIDE, ("It is a decision about what the product does, so whoever decides answers it: the skipper "
                        "while the fleet cruises, otherwise you.")
    held = need.get("check")
    check: dict[str, Any] = held if isinstance(held, dict) else {}
    if SECRET.search(f"{need.get('what', '')} {need.get('plain', '')}") and check.get("kind") != "text":
        return PERSON, "It needs a secret or a credential, and only a person holds those."
    if check.get("kind") == "make":
        return PERSON, ("It is proved by a check run on trunk, not by a change to one file, so the mender does "
                        "not take it.")
    if check.get("kind") != "text" or not check.get("path"):
        return PERSON, "Nothing on trunk can show it is done, so only you can say so."
    if str(need.get("by", "person")) != "fleet" and not cruising:
        return PERSON, "The slice asked for a person to do this, and the fleet is not cruising on its own."
    refused = path_refusal(str(check["path"]), busy, merged)
    return (PERSON, refused) if refused else (MENDER, "")


def tally(harbour: Iterable[Any]) -> dict[tuple[str, str, int], dict[str, Any]]:
    """What the mender has done with each need, by (fairway, parked, index): `tried` since a person last asked
    for it afresh (`mend-again`), `landed`, and its last failure's `why` and whether it `declined` — ended with
    nothing changed and said why, which another attempt would only say again."""
    held: dict[tuple[str, str, int], dict[str, Any]] = {}
    for line in harbour:
        fields = line.fields
        if line.kind == "mend-again":
            again = (str(fields.get("fairway", "")), str(fields.get("parked", "")))
            for key, one in held.items():
                if key[:2] == again:
                    one.update(tried=0, declined=False)
            continue
        if fields.get("job") != "need" or line.kind not in ("mend", "mended", "mend-failed"):
            continue
        key = (str(fields.get("fairway", "")), str(fields.get("parked", "")), int(fields.get("need", -1)))
        one = held.setdefault(key, {"tried": 0, "landed": False, "why": "", "declined": False})
        if line.kind == "mend":
            one["tried"] += 1
        elif line.kind == "mended":
            one["landed"] = True
        else:
            one["why"], one["declined"] = str(fields.get("why", "")), bool(fields.get("declined"))
    return held


def spent(one: Mapping[str, Any] | None, allowed: int) -> bool:
    """Whether the mender has no attempt left at a need: every one tried, or the last declined."""
    return bool(one) and (bool(one.get("declined")) or int(one.get("tried", 0)) >= allowed)  # type: ignore[union-attr]


def read_json(path: Path) -> dict[str, Any]:
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def allowed(root: Path) -> int:
    """How many attempts the mender has at one need: `harbour.json`'s `attempts`, else the default."""
    held = read_json(root / "harbour.json").get("attempts")
    return held if isinstance(held, int) and not isinstance(held, bool) and held > 0 else DEFAULT_ATTEMPTS


def cruising(root: Path) -> bool:
    """Whether the fleet runs with nobody at the wheel, so a person's need checked on a file is the mender's."""
    held = read_json(root / ".specify/cruise.json")
    return held.get("enabled") is True and str(held.get("decide") or "recommended-first") in (
        "recommended-first", "skipper-always")


def git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=False)
    except OSError as fault:
        return subprocess.CompletedProcess(["git", *argv], 1, "", str(fault))


def touched(root: Path, base: str, slices: Iterable[str]) -> dict[str, str] | None:
    """Each path an open slice's branch changes against trunk, against the first such slice; None where trunk
    is not known, so nothing can be said. A branch is `slice/<id>`, here or on the remote."""
    if not base:
        return None
    wanted = list(dict.fromkeys(slices))
    if not wanted:
        return {}
    listed = git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/slice/",
                 "refs/remotes/origin/slice/")
    if listed.returncode != 0:
        return None
    heads: dict[str, str] = {}
    for line in listed.stdout.splitlines():
        name, _, commit = line.partition(" ")
        heads.setdefault(name.removeprefix("refs/heads/").removeprefix("refs/remotes/origin/"), commit)
    found: dict[str, str] = {}
    for slice_id in wanted:
        commit = heads.get(f"slice/{slice_id}", "")
        if not commit:
            continue
        if (base, commit) not in SEEN:
            if len(SEEN) > 1024:
                SEEN.clear()
            done = git(root, "diff", "--name-only", f"{base}...{commit}")
            SEEN[(base, commit)] = [path for path in done.stdout.splitlines() if path] if done.returncode == 0 else []
        for path in SEEN[(base, commit)]:
            found.setdefault(path, slice_id)
    return found

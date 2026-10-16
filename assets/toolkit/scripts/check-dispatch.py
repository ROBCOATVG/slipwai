#!/usr/bin/env python3
"""Refuse a commit that names work no plan knows, or work no dispatch accounts for.

    python3 scripts/check-dispatch.py                 # this branch against trunk
    python3 scripts/check-dispatch.py --range A..B
    python3 scripts/check-dispatch.py --stdin         # as git's `pre-push` hands it over

**This is the only gate here that holds whoever is driving.** Every other one is a rule a session has to
choose to read: the command page is prose, `make verify` runs when something runs it, and the session-start
guards reach three of the registry's thirty-six harnesses. Git reaches all of them, because git does not
know which agent is pushing.

It refuses two things, and both of them happened in one run:

**Work that is in no plan.** Six commits named `UI1` through `UI9` — items in no chart, no `model.yaml`
and no `slices/` directory, invented mid-run from a plan file nothing reads. A rule that checked only
*known* slice ids would have waved every one of them through, so the shape is the test and the plan is
the answer: a token shaped like an id that no plan knows is refused by that fact alone.

**Work no dispatch accounts for.** A slice the plan does know, pushed with no line in
`specs/<feature>/dispatch-ledger.jsonl` saying it was started — dispatched into a worktree, or taken here
because this harness cannot delegate. The ledger is written by `dispatch.py` at the moment of dispatch and
committed, so a checkout that has the commit has the evidence about it.

**Where it looks, and why so narrowly.** The subject line, up to its first colon, and nowhere else. Every
commit in the run this came from names its work there — `036 UI9: …`, `SB2V: …`, `036 SB4-SB7 browser: …`
— and a gate that read whole messages would refuse a commit for saying `HTTP2` in a sentence. A refusal
that is wrong costs more than a miss here: this one blocks a push, and a gate people switch off holds
nothing at all. Decision ids (`D12`) and task ids (`T018`) are excluded by shape, because they are not
slices and never were.

Standalone and dependency-free: PyYAML is read where it is installed and the charts are read by pattern
where it is not, because a gate that could not run without a dependency would be a gate nobody installed.
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
LEDGER = "dispatch-ledger.jsonl"
#: What a slice id looks like: letters then digits, optionally one more letter — `SB1`, `SB7V`, `OB7I`,
#: `TN16V`, `GV5`, `UI9`. Anchored whole, so `HTTP2XX` inside a word is not one.
SHAPE = re.compile(r"^[A-Z]{1,5}\d{1,3}[A-Z]{0,2}$")
#: Shapes that are id-like and are never slices: a decision and a task. Excluded by what they are rather
#: than by a list of the ones seen so far, which would need editing every time a project minted one.
NOT_SLICES = re.compile(r"^(D\d+|T\d+)$")
#: Where a commit says what it is about. Everything after the first colon is prose about the change.
SUBJECT = re.compile(r"^([^:\n]*):")


def git(*argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=ROOT, capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else ""


def charted() -> set[str]:
    """Every slice id any plan in this project knows: the charts' `slices` blocks and the event model.

    Read by pattern rather than parsed. A gate that refuses a push has to run on whatever interpreter the
    person has, and `yaml` is not in the standard library — so the question asked is *does any plan name
    this id*, which a pattern answers exactly as well as a parse and without the dependency.
    """
    found: set[str] = set()
    texts = [path.read_text(encoding="utf-8", errors="replace")
             for path in sorted(SPECS.glob("*/chart.yaml")) if path.is_file()] if SPECS.is_dir() else []
    if MODEL.is_file():
        texts.append(MODEL.read_text(encoding="utf-8", errors="replace"))
    for text in texts:
        found |= {match for match in re.findall(r"^\s*-?\s*(?:id:\s*)?['\"]?([A-Za-z]+\d+[A-Za-z]*)['\"]?\s*:?\s*$",
                                                text, re.M)}
        found |= set(re.findall(r"^\s*-\s*id:\s*['\"]?([A-Za-z]+\d+[A-Za-z]*)['\"]?", text, re.M))
    if SPECS.is_dir():
        found |= {path.name for path in SPECS.glob("*/slices/*") if path.is_dir()}
    return {one for one in found if one}


def ledgered() -> set[str]:
    """Every slice any feature's dispatch ledger accounts for, however it accounts for it."""
    found: set[str] = set()
    for path in sorted(SPECS.glob(f"*/{LEDGER}")) if SPECS.is_dir() else []:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("slice"):
                found.add(str(row["slice"]))
    return found


def named(subject: str) -> list[str]:
    """The slice-shaped tokens one commit subject claims, before its first colon and nowhere else."""
    head = SUBJECT.match(subject)
    if head is None:
        return []
    words = re.split(r"[\s,/()\[\]]+|(?<=[A-Z0-9])-(?=[A-Z])", head.group(1))
    return [word for word in (one.strip(".,;") for one in words)
            if SHAPE.match(word) and not NOT_SLICES.match(word)]


def trunk() -> str:
    for candidate in ("origin/main", "origin/master", "main", "master"):
        if git("rev-parse", "--verify", "--quiet", candidate).strip():
            return candidate
    return ""


def commits(span: str) -> list[tuple[str, str]]:
    """(hash, subject) for each commit in the range, newest last. Empty where the range names nothing."""
    text = git("log", "--no-merges", "--format=%H%x1f%s", span)
    found = []
    for line in text.splitlines():
        if "\x1f" in line:
            commit, subject = line.split("\x1f", 1)
            found.append((commit.strip(), subject.strip()))
    return list(reversed(found))


def ranges(argv: list[str]) -> list[str]:
    """Which commits to judge: an explicit range, git's `pre-push` on stdin, or this branch against trunk."""
    if "--range" in argv:
        index = argv.index("--range") + 1
        return [argv[index]] if index < len(argv) else []
    if "--stdin" in argv:
        found = []
        base = ""
        for line in sys.stdin.read().splitlines():
            parts = line.split()
            if len(parts) != 4:
                continue
            _, local, _, remote = parts
            if set(local) == {"0"}:
                continue  # a branch being deleted carries no commits to judge
            if set(remote) != {"0"} and remote:
                found.append(f"{remote}..{local}")
                continue
            # A branch the remote has never seen. Forty zeros means "new", and bare `local` is every
            # ancestor — the whole history, including commits already on trunk. The commits being pushed
            # are the same range a push with no arguments already judges.
            if not base:
                base = trunk()
            found.append(f"{base}..{local}" if base else local)
        return found
    base = trunk()
    return [f"{base}..HEAD"] if base else []


def faults(span: str, plans: set[str], accounted: set[str]) -> list[str]:
    found = []
    for commit, subject in commits(span):
        for token in named(subject):
            if token not in plans:
                found.append(
                    f"{commit[:8]} names {token}, which is in no chart, no event model and no "
                    f"specs/*/slices/ — so it is work no plan knows about. Put it in the model and run "
                    f"`make chart`, or name the slice this commit is really part of ({subject!r})")
            elif token not in accounted:
                found.append(
                    f"{commit[:8]} names {token} and no dispatch ledger accounts for it. Run "
                    f"`make dispatch` before starting a slice — it records the worktree and the delegate, "
                    f"or the reason this session could not delegate — and commit the ledger with the work")
    return found


def main(argv: list[str]) -> int:
    spans = ranges(argv)
    if not spans:
        print("check-dispatch: no range to judge and no trunk to compare with — nothing to hold")
        return 0
    plans, accounted = charted(), ledgered()
    if not plans:
        print("check-dispatch: no chart, no event model and no slice folders, so no plan says what the "
              "ids in a commit mean — nothing to hold")
        return 0
    found = [fault for span in spans for fault in faults(span, plans, accounted)]
    if found:
        print("check-dispatch: a commit names work no plan knows, or work no dispatch accounts for\n",
              file=sys.stderr)
        for fault in dict.fromkeys(found):
            print(f"  {fault}", file=sys.stderr)
        print(file=sys.stderr)
        return 1
    judged = sum(len(commits(span)) for span in spans)
    print(f"check-dispatch: {judged} commit(s) judged; every slice they name is planned and dispatched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

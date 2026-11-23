#!/usr/bin/env python3
"""Fold each fairway's append-only files into the feature-level ones nobody edits by hand.

Two fairways appending to one `decisions.md` is the shared-file problem the ids already fixed from the other
side: in the first attempt it produced 54 renumbering commits in a night, and every merge of that file was a
conflict in the same three lines. So each fairway writes its own — `fairways/<name>/decisions.md`,
`adversary-log.md` — and two fairways never meet on one line, because they are never in one file.

The feature-level file still has to exist, because a reader wants one list and a citation has to resolve. It
is **rendered**, by this, and never written: the sources are the fairway files, the order is the instant each
entry records, and `--check` refuses a rendered file that is not what its sources render to. That is
`scripts/glossary.py --check`'s pattern, which this repository has used since slice 1.6 for the same reason —
a generated file somebody edited is a file that disagrees with its source and says nothing about it.

**The order is the instant, not the fairway.** Interleaving by time is what makes the feature-level file read
as one history rather than as two lists stapled together. Ids are *not* renumbered to match, and that is the
point of them carrying their fairway: `D-ORD-07` sitting between `D-BIL-02` and `D-BIL-03` is not a gap, and
a reader who knows the scheme is not confused by it.

**One file per entry, inside a fairway as well as across them.** A fairway's own copy stopped two fairways
meeting on one line and did nothing for the seven slices one fairway runs abreast, which all appended to it —
or, with no fairway copy at all, to the feature-level file itself. Their merges were a union of two endings,
and a union done by hand or by a weave drops the lines the two sides share: manda lost a record's
`- **Status:** standing` six times that way, and `check-decisions` refused the merge after each. So a
decision is written as its own file, `specs/<feature>/decisions/<id>.md`, and a slice's adversary rows as
theirs, `specs/<feature>/adversary-log/<slice or capability>.md`. Two slices then never write one file, and
the feature-level file is rendered from those records together with any fairway copies that predate them.

**An entry no source holds is adopted, never dropped.** Writing — not `--check` — moves every entry in the
feature-level file that no record or fairway copy holds into a record of its own before it renders: a
`decisions.md` written by hand before the records existed (which is how `slipwai migrate` splits one, with
`--split`), and an entry a page older than this one appended to the rendered file. `--check` names them
instead, and says `make decisions` moves them.

    python3 scripts/render-fairways.py           # write the feature-level files
    python3 scripts/render-fairways.py --check    # fail where one is not what its sources render to
    python3 scripts/render-fairways.py --split    # the folded logs alone: adopt, then render
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


ROOT = project_root(Path(__file__).resolve())
FAIRWAYS = ROOT / "fairways"
SPECS = ROOT / "specs"
#: The append-only files a fairway keeps its own copy of, and the feature-level file each folds into.
FOLDED = ("decisions.md", "adversary-log.md")
#: Each folded file's records: the directory beside it, under `specs/<feature>/`, holding one file per entry.
RECORDS = {"decisions.md": "decisions", "adversary-log.md": "adversary-log"}
#: A decision's id in its heading — `D470`, or a fairway's `D-ORD-07` — which is its record's file name.
DECISION_ID = re.compile(r"^## (D(?:-[A-Za-z0-9][A-Za-z0-9_-]*-)?-?\d+) — ")
#: The instant an entry records, which is what the fold orders by. An entry without one sorts after the
#: entries that have one, in the order its own file had it — visible rather than silently first.
WHEN = re.compile(r"\*\*When:\*\*\s*(\S+)")
#: One entry: a `## ` heading and everything until the next one. Found rather than split, because splitting
#: on the heading loses whether the file opened with one and the first entry goes with the preamble.
ENTRY = re.compile(r"^## .*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
BANNER = ("<!-- Rendered by `make decisions` from one file per entry under {records}/ beside this file, and any\n"
          "     fairways/*/{name}. Never edit by hand: `make check-rendered` refuses a file that is not what its\n"
          "     sources render to. Write or edit the entry's own file. -->\n")


def entries(text: str) -> list[str]:
    """One string per `## ` entry, with whatever preamble the file has dropped."""
    return [found.group(0).rstrip() + "\n" for found in ENTRY.finditer(text)]


def ordered(parts: list[str]) -> list[str]:
    """Every entry, by the instant it records. Stable, so two entries of one instant keep their file's order."""
    return sorted(parts, key=lambda part: (WHEN.search(part) is None, (WHEN.search(part) or [None, ""])[1]))


def natural(path: Path) -> list[object]:
    """A record's name as its numbers read: D9 before D10, which a plain sort puts the other way round."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.stem)]


def records(name: str, where: str = "") -> list[Path]:
    """A feature's own records of one folded file, `specs/<feature>/<records>/*.md`, in their numbers' order."""
    folder = SPECS / (where or feature()) / RECORDS[name]
    return sorted(folder.glob("*.md"), key=natural) if folder.is_dir() else []


def sources(name: str, where: str = "") -> list[Path]:
    """A feature's fairway files: `fairways/<fairway>/<feature>/<name>`, and for the first feature the ones a
    fairway keeps beside them with no feature in the path, which were written when there was one feature —
    then the feature's records, one file per entry, which is where every entry since is written."""
    where = where or feature()
    copies: list[Path] = []
    if FAIRWAYS.is_dir():
        bare = [*FAIRWAYS.glob(f"*/{name}")] if where == feature() else []
        copies = sorted([*bare, *FAIRWAYS.glob(f"*/{where}/{name}")])
    return [*copies, *records(name, where)]


def key(name: str, part: str) -> str:
    """What makes an entry the same entry wherever it is written: a decision's id, an adversary row's heading."""
    heading = part.split("\n", 1)[0].rstrip()
    found = DECISION_ID.match(heading) if name == "decisions.md" else None
    return found.group(1) if found else heading


def record_name(name: str, part: str) -> str:
    """The record an entry belongs in: its decision id, or the slice or capability its adversary row heads."""
    if name == "decisions.md" and (found := DECISION_ID.match(part)):
        return f"{found.group(1)}.md"
    head = part.split("\n", 1)[0][3:].split(" · ", 1)[0]
    return (re.sub(r"[^A-Za-z0-9._-]+", "-", head).strip("-.")[:80] or "entry") + ".md"


def held(name: str, where: str) -> dict[str, tuple[str, Path]]:
    """Every entry the sources hold, by its key, with its text and the file it is in."""
    found: dict[str, tuple[str, Path]] = {}
    for path in sources(name, where):
        for part in entries(path.read_text(encoding="utf-8")):
            found.setdefault(key(name, part), (part, path))
    return found


def orphans(name: str, where: str) -> list[str]:
    """The entries of the feature-level file no source holds: written to it by hand, or before the records."""
    path = SPECS / where / name
    if not path.is_file():
        return []
    known = held(name, where)
    return [part for part in entries(path.read_text(encoding="utf-8")) if key(name, part) not in known]


def adopt(name: str, where: str) -> int:
    """Every orphan moved into a record of its own — appended to the record its key names where one exists —
    so the render that follows keeps it. How many were moved."""
    found = orphans(name, where)
    for part in found:
        target = SPECS / where / RECORDS[name] / record_name(name, part)
        target.parent.mkdir(parents=True, exist_ok=True)
        was = target.read_text(encoding="utf-8").rstrip("\n") + "\n\n" if target.is_file() else ""
        target.write_text(was + part, encoding="utf-8")
    return len(found)


def features() -> list[str]:
    """Every feature with a slice record or a log's records, in name order. Each is folded from its own fairway
    files and records: only the first was, and a further feature's decisions stayed in its fairways' copies with
    no file a reader opens."""
    if not SPECS.is_dir():
        return []
    return sorted(path.name for path in SPECS.glob("*/")
                  if any((path / folder).is_dir() for folder in ("slices", *RECORDS.values())))


def feature() -> str:
    """The first feature with a slice record, which a fairway file naming no feature belongs to."""
    found = sorted(path.name for path in SPECS.glob("*/") if (path / "slices").is_dir()) if SPECS.is_dir() else []
    return found[0] if found else ""


def rendered(name: str, where: str = "") -> str:
    """What the feature-level file should hold, from every fairway's own copy and every record."""
    parts: list[str] = []
    for path in sources(name, where):
        parts.extend(entries(path.read_text(encoding="utf-8")))
    return BANNER.format(name=name, records=RECORDS[name]) + "\n" + "\n".join(ordered(parts))


#: The split's own file, and the one column in it nobody types.
SPLIT = "story-split.md"
#: What a `held_by` cell says when nobody holds that fairway. An em dash, which is what the split template
#: and the skill both already write there.
NOBODY = "—"
#: The split's fairways table, by its header row. Found rather than counted from the top: a split has three
#: tables and the one above this has five columns too.
FAIRWAY_TABLE = re.compile(r"^\|\s*Fairway\s*\|.*\|\s*$", re.M)


def claims_module() -> object | None:
    """`scripts/agents/claims.py`, or None in a project that has not got it.

    Imported here rather than at the top because this script also runs in a project whose toolkit predates
    the claim: the fold of the decisions files is the older job and must not stop for the newer one.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent / "agents"))
    try:
        import claims  # noqa: PLC0415
    except ImportError:  # pragma: no cover - a toolkit older than the claim
        return None
    return claims


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def split_rendered(text: str, holders: dict[str, str]) -> str:
    """The split with every `held_by` cell rewritten from the claim refs.

    Only that one cell: the rest of the table is the split's own work and this is not a renderer of it.
    What makes the column trustworthy is that a name somebody typed does not survive the next fold —
    the hand edit is not an error to report, it is a thing that does not last.
    """
    lines = text.splitlines(keepends=True)
    header = next((index for index, line in enumerate(lines) if FAIRWAY_TABLE.match(line)), None)
    if header is None:
        return text
    names = cells(lines[header])
    if "held_by" not in names:
        return text
    column = names.index("held_by")
    for index in range(header + 2, len(lines)):
        if not lines[index].lstrip().startswith("|"):
            break
        row = cells(lines[index])
        if len(row) != len(names):
            continue
        fairway = row[0].strip("`*_ ")
        row[column] = holders.get(fairway, NOBODY) or NOBODY
        lines[index] = "| " + " | ".join(row) + " |\n"
    return "".join(lines)


def held_by(where: str) -> tuple[dict[str, str], str]:
    """Who holds each fairway the split names, and the note to print where the answer is local.

    A claim no other machine can see is not routing, whatever this machine's ref says — so a harbour with
    no forge renders nothing in the column and the command says why, rather than naming a machine nobody
    else can reach and leaving a reader to find out which it was.
    """
    claims = claims_module()
    path = SPECS / where / SPLIT
    if claims is None or not path.is_file():
        return {}, ""
    text = path.read_text(encoding="utf-8")
    header = next((line for line in text.splitlines() if FAIRWAY_TABLE.match(line)), None)
    if header is None:
        return {}, ""
    names = cells(header)
    fairways = []
    for line in text.splitlines():
        row = cells(line)
        if line.lstrip().startswith("|") and len(row) == len(names) and row[0] not in (names[0], "---"):
            fairways.append(row[0].strip("`*_ "))
    if not claims.forge(ROOT):  # type: ignore[attr-defined]
        return {}, (f"render-fairways: there is no `origin` to push a claim to, so every claim is local to "
                    f"this machine and {SPLIT}'s held_by is left as {NOBODY}")
    return {fairway: claim.machine
            for fairway, claim in claims.every(ROOT, fairways).items()  # type: ignore[attr-defined]
            if claim is not None}, ""


def main(argv: list[str]) -> int:
    checking = "--check" in argv
    if not features():
        print("render-fairways: no feature with a slice record yet; nothing to fold")
        return 0
    drifted: list[str] = []
    for where in features():
        fold(where, checking, drifted, split="--split" in argv)
    if drifted:
        print("render-fairways: a rendered file is not what its sources render to\n", file=sys.stderr)
        for path in drifted:
            print(f"  {path}", file=sys.stderr)
        print("\nRun: make decisions", file=sys.stderr)
        return 1
    if checking:
        print("render-fairways: the feature-level files are what their records and fairways/*/ render to")
    return 0


def fold(where: str, checking: bool, drifted: list[str], split: bool = False) -> None:
    """One feature's split and its folded files, written or — checking — added to `drifted` where they differ.
    `split` folds the logs alone and leaves the story split's `held_by` as it is."""
    if not split:
        fold_split(where, checking)
    for name in FOLDED:
        fold_log(name, where, checking, drifted)


def fold_log(name: str, where: str, checking: bool, drifted: list[str]) -> None:
    """One folded file of one feature: its orphans adopted and the file rendered, or — checking — said."""
    path = SPECS / where / name
    relative = path.relative_to(ROOT).as_posix()
    if checking:
        if not sources(name, where):
            return
        lost = [key(name, part) for part in orphans(name, where)]
        if lost:
            drifted.append(f"{relative}: {', '.join(lost[:5])}{' …' if len(lost) > 5 else ''} in no record — "
                           f"`make decisions` moves each into specs/{where}/{RECORDS[name]}/")
        elif not path.is_file() or path.read_text(encoding="utf-8") != rendered(name, where):
            drifted.append(f"{relative}: edited by hand, or a record changed since it was folded — the records "
                           f"under specs/{where}/{RECORDS[name]}/ are the source")
        return
    adopted = adopt(name, where)
    if adopted:
        print(f"render-fairways: {relative}: {adopted} entr{'y' if adopted == 1 else 'ies'} moved into "
              f"specs/{where}/{RECORDS[name]}/, one file each")
    if not sources(name, where):
        return
    if path.is_file():
        known = held(name, where)
        for part in entries(path.read_text(encoding="utf-8")):
            text, source = known.get(key(name, part), (part, path))
            if text != part:
                print(f"render-fairways: {key(name, part)} in {relative} differed from "
                      f"{source.relative_to(ROOT).as_posix()}, which is its source and was kept; an edit meant "
                      f"for it is made there")
    meant = rendered(name, where)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(meant, encoding="utf-8")
    print(f"render-fairways: {relative} from {len(sources(name, where))} source file(s)")


def fold_split(where: str, checking: bool) -> None:
    """The story split's `held_by`, from the claim refs."""
    holders, note = held_by(where)
    split = SPECS / where / SPLIT
    if split.is_file():
        was = split.read_text(encoding="utf-8")
        meant = split_rendered(was, holders)
        # Never held by `--check`. `held_by` is the only cell here this renders, and it is the claim refs at
        # the moment of the last fold, which move whenever a fleet takes or gives back a fairway: held, it
        # turned `make verify` red on trunk mid-run (game-club-manager: clubs released, tables taken), and the
        # only fix was to commit a machine's name. The fold still writes it fresh, and a typed name in it
        # still does not survive the next one.
        if not checking and was != meant:
            split.write_text(meant, encoding="utf-8")
            print(f"render-fairways: {split.relative_to(ROOT).as_posix()}'s held_by from the claim refs")
        if note:
            print(note)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

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

    python3 scripts/render-fairways.py           # write the feature-level files
    python3 scripts/render-fairways.py --check    # fail where one is not what its sources render to
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
#: The instant an entry records, which is what the fold orders by. An entry without one sorts after the
#: entries that have one, in the order its own file had it — visible rather than silently first.
WHEN = re.compile(r"\*\*When:\*\*\s*(\S+)")
#: One entry: a `## ` heading and everything until the next one. Found rather than split, because splitting
#: on the heading loses whether the file opened with one and the first entry goes with the preamble.
ENTRY = re.compile(r"^## .*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
BANNER = ("<!-- Rendered from fairways/*/{name} by `make decisions`. Never edit by hand: `make check-rendered`\n"
          "     refuses a file that is not what its sources render to. Edit the fairway's own copy. -->\n")


def entries(text: str) -> list[str]:
    """One string per `## ` entry, with whatever preamble the file has dropped."""
    return [found.group(0).rstrip() + "\n" for found in ENTRY.finditer(text)]


def ordered(parts: list[str]) -> list[str]:
    """Every entry, by the instant it records. Stable, so two entries of one instant keep their file's order."""
    return sorted(parts, key=lambda part: (WHEN.search(part) is None, (WHEN.search(part) or [None, ""])[1]))


def sources(name: str) -> list[Path]:
    if not FAIRWAYS.is_dir():
        return []
    return sorted([*FAIRWAYS.glob(f"*/{name}"), *FAIRWAYS.glob(f"*/{feature()}/{name}")])


def feature() -> str:
    """The feature in flight: the one directory under `specs/` with a slice record."""
    found = sorted(path.name for path in SPECS.glob("*/") if (path / "slices").is_dir()) if SPECS.is_dir() else []
    return found[0] if found else ""


def rendered(name: str) -> str:
    """What the feature-level file should hold, from every fairway's own copy."""
    parts: list[str] = []
    for path in sources(name):
        parts.extend(entries(path.read_text(encoding="utf-8")))
    return BANNER.format(name=name) + "\n" + "\n".join(ordered(parts))


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


def held(where: str) -> tuple[dict[str, str], str]:
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
    where = feature()
    if not where:
        print("render-fairways: no feature with a slice record yet; nothing to fold")
        return 0
    drifted = []
    holders, note = held(where)
    split = SPECS / where / SPLIT
    if split.is_file():
        was = split.read_text(encoding="utf-8")
        meant = split_rendered(was, holders)
        if checking:
            if was != meant:
                drifted.append(split.relative_to(ROOT).as_posix())
        elif was != meant:
            split.write_text(meant, encoding="utf-8")
            print(f"render-fairways: {split.relative_to(ROOT).as_posix()}'s held_by from the claim refs")
        if note:
            print(note)
    for name in FOLDED:
        if not sources(name):
            continue
        path = SPECS / where / name
        meant = rendered(name)
        if checking:
            if not path.is_file() or path.read_text(encoding="utf-8") != meant:
                drifted.append(path.relative_to(ROOT).as_posix())
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(meant, encoding="utf-8")
        print(f"render-fairways: {path.relative_to(ROOT).as_posix()} from {len(sources(name))} fairway(s)")
    if drifted:
        print("render-fairways: a rendered file is not what its sources render to\n", file=sys.stderr)
        for path in drifted:
            print(f"  {path}: edited by hand, or a fairway's copy changed since it was folded"
                  + (f". {SPLIT}'s held_by is the claim refs and no hand writes it" if path.endswith(SPLIT)
                     else ""), file=sys.stderr)
        print("\nRun: make decisions", file=sys.stderr)
        return 1
    if checking:
        print(f"render-fairways: the feature-level files are what fairways/*/ render to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

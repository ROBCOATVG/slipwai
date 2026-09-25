#!/usr/bin/env python3
"""Hold `/cruise`'s record to its shape: every decision the run took, and every demo it ran, readable and true.

A run with nobody at the wheel is trusted through what it wrote down. `specs/<feature>/decisions.md` is the one
place every product decision the machine took can be read and overturned, and `specs/<feature>/slices/<id>/
demo-log.md` is what a person reads to trust an acceptance the machine gave. Both are append-only entries in a
fixed shape — `commands/cruise.md` shows it, and `.specify/product-owner.md` repeats it — and this is the
gate on that shape: an entry with a field missing is a decision nobody can audit, a `Written to` path that is
not in the tree is a decision that was never applied, and evidence that does not exist is no evidence.

What is held, one finding per line (the adversary log's row per finished slice included, because `/adversary` says
an unwritten row is a pass that has to be run again, and until now nothing noticed one):

- a decision entry is `## D<n> — <question>` followed by the fixed fields in order: **Stage** (with Slice, When,
  Iteration), **Question**, **Options**, **Decision**, **Why**, **Decided by**, **Confidence** (with Would
  reverse if), **Written to**, **Status**;
- entries are numbered contiguously from `D1`, in order;
- **Decided by** is `host (stage recommendation)`, `host (standing decision D<m>)`, `drive-skipper (<model>)`,
  `drive-bosun` — with or without its `(<model>)` — or `human`; **Status** is `standing`, `overridden by D<m>` or `overridden by human <date>`;
- every **Written to** path exists in the repository, and a path still carrying `<placeholders>` is a finding;
- a demo entry is `## <instant> — <verdict> · iteration <n> · drive-hand (<model>)`, its verdict one of
  `accepted`, `behaviour`, `implementation`, followed by **Started with**, **Driven through**, **Examples**,
  **Evidence**, **Feedback**; every **Evidence** path exists, beside the log or from the root, or is `none`;
- every slice the ladder calls done — a row in `specs/<feature>/slices/README.md`, or `status: implemented` in
  `docs/event-model/model.yaml` — has a `## <slice-id> · …` row in `specs/<feature>/adversary-log.md`: the attack,
  or the recorded skip, that `/adversary` writes after every acceptance. The model is the whole project's, so a
  slice in it counts for the feature its `spec` or `gwt` path is under, or, naming none, the one holding
  `slices/<id>/`; an implemented slice no feature holds is noted, not charged to every feature.

`python3 scripts/check-decisions.py --adversary-baseline` is for a project that migrated across that last rule: it
writes, once, a `## <id> · predates the adversary gate · <date>` row for every done slice without one, which the gate accepts
and which says the slice was never attacked. A second baseline is refused.

A project with no record anywhere passes and says so: the gate runs in `make verify` from the first commit.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
SPECS = ROOT / "specs"
DECISIONS = "decisions.md"
DEMO_LOG = "demo-log.md"
ADVERSARY_LOG = "adversary-log.md"
# The fields of one decision entry, in order, as the bold label each line opens with.
DECISION_FIELDS = ("Stage", "Question", "Options", "Decision", "Why", "Decided by", "Confidence", "Written to",
                   "Status")
DEMO_FIELDS = ("Started with", "Driven through", "Examples", "Evidence", "Feedback")
VERDICTS = ("accepted", "behaviour", "implementation")
DECISION_HEADING = re.compile(r"^## D(\d+) — (.+)$")
DEMO_HEADING = re.compile(r"^## (\S+) — (\w+) · iteration (\d+) · drive-hand \((.+)\)$")
# The bosun's entries name the type alone or with the model, because the command tells it `Decided by: drive-bosun`
# and the skipper's habit of naming its model is one it may share.
DECIDED_BY = re.compile(r"^(host \(stage recommendation\)|host \(standing decision D\d+\)|drive-skipper \(.+\)|"
                        r"drive-bosun( \(.+\))?|human)$")
STATUS = re.compile(r"^(standing|overridden by D\d+|overridden by human \S+)$")
FIELD = re.compile(r"^- \*\*([^*]+):\*\* ?(.*)$")
PLACEHOLDER = re.compile(r"<[^>]*>")


Entry = tuple[int, "re.Match[str] | None", dict[str, str]]


def entries(text: str, heading: re.Pattern[str]) -> list[Entry]:
    """Each entry as (line number, its heading match or None for a heading in the wrong shape, its fields as
    first label → the rest of the line)."""
    found: list[Entry] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            found.append((number, heading.match(line), {}))
        elif found and (field := FIELD.match(line)):
            label = field.group(1).split(":")[0].strip()
            found[-1][2].setdefault(label, field.group(2).strip())
    return found


def paths_of(value: str) -> list[str]:
    """The paths a `Written to` or `Evidence` line names: backticked, or comma-separated bare."""
    quoted = re.findall(r"`([^`]+)`", value)
    if quoted:
        return quoted
    return [part.strip() for part in value.split(",") if part.strip()]


def path_findings(where: str, label: str, value: str, base: Path) -> list[str]:
    findings = []
    for path in paths_of(value):
        if PLACEHOLDER.search(path):
            findings.append(f"{where}: {label} still carries a placeholder: {path}")
        elif not (base / path).exists() and not (ROOT / path).exists():
            findings.append(f"{where}: {label} names `{path}`, which is not in the tree")
    return findings


def check_decisions(path: Path) -> list[str]:
    relative = path.relative_to(ROOT).as_posix()
    findings: list[str] = []
    expected = 1
    for line, heading, fields in entries(path.read_text(), DECISION_HEADING):
        where = f"{relative}:{line}"
        if heading is None:
            findings.append(f"{where}: a heading that is not `## D<n> — <question>`")
            continue
        number = int(heading.group(1))
        if number != expected:
            findings.append(f"{where}: D{number} where D{expected} was expected — entries are numbered contiguously")
        expected = number + 1
        missing = [field for field in DECISION_FIELDS if field not in fields]
        if missing:
            findings.append(f"{where}: D{number} is missing {', '.join(f'**{field}:**' for field in missing)}")
            continue
        listed = [label for label in fields if label in DECISION_FIELDS]
        if listed != list(DECISION_FIELDS):
            findings.append(f"{where}: D{number}'s fields are out of order; the shape is {', '.join(DECISION_FIELDS)}")
        if not DECIDED_BY.match(fields["Decided by"]):
            findings.append(f"{where}: D{number} `Decided by` is {fields['Decided by']!r}; it is host (stage "
                            "recommendation), host (standing decision D<m>), drive-skipper (<model>), drive-bosun "
                            "or human")
        if not STATUS.match(fields["Status"]):
            findings.append(f"{where}: D{number} `Status` is {fields['Status']!r}; it is standing, overridden by "
                            "D<m> or overridden by human <date>")
        findings += path_findings(where, f"D{number} `Written to`", fields["Written to"], ROOT)
    return findings


def check_demo_log(path: Path) -> list[str]:
    relative = path.relative_to(ROOT).as_posix()
    findings: list[str] = []
    for line, heading, fields in entries(path.read_text(), DEMO_HEADING):
        where = f"{relative}:{line}"
        if heading is None:
            findings.append(f"{where}: a heading that is not `## <instant> — <verdict> · iteration <n> · drive-hand (<model>)`")
            continue
        verdict = heading.group(2)
        if verdict not in VERDICTS:
            findings.append(f"{where}: verdict {verdict!r} is not one of {', '.join(VERDICTS)}")
        missing = [field for field in DEMO_FIELDS if field not in fields]
        if missing:
            findings.append(f"{where}: the {heading.group(1)} demo is missing "
                            f"{', '.join(f'**{field}:**' for field in missing)}")
            continue
        if fields["Evidence"].strip() != "none":
            findings += path_findings(where, "`Evidence`", fields["Evidence"], path.parent)
    return findings


def implemented() -> list[tuple[str, str | None]]:
    """Every slice `docs/event-model/model.yaml` marks `status: implemented`, with the feature it names: the
    `specs/<feature>/` its `spec` or `gwt` path is under, or None where it names none. The model is the whole
    project's, so a slice in it belongs to one feature, not to every feature that asks."""
    model = ROOT / "docs/event-model/model.yaml"
    found: list[tuple[str, str | None]] = []
    if model.is_file():
        for block in re.split(r"^\s*- id:\s*", model.read_text(), flags=re.M)[1:]:
            ident = block.split("\n", 1)[0].strip().strip("'\"")
            if ident and re.search(r"^\s*status:\s*implemented\s*$", block, re.M):
                named = re.search(r"^\s*(?:spec|gwt):\s*['\"]?specs/([^/\s'\"]+)/", block, re.M)
                found.append((ident, named.group(1) if named else None))
    return found


def done_slices(feature: Path) -> set[str]:
    """The slices this feature has finished, as the ladder marks them (`commands/drive.md`, *Ready-set selection*):
    a row in its register at `slices/README.md`, or `status: implemented` in the event model on a slice that names
    this feature, or names none and has its folder at `slices/<id>/` here."""
    done: set[str] = set()
    register = feature / "slices/README.md"
    if register.is_file():
        for line in register.read_text().splitlines():
            if line.strip().startswith("|"):
                first = line.strip().strip("|").split("|")[0].strip().strip("`")
                found = re.match(r"([A-Za-z]+\d+)\b", first)
                if found:
                    done.add(found.group(1))
    for ident, named in implemented():
        if named == feature.name or (named is None and (feature / "slices" / ident).is_dir()):
            done.add(ident)
    return done


def unowned() -> list[str]:
    """Implemented slices no feature holds: the model names no feature for them and no `specs/*/slices/<id>/`
    exists. Not charged to any feature — said, so the model can be given its `spec` or the id corrected."""
    features = [path for path in (ROOT / "specs").iterdir() if path.is_dir()] if (ROOT / "specs").is_dir() else []
    return sorted(ident for ident, named in implemented()
                  if named is None and not any((feature / "slices" / ident).is_dir() for feature in features))


def check_adversary_rows() -> list[str]:
    """A finished slice with no row in the adversary log was never attacked and never recorded as skipped."""
    findings: list[str] = []
    for feature in sorted(SPECS.iterdir()) if SPECS.is_dir() else []:
        done = done_slices(feature) if (feature / "slices").is_dir() else set()
        if not done:
            continue
        log = feature / ADVERSARY_LOG
        rows = set(re.findall(r"^## (\S+) · ", log.read_text(), re.M)) if log.is_file() else set()
        for ident in sorted(done - rows):
            findings.append(f"{log.relative_to(ROOT).as_posix()}: no row for {ident}, which is done — `/adversary` runs "
                            "after every acceptance and records the attack or the skip; an unwritten row is a pass "
                            "that has to be run again")
    return findings


PREDATES = "predates the adversary gate"


def baseline() -> int:
    """Write, once, a row for every done slice the adversary log lacks, saying it was finished before this gate held
    finished slices to the log — which is true, and which no later slice may cite as an attack. For a project that
    migrated across the gate, whose history cannot be attacked honestly after the fact; refused where any log
    already carries a baseline row, so it is the done set at one moment and not a way past the gate afterwards."""
    logs = sorted(SPECS.glob(f"*/{ADVERSARY_LOG}")) if SPECS.is_dir() else []
    taken = [log for log in logs if f"· {PREDATES}" in log.read_text()]
    if taken:
        print(f"check-decisions: a baseline was already taken ({taken[0].relative_to(ROOT).as_posix()}); a slice "
              "finished since is held to a row `/adversary` writes", file=sys.stderr)
        return 1
    written = 0
    today = date.today().isoformat()
    for feature in sorted(SPECS.iterdir()) if SPECS.is_dir() else []:
        if not (feature / "slices").is_dir():
            continue
        log = feature / ADVERSARY_LOG
        text = log.read_text() if log.is_file() else f"# Adversary log — {feature.name}\n"
        missing = sorted(done_slices(feature) - set(re.findall(r"^## (\S+) · ", text, re.M)))
        if not missing:
            continue
        rows = "".join(f"\n## {ident} · {PREDATES} · {today}\n\nFinished before `check-decisions` held every done "
                       "slice to a row here. Never attacked by `/adversary`, so no slice may cite this row as "
                       "coverage.\n" for ident in missing)
        log.write_text(text.rstrip("\n") + "\n" + rows)
        written += len(missing)
        print(f"check-decisions: {log.relative_to(ROOT).as_posix()}: {len(missing)} baseline row(s)")
    print(f"check-decisions: baselined {written} done slice(s)" if written
          else "check-decisions: every done slice already has a row — nothing to baseline")
    return 0


def main() -> int:
    if sys.argv[1:] == ["--adversary-baseline"]:
        return baseline()
    for ident in unowned():
        print(f"check-decisions: note: {ident} is implemented in docs/event-model/model.yaml but names no feature "
              "and has no specs/*/slices/ folder, so no adversary log is asked for it")
    decisions = sorted(SPECS.glob(f"*/{DECISIONS}")) if SPECS.is_dir() else []
    logs = sorted(SPECS.glob(f"*/slices/*/{DEMO_LOG}")) if SPECS.is_dir() else []
    findings: list[str] = check_adversary_rows()
    if not decisions and not logs and not findings:
        print("check-decisions: no decisions.md or demo-log.md under specs/ — nothing recorded yet")
        return 0
    for path in decisions:
        findings += check_decisions(path)
    for path in logs:
        findings += check_demo_log(path)
    if findings:
        print("check-decisions: the record is not in the shape commands/cruise.md shows\n", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print(file=sys.stderr)
        return 1
    counted = sum(len(entries(p.read_text(), DECISION_HEADING)) for p in decisions)
    demos = sum(len(entries(p.read_text(), DEMO_HEADING)) for p in logs)
    print(f"check-decisions: {counted} decision(s) in {len(decisions)} file(s), {demos} demo(s) in {len(logs)} log(s), "
          "every field present and every path in the tree, every done slice in the adversary log")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as error:
        print(f"check-decisions failed: {error}", file=sys.stderr)
        sys.exit(1)

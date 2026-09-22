#!/usr/bin/env python3
"""Hold `/cruise`'s record to its shape: every decision the run took, and every demo it ran, readable and true.

A run with nobody at the wheel is trusted through what it wrote down. `specs/<feature>/decisions.md` is the one
place every product decision the machine took can be read and overturned, and `specs/<feature>/slices/<id>/
demo-log.md` is what a person reads to trust an acceptance the machine gave. Both are append-only entries in a
fixed shape — `commands/cruise.md` shows it, and `.specify/product-owner.md` repeats it — and this is the
gate on that shape: an entry with a field missing is a decision nobody can audit, a `Written to` path that is
not in the tree is a decision that was never applied, and evidence that does not exist is no evidence.

What is held, one finding per line:

- a decision entry is `## D<n> — <question>` followed by the fixed fields in order: **Stage** (with Slice, When,
  Iteration), **Question**, **Options**, **Decision**, **Why**, **Decided by**, **Confidence** (with Would
  reverse if), **Written to**, **Status**;
- entries are numbered contiguously from `D1`, in order;
- **Decided by** is `host (stage recommendation)`, `host (standing decision D<m>)`, `drive-skipper (<model>)`
  or `human`; **Status** is `standing`, `overridden by D<m>` or `overridden by human <date>`;
- every **Written to** path exists in the repository, and a path still carrying `<placeholders>` is a finding;
- a demo entry is `## <instant> — <verdict> · iteration <n> · drive-hand (<model>)`, its verdict one of
  `accepted`, `behaviour`, `implementation`, followed by **Started with**, **Driven through**, **Examples**,
  **Evidence**, **Feedback**; every **Evidence** path exists, beside the log or from the root, or is `none`.

A project with no record anywhere passes and says so: the gate runs in `make verify` from the first commit.
"""

from __future__ import annotations

import re
import sys
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
# The fields of one decision entry, in order, as the bold label each line opens with.
DECISION_FIELDS = ("Stage", "Question", "Options", "Decision", "Why", "Decided by", "Confidence", "Written to",
                   "Status")
DEMO_FIELDS = ("Started with", "Driven through", "Examples", "Evidence", "Feedback")
VERDICTS = ("accepted", "behaviour", "implementation")
DECISION_HEADING = re.compile(r"^## D(\d+) — (.+)$")
DEMO_HEADING = re.compile(r"^## (\S+) — (\w+) · iteration (\d+) · drive-hand \((.+)\)$")
DECIDED_BY = re.compile(r"^(host \(stage recommendation\)|host \(standing decision D\d+\)|drive-skipper \(.+\)|human)$")
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
                            "recommendation), host (standing decision D<m>), drive-skipper (<model>) or human")
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


def main() -> int:
    decisions = sorted(SPECS.glob(f"*/{DECISIONS}")) if SPECS.is_dir() else []
    logs = sorted(SPECS.glob(f"*/slices/*/{DEMO_LOG}")) if SPECS.is_dir() else []
    if not decisions and not logs:
        print("check-decisions: no decisions.md or demo-log.md under specs/ — nothing recorded yet")
        return 0
    findings: list[str] = []
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
          "every field present and every path in the tree")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as error:
        print(f"check-decisions failed: {error}", file=sys.stderr)
        sys.exit(1)

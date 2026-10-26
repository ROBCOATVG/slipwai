#!/usr/bin/env python3
"""Hold the convergence map to the tree: fail a row that claims a rung the repository contradicts, and a page
that no longer matches the record.

    python3 scripts/check-convergence.py

`project.json`'s `convergence` rows say where an adopted repository stands on each ladder (brownfield adoption). Most rungs only a person can establish, and those stand as written. What the tree can contradict
it does: a constitution that is still the template cannot be `ratified`; a test suite the ratchet quarantines
cannot be `tests-pass`; a repository whose release path is `manual` is not on `pipeline`; an application whose
role is not established is not `named`. An `unrecorded` row passes with a line saying so — it is a question, not
a gap. A page rendered from other rows than the record now holds is stale, and fails: `/survey` regenerates it.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[1]


SCRIPT = Path(__file__).resolve()
ROOT = project_root(SCRIPT)
DELIVERY = SCRIPT.parents[1]
PAGE = DELIVERY / "docs/convergence.md"
BASELINE = DELIVERY / "baseline.json"
CONSTITUTION = ROOT / ".specify/memory/constitution.md"
PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_]{2,}[^\]]*\]")
# A whole line, as `slipwai.strategy` reads it; a sentence mentioning the `Strategy:` line is not the line.
ADR_STRATEGY = re.compile(r"^\W*strategy\W*:\W*([a-z-]+)\W*$", re.IGNORECASE | re.MULTILINE)
STRATEGIES = ("leave-it", "in-place", "strangler-fig", "rewrite")
# What a strategy was called before the axis was `strategy`: an ADR accepted under the older spelling still
# decides, and the record is written under the current name by the next `/survey`.
OLD_STRATEGIES = {"modernise-in-place": "in-place", "modular-monolith": "strangler-fig"}
ADR_ACCEPTED = re.compile(r"^## Status\s*\n+\s*Accepted\b", re.MULTILINE)
LEDGER = DELIVERY / "retirement.md"
MARKER = re.compile(r"<!-- convergence: ([0-9a-f]+) -->")
RUNGS = {
    "path-to-production": ("unknown", "manual", "scripted", "pipeline", "one-path", "pipeline-decides"),
    "integration": ("unknown", "branches", "trunk", "continuous"),
    "safety-net": ("none", "tests-exist", "tests-pass", "fast", "pinned", "mutation-measured"),
    "structure": ("as-found", "named", "laid-out", "hexagonal", "typed"),
    "platform": ("unknown", "inventoried", "supported", "audited"),
    "constitution": ("template", "ratified", "in-full"),
    "data": ("open", "recorded", "settled"),
    "infrastructure": ("open", "recorded", "settled"),
    "release-mode": ("unrecorded", "recorded", "confirmed"),
    "strategy": ("open", "why-recorded", "recommended", "decided", "done"),
}


def caps(document: dict) -> dict[str, tuple[str, str]]:
    """The highest rung the tree allows each axis, with the fact that caps it — only where the tree can say."""
    found: dict[str, tuple[str, str]] = {}
    mode = document.get("releaseMode")
    if mode not in ("open", "keystone", "flagged", "promoted"):
        found["release-mode"] = ("unrecorded", "no valid releaseMode is recorded; confirm the mode in project.json")
    elif not any(row.get("axis") == "release-mode" and row.get("provenance") == "confirmed"
                 for row in (document.get("convergence") or [])):
        found["release-mode"] = ("recorded", "a person has not confirmed the release mode")
    release = (document.get("release") or {}).get("path", "unknown")
    if release in ("unknown", "manual", "scripted"):
        found["path-to-production"] = (release, f"release.path is `{release}`")
    wrapped = [r for r in (document.get("deployables") or {}).values() if r.get("generated") is False]
    if wrapped:
        if any(r.get("kind") == "application" for r in wrapped):
            found["structure"] = ("as-found", "an application's role is not established (`kind: application`)")
        elif not all(r.get("path", "").startswith("apps/") for r in wrapped):
            found["structure"] = ("named", "not every application lives under apps/")
        elif not all(r.get("layout") == "hexagonal" for r in wrapped):
            found["structure"] = ("laid-out", "not every application declares the hexagonal layout")
        elif not all((r.get("commands") or {}).get("typecheck") for r in wrapped):
            found["structure"] = ("hexagonal", "not every application records a typecheck command")
        if not any((r.get("commands") or {}).get("test") for r in wrapped):
            found["safety-net"] = ("none", "no application records a test command")
        # What the applications run on, as `/survey` dated it: a product past its end of life, or one the table does
        # not know, caps the row; a missing audit command caps it below `audited`. A person who knows better — a
        # vendor's paid support — records the row with `confirmed` provenance and the terms as evidence, and this
        # still says what the tree and the table say.
        products = [p for p in ((document.get("platform") or {}).get("products") or []) if isinstance(p, dict)]
        if not products:
            found["platform"] = ("unknown", "no runtime pin, framework version or image was dated by the survey")
        else:
            behind = [f"{p.get('title')} {p.get('version')}" for p in products
                      if p.get("status") in ("end-of-life", "unknown")]
            # An Ant build declares nothing a tool can audit: its jars are committed. The floor under the ladder is
            # a build that does (`docs/change-strategy.md`), and the programme's first step is to move there.
            ant = [r.get("name") for r in wrapped if (r.get("toolchain") or {}).get("ecosystem") == "ant"]
            if behind and (document.get("platform") or {}).get("provenance") != "confirmed":
                found["platform"] = ("inventoried",
                                     f"{', '.join(behind)} is out of support or not in the support table")
            elif ant:
                found["platform"] = ("inventoried", f"{', '.join(map(str, ant))} builds with Ant, whose committed jars "
                                                    "nothing can audit — Maven or Gradle first")
            elif not all((r.get("commands") or {}).get("audit") for r in wrapped):
                found["platform"] = ("supported", "not every application records an audit command")
    if BASELINE.is_file():
        try:
            baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        except ValueError:
            baseline = {}
        red = []
        for name, targets in baseline.items():
            test = targets.get("test") or {}
            if test.get("exit"):
                # The runner's own failure names are findings (`test: <name>`), so the count is of failing tests
                # where the output named them, and of nothing where it did not.
                failing = sum(1 for finding in test.get("findings") or [] if str(finding).startswith("test: "))
                red.append(f"{name} ({failing} failing)" if failing else name)
        if red and "safety-net" not in found:
            found["safety-net"] = ("tests-exist", f"the ratchet quarantines the test suite of {', '.join(red)}")
    if not CONSTITUTION.is_file() or PLACEHOLDER.search(CONSTITUTION.read_text(errors="replace", encoding="utf-8")):
        found["constitution"] = ("template", "the constitution is missing or still carries the template's placeholders")
    if not document.get("why"):
        found["strategy"] = ("open", "no `why` is recorded")
    else:
        decided = decided_strategy()
        if decided is None:
            found["strategy"] = ("recommended", "no accepted ADR under docs/adr/ carries a `Strategy:` line")
        elif decided != "leave-it" and not ledger_finished():
            found["strategy"] = ("decided", f"the ADR decides `{decided}` and the retirement ledger does not "
                                                 "read *removed* throughout")
    return found


def decided_strategy() -> str | None:
    """The strategy the highest-numbered accepted ADR names, or None."""
    decided = None
    for path in sorted((DELIVERY / "docs/adr").glob("*.md")):
        text = path.read_text(errors="replace", encoding="utf-8")
        spelled = [match.group(1).lower() for match in ADR_STRATEGY.finditer(text)]
        named = [OLD_STRATEGIES.get(name, name) for name in spelled]
        strategy = next((name for name in named if name in STRATEGIES), None)
        if strategy and ADR_ACCEPTED.search(text):
            decided = strategy
    return decided


#: What a capability passes through, in order. `shadowed` is the evidence `moved` stands on: the new home served
#: reads beside the old one, reconciled, before it served anyone.
STATUSES = ("routed", "shadowed", "moved", "retired", "removed")
#: Why a commit may change the code that was here once a strangler fig or a rewrite is decided — the freeze's
#: own exceptions, and the work the method does to the old code to make it safe to replace.
LEGACY_CHANGE = re.compile(r"^Legacy-change:\s*(security|bugfix|seam|quick-win|build|characterise)\b",
                           re.IGNORECASE | re.MULTILINE)


def ledger_rows() -> tuple[dict[str, list[str]], dict[str, str]]:
    """Every capability's statuses in order, and every transitional piece's last status, from the ledger's two
    tables: capabilities (seven columns) and the transitional pieces the seam needs (five)."""
    capabilities: dict[str, list[str]] = {}
    pieces: dict[str, str] = {}
    for line in (LEDGER.read_text(errors="replace", encoding="utf-8") if LEDGER.is_file() else "").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.strip().startswith("|") or cells[0] in ("Date", "") or cells[0].startswith("-"):
            continue
        if len(cells) == 7:
            capabilities.setdefault(cells[1], []).append(cells[6].strip("*").lower())
        elif len(cells) == 5:
            pieces[cells[1]] = cells[4].strip("*").lower()
    return capabilities, pieces


def ledger_finished() -> bool:
    """Every capability *removed*, and every transitional piece with it: an include left behind is the old home
    still serving."""
    capabilities, pieces = ledger_rows()
    return bool(capabilities) and all(statuses[-1] == "removed" for statuses in capabilities.values()) and all(
        status == "removed" for status in pieces.values())


def ledger_gaps() -> list[str]:
    """A status the ledger does not know, or a capability *moved* with no *shadowed* row before it."""
    capabilities, _ = ledger_rows()
    gaps = []
    for capability, statuses in capabilities.items():
        unknown = [status for status in statuses if status not in STATUSES]
        if unknown:
            gaps.append(f"the ledger gives `{capability}` the status `{unknown[0]}`; it is one of {', '.join(STATUSES)}")
        if "moved" in statuses and "shadowed" not in statuses[:statuses.index("moved")]:
            gaps.append(f"the ledger says `{capability}` moved with no `shadowed` row before it — the new home serves "
                        "reads beside the old one, reconciled, before it serves anyone")
    return gaps


def legacy_changes(document: dict, record: dict) -> list[str]:
    """Commits since the strategy was decided that changed the code that was here without saying why it could."""
    adr = record.get("adr")
    old = [str(r.get("path")) for r in (document.get("deployables") or {}).values()
           if isinstance(r, dict) and r.get("generated") is False and r.get("path") not in (None, ".")]
    if not adr or not old:
        return []
    git = ["git", "-C", str(ROOT)]
    since = subprocess.run([*git, "log", "-1", "--format=%H", "--", adr], capture_output=True, text=True)
    if since.returncode or not since.stdout.strip():
        return []  # a shallow clone, or an ADR nobody committed: nothing to measure from
    log = subprocess.run([*git, "log", f"{since.stdout.strip()}..HEAD", "--format=%h%x1f%s%x1f%B%x1e", "--", *old],
                         capture_output=True, text=True).stdout
    unsaid = [entry.split("\x1f") for entry in log.split("\x1e") if entry.strip()]
    unsaid = [(sha.strip(), subject) for sha, subject, body in unsaid if not LEGACY_CHANGE.search(body)]
    return [f"commit {sha} changed the code that was here ({', '.join(old)}) without a `Legacy-change:` trailer — "
            f"\"{subject}\". Under `{record['decided']}` the old code takes security, bugfix, seam, quick-win, build "
            "and characterise changes only, and says which" for sha, subject in unsaid[:5]]


def strategy_gaps(document: dict) -> list[str]:
    """What the decided strategy refuses before it happens, rather than warns about after: a feature specified
    before its new home exists, the old code changed without saying why, a left system past its review."""
    record = document.get("strategy") or {}
    strategy, lines = record.get("decided"), record.get("lines") or {}
    if not strategy or record.get("missing"):
        return []
    gaps: list[str] = []
    specified = sorted(path.parent.name for path in (ROOT / "specs").glob("*/spec.md"))
    if strategy in ("strangler-fig", "rewrite") and specified:
        place = str(lines.get("New home" if strategy == "strangler-fig" else "Home") or "").split(" ")[0].lower()
        # A generated deployable carries no `generated` key; only the code that was here is marked `false`.
        generated = any(isinstance(r, dict) and r.get("generated") is not False
                        for r in (document.get("deployables") or {}).values())
        if place == "new-repo":
            gaps.append(f"specs/{specified[0]} is specified here, but the rewrite is built in a new repository: the "
                        "constitution and every feature are that project's")
        elif place == "inside" and not (DELIVERY / "docs/module-map.md").is_file():
            gaps.append(f"specs/{specified[0]} is specified before the new home's modules are declared — "
                        f"{(DELIVERY / 'docs/module-map.md').relative_to(ROOT)} first")
        elif place != "inside" and not generated:
            gaps.append(f"specs/{specified[0]} is specified before the new home exists: under `{strategy}` a feature "
                        "is built in the new home, so it is generated first (`slipwai adopt --next` says how)")
    if strategy in ("strangler-fig", "rewrite"):
        gaps += legacy_changes(document, record)
    if strategy == "leave-it":
        due = re.search(r"\d{4}-\d{2}-\d{2}", str(lines.get("Review") or ""))
        if due and datetime.date.fromisoformat(due.group(0)) < datetime.date.today():
            gaps.append(f"the system was left as it is to be reviewed by {due.group(0)}, and that date has passed: "
                        "review it, and record the outcome as a new ADR")
    return gaps + ledger_gaps()


def main() -> int:
    document = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    rows = document.get("convergence")
    if not isinstance(rows, list) or not rows:
        print("check-convergence: no map recorded — adopted before the map existed; `slipwai adopt --refresh` writes "
              "it")
        return 0
    if not PAGE.is_file():
        print(f"check-convergence: {PAGE.relative_to(ROOT)} is missing; /survey (slipwai adopt --refresh) writes it",
              file=sys.stderr)
        return 1
    marker = MARKER.search(PAGE.read_text(encoding="utf-8"))
    expected = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16]
    if marker is None or marker.group(1) != expected:
        print(
            f"check-convergence: {PAGE.relative_to(ROOT)} is stale — project.json's convergence rows changed and the "
            "page was not regenerated; run /survey (slipwai adopt --refresh) and commit both.", file=sys.stderr,
        )
        return 1
    capped = caps(document)
    failures = 0
    for row in rows:
        axis, rung = row.get("axis"), row.get("rung")
        if axis not in RUNGS or rung not in RUNGS[axis]:
            print(f"check-convergence: {axis}: `{rung}` is not a rung this factory knows", file=sys.stderr)
            failures += 1
            continue
        if row.get("provenance") == "unrecorded":
            print(f"  {axis}: `{rung}` — unrecorded: nothing has established it; /sail asks before the first slice")
            continue
        cap = capped.get(axis)
        if cap and RUNGS[axis].index(rung) > RUNGS[axis].index(cap[0]):
            print(
                f"check-convergence: {axis} is recorded at `{rung}` ({row.get('provenance')}), but {cap[1]} — the tree "
                f"allows `{cap[0]}` at most. Establish the rung, or record where it stands.", file=sys.stderr,
            )
            failures += 1
            continue
        mark = "at target" if rung == row.get("target") else f"below `{row.get('target')}`"
        print(f"  {axis}: `{rung}` — {mark}" + (f"; planned as {row['planned']}" if row.get("planned") else ""))
    for gap in strategy_gaps(document):
        print(f"check-convergence: strategy: {gap}", file=sys.stderr)
        failures += 1
    # Said, not failed: a strangler fig decided with nowhere for a capability to move to. The first strangler
    # adoption archived five product slices, all built in the WAR it had decided to strangle, with an empty ledger.
    deployables = document.get("deployables") or {}
    if decided_strategy() == "strangler-fig" and not ledger_finished() and deployables and all(
        (record or {}).get("generated") is False for record in deployables.values()
    ):
        archived = len([path for path in (ROOT / "specs").glob("*/slices/*") if path.is_dir()])
        print(
            f"  strategy: `strangler-fig` is decided, {archived} slice(s) are archived, the retirement ledger "
            "reads *removed* for nothing, and every deployable is one that was here — nothing has moved to a new "
            "home. A product slice under a strangler lands in a new home (`add-service`, then `/strangle`); the "
            "Plan stage of /sail has the rule."
        )
    # Said, not failed: a strategy decided without the lines its playbook cannot start without. The decision is the
    # person's and stands; what follows from it waits on these.
    record = document.get("strategy") or {}
    if record.get("decided") and record.get("missing"):
        print(
            f"  strategy: `{record['decided']}` is decided, and its ADR does not yet say "
            + ", ".join(f"`{name}:`" for name in record["missing"])
            + f" — docs/strategies/{record['decided']}.md, *What the ADR records*, says what each line holds"
        )
    at = sum(1 for r in rows if r.get("rung") == r.get("target"))
    print(f"check-convergence: {at} of {len(rows)} axes at target; the map is {PAGE.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

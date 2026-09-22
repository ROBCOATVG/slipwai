"""What `adopt` writes for a reader: the survey page, with its evidence, and the report the command ends with.

Split from `adopt.py`, which keeps the record and the writing, when the two together passed the module budget.
The report's rule is the interview's: every line says where a fact came from, `init` is always the first next
step, and what was not established is said to be unrecorded rather than filled in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .assets import VERSION
from .convergence import summary
from .harness import name_of
from .layout import Layout
from .origin import Adoption
from .programme import expired, phrase, unplaced
from .services import App, wrapped_of
from .survey import Survey
from .wrappers import missing_tools, wrapper_lines


@dataclass(frozen=True)
class Adopted:
    """What `adopt` did, for the report."""

    root: Path
    name: str
    layout: Layout
    apps: list[App]
    adoption: Adoption
    written: list[str]
    appended: list[str]
    settings_written: bool
    # A root `Makefile` written because there was none — the repository's from then on, not in `.written`.
    makefile_written: bool = False
    # Build wrappers written where a Maven or Gradle build had none — theirs too; by application, the paths.
    wrappers: dict[str, list[str]] = field(default_factory=dict)


MAKEFILE = "Makefile"


SETTINGS = ".claude/settings.json"


def survey_page(found: Survey, apps: list[App]) -> str:
    """`<delivery>/survey/survey.md`: what the tree said, with the evidence, as it stood when adopted."""
    roots = "\n".join(
        f"- `{root.path}` — {root.found.ecosystem}, {root.found.language}, from `{root.found.evidence}`"
        + (
            f", {root.found.toolchain['kind']} {root.found.toolchain['version']}"
            if root.found.toolchain.get("version") else ""
        )
        + (f", packaged as {root.found.packaging}" if root.found.packaging else "")
        + (f"; a {root.role} by `{root.role_evidence}`" if root.role else "; what it is for, nothing here says")
        for root in found.roots
    ) or "- none found"
    listed = lambda pairs: "\n".join(f"- {a} — `{b}`" for a, b in pairs) or "- none found"  # noqa: E731
    forge, forge_evidence = found.forge
    forge_source = forge_evidence if forge_evidence.startswith(("remote", "no ")) else f"`{forge_evidence}`"
    release = f"`{found.release_path}`" if found.release_path else (
        "`unknown` — nothing in the tree says, so it stays unrecorded until somebody does"
    )
    return f"""# Survey

Written by `slipwai adopt` ({VERSION}) from the tree as it was; `/survey` refreshes it. Every line names the
file that said so. Experimental: see `../docs/adoption.md`.

## Builds

{roots}

Wrapped as: {', '.join(f'`{app.name}` (`{app.path}`)' for app in wrapped_of(apps)) or 'nothing'}.

## Continuous integration

{chr(10).join(f'- `{path}`' for path in found.ci) or '- none found'}

Proposed forge: `{forge}`, from {forge_source}.

## How a change reaches production

{listed(found.release_evidence)}

Proposed: {release}.

## Containers

{chr(10).join(f'- `{path}`' for path in found.containers) or '- none found'}

## Infrastructure as code

{listed(found.infrastructure)}

Proposed home: `{found.infrastructure_home}`.

## Database

Schema tools:

{listed(found.schema_tools)}

Drivers in dependency manifests:

{listed(found.drivers)}

Proposed schema home: `{found.schema_home}`.

## Also here

- root `Makefile`: {'yes' if found.makefile else 'no'}
- `README`: {'yes' if found.readme else 'no'}

## Big issues that are quick wins

{quick_wins_table(found.quick_wins)}
"""


def quick_wins_table(findings: tuple[dict, ...]) -> str:
    """What is cheap to fix and expensive to leave, with the file that shows it and the fix — never a value. The list
    is read from the tree on every `/survey`, so a finding fixed disappears here rather than being ticked off."""
    if not findings:
        return ("None the survey can see: no credential written in a file it reads, no IDE or build output tracked, no "
                "dependency source over plain HTTP, no missing lockfile, no archive under version control.")
    rows = "\n".join(f"| `{f['kind']}` | `{f['where']}` | {f['what']} | {f['fix']} |" for f in findings)
    return (
        f"Each is a proposal, not a change the factory made; `/drive` offers them before the map's rows while any "
        f"remain, a secret first, and `/survey` drops each as the tree stops showing it.\n\n"
        f"| Kind | Where | What | Fix |\n|---|---|---|---|\n{rows}"
    )


def report(done: Adopted) -> str:
    """What was written, what it forfeits, and the next steps in order — the first line says experimental, and the
    first step is always `init`, as it is in a generated project's README: the agent before the gate."""
    wrapped = wrapped_of(done.apps)
    lines = [
        f"adopted {done.name} with slipwai {VERSION} — experimental: this path is new, its shape may change in a "
        "MINOR, and what surprised you belongs on the public issue tracker",
        f"{len(done.written)} files written under {done.layout.delivery}/ and beside it; nothing of the "
        "repository's own was written over. One commit by the factory; `git reset --hard HEAD^` undoes all of it.",
    ]
    for app in wrapped:
        recorded = sum(1 for command in (app.commands or {}).values() if command)
        what = f"a {app.kind}" if app.kind != "application" else "what it is for is not recorded"
        lines.append(
            f"  {app.name}: {app.path} ({app.language}; {what}), {recorded} of {len(app.commands or {})} targets "
            "have a command; the rest are written no's"
        )
    # Nothing a person said stands behind an application every one of whose facts is still the survey's own
    # reading, which is what `--yes` leaves. Said once, plainly, rather than left to be inferred from the word
    # `detected` in a file nobody opens: the whole point of the candidate state is that a record says whether
    # somebody looked, and a record that says nobody did has to be as readable as one that says somebody did.
    unlooked = [app for app in wrapped if set(app.provenance.values()) <= {"detected", "unrecorded"}]
    if unlooked and len(unlooked) == len(wrapped):
        lines.append(
            f"  Nobody has looked at {'either' if len(unlooked) == 2 else 'any'} of these: every fact above is "
            "the survey's own reading, recorded `detected`. /ground asks about each, and `/survey` refreshes "
            "what stays the tree's word."
            if len(unlooked) > 1 else
            "  Nobody has looked at it: every fact above is the survey's own reading, recorded `detected`. "
            "/ground asks, and `/survey` refreshes what stays the tree's word."
        )
    candidates = done.adoption.candidates or []
    if candidates:
        one = len(candidates) == 1
        lines.append(
            f"  {len(candidates)} buildable director{'y' if one else 'ies'}, "
            + ("which is not recorded as an application yet" if one else "none of them recorded as an "
               "application yet")
            + " — what each is, what it is called and what it owns are questions the code answers:"
        )
        for row in candidates:
            answered = sum(1 for command in (row.get("commands") or {}).values() if command)
            lines.append(
                f"    {row['path']} ({row['language']}, from {row['evidence']}), "
                f"{answered} of {len(row.get('commands') or {})} targets have a command"
            )
        lines.append(
            "  Until one is confirmed, `verify` refuses rather than passing over nothing: /ground asks about "
            "each with the code in front of it, and `slipwai adopt --confirm <name>` records the answer."
        )
    elif not wrapped:
        lines.append("  no buildable directory was found; the gate is the method's own checks alone")
    lines += ci_lines(done.adoption, done.layout)
    at, below, unrecorded = summary(done.adoption.convergence)
    lines.append(
        f"Map: {done.layout.delivery}/docs/convergence.md — {at} of {len(done.adoption.convergence)} axes at a "
        f"generated project's rung, {below} below, {unrecorded} unrecorded; verify holds it, /survey refreshes it."
    )
    platform = done.adoption.platform or {}
    behind, unknown = expired(platform), unplaced(platform)
    if behind:
        lines.append(
            f"Platform: out of support — {'; '.join(phrase(p) for p in behind)}. The way up for each is in "
            f"{done.layout.delivery}/survey/structure.md (*What it runs on*) and leads the recommendation's `before` "
            "list; offered as method slices, never bumped by the factory."
        )
    elif platform.get("products"):
        missing = ", ".join(p["title"] + " " + p["version"] for p in unknown)
        lines.append(f"Platform: {len(platform['products'])} product(s) read, in support on {platform.get('dated')}"
                     + (f"; not in the support table: {missing}" if missing else "") + ".")
    else:
        lines.append("Platform: nothing the survey can date — no runtime pin, framework version or image; /ground "
                     "asks.")
    wins = (done.adoption.survey or {}).get("quickWins") or []
    if wins:
        shown = "; ".join(f"{w['kind']} at {w['where']}" for w in wins[:3])
        lines.append(
            f"Quick wins: {len(wins)} big issue(s) that are cheap to fix — {shown}"
            + (f"; and {len(wins) - 3} more" if len(wins) > 3 else "")
            + f". Each with its fix in {done.layout.delivery}/survey/survey.md; /drive offers them first."
        )
    record = done.adoption.strategy or {}
    if record:
        lines.append(
            f"Strategy: recommended `{record.get('recommended')}` — {(record.get('because') or ['—'])[0]}. "
            f"Decided: {record.get('decided') or 'nothing yet; an accepted ADR with a Strategy line decides, '}"
            f"{'' if record.get('decided') else 'leave-it included'}."
        )
    appended = [name for name in done.appended if name != MAKEFILE]
    if appended:
        lines.append(f"Appended a marked block to {' and '.join(appended)}; edit around it, not inside it.")
    if done.settings_written:
        lines.append(f"Wrote {SETTINGS}, since there was none.")
    else:
        lines.append(f"{SETTINGS} was already here and is untouched.")
    if done.makefile_written:
        lines.append(
            f"Wrote {MAKEFILE} with `-include {done.layout.delivery}/Makefile`, since there was none: "
            "`make verify` is one word."
        )
    lines += wrapper_lines(done.wrappers, wrapped)
    lines += missing_tools(wrapped, done.layout)
    verify = "make" if done.makefile_written else done.layout.make
    init = f"./{done.layout.delivery}/init"
    named = recorded_agent(done)
    lines += [
        "",
        f"Next: {init} — installs Spec Kit and " + (
            f"projects the skills and commands into {name_of(named)}, which this record already "
            f"names, so it asks nothing ({init} --integration <agent> changes it)"
            if named
            else f"asks which coding agent gets the skills and commands (or name it: {init} --integration claude)"
        ) + ". Add --extension codegraph to index the code for that agent.",
        "Then: /ground, in the agent — it asks what the tree could not say" + (
            ", starting with which of the directories above is an application, what it is called and what it "
            "owns; then one row of the map at a time"
            if done.adoption.candidates
            else ", one row of the map at a time"
        ) + ", and records each answer with its provenance; what --yes left unrecorded is settled there.",
        f"Then: {verify} verify — the gate" + (
            ", once a candidate above has been confirmed: it refuses while nothing is, because a gate with "
            "nothing to hold has not been given its subject yet"
            if done.adoption.candidates else ""
        ) + ". Its first run records the lint and typecheck findings that are there as "
        f"the baseline; commit {done.layout.delivery}/baseline.json with what init wrote. A test suite that is red "
        "stops that run and says so: read the failures, then `make ratchet-tighten` quarantines it deliberately.",
        *([] if done.makefile_written else [
            f"Then: add `-include {done.layout.delivery}/Makefile` to the root Makefile, and `make verify` is one word"
        ]),
        f"Read {done.layout.delivery}/docs/adoption.md — what was wrapped, what that forfeits, and where each fact "
        f"came from — and {done.layout.delivery}/docs/convergence.md, where this repository stands and what is next; "
        f"{done.layout.delivery}/survey/survey.md is the survey with its evidence.",
        "This list scrolls away, and the sequence it names takes longer than one sitting: `slipwai adopt --next` "
        "says where you are in it, read off the tree rather than remembered.",
    ]
    return "\n".join(lines)


def recorded_agent(done: Adopted) -> str | None:
    """The harness the record names, or None where the question is still `./init`'s to ask."""
    harness = (done.adoption.agent or {}).get("harness")
    return harness if isinstance(harness, str) and harness else None


def ci_lines(adoption: Adoption, layout: Layout) -> list[str]:
    """What the report says about the gate's CI configuration and the release path: which forge was recorded, what
    was written for it — or that nothing was, and what to run instead — and how a change reaches production."""
    ci, release = adoption.ci, adoption.release
    forge, gate = ci.get("forge", "none"), ci.get("gate")
    said = {
        "github": f"CI: {gate} runs the gate on GitHub Actions ({ci.get('provenance')}, from {ci.get('evidence')}).",
        "gitea": f"CI: {gate} runs the gate on Gitea Actions ({ci.get('provenance')}, from {ci.get('evidence')}).",
        "gitlab": f"CI: {gate} is a GitLab job; add `include: [local: {gate}]` to .gitlab-ci.yml and it runs the gate.",
        "other": f"CI: no configuration written — the forge is `other` ({ci.get('evidence')}); have your CI "
        f"run `{layout.make} verify`.",
        "none": f"CI: none found in this repository, so nothing was written; when there is one, have it run "
        f"`{layout.make} verify`.",
    }[forge]
    path = release.get("path", "unknown")
    evidence = ", ".join(release.get("evidence") or [])
    how = {
        "pipeline": f"a pipeline deploys ({evidence})",
        "scripted": f"somebody runs a script ({evidence})",
        "manual": "by hand",
        "unknown": "not recorded — nothing in the tree says, and nobody has yet; `--release` or project.json's "
        "`release` is where to say it, and /drive asks before the first slice",
    }[path]
    return [said, f"How a change reaches production: {how} ({release.get('provenance')})."]

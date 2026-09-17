"""What a repository the factory did not make takes from it, and the pages and blocks that explain the adoption.

`scaffold.project_files` assembles the whole of a project as if the factory had made it; this cuts that set
down for one the method is installed around (brownfield adoption; experimental as `AGENTS.md` defines
the word). Three root files are the repository's own and never claimed — `README.md`, `AGENTS.md`,
`.gitignore` — and `.claude/settings.json` is written only where there is none. What the factory owes them is
a marked block, appended once by `adopt` and left alone by `replay`, which regenerates only what is listed in
`<layout.delivery>/.written`: the paths it wrote, so that a newer factory can tell what to replace in a tree
that is mostly not its own. The CI workflow is `verify-delivery.yml`, beside whatever CI the repository runs,
and sets up the toolchains the wrapped applications recorded rather than the ones the catalog knows.
"""
from __future__ import annotations

from ..catalog import CATALOG, families
from ..layout import Layout
from ..origin import Adoption
from ..services import App, wrapped_of
from .adopted_ci import ACTIONS_GATE, delivery_workflow, gitlab_job
from .drive_adoption import adoption_hooks
from .shared_packages import PACKAGES

# The list of every path the factory wrote into an adopted repository, relative to the root. `replay` reads the
# previous one out of the commit it sits on, so what an older factory wrote and a newer one no longer does is
# removed rather than left behind.
WRITTEN = ".written"
# The repository's own files, which an adoption never writes over. The first three take a marked block instead;
# `.claude/settings.json` is written only where the repository has none.
#
# The rest are the root files a repository that already exists has already answered for itself, and answered
# for its own reasons: which Node it is pinned to, how it indents, who it is licensed to, how a vulnerability
# reaches its maintainers, what a pull request into it has to say, and whether anything updates its
# dependencies. Every one of them would be wrong if the factory wrote it — a placeholder licence over a real
# one is the worst of them — and none is something the method needs in order to work.
OWN = (
    "README.md", "AGENTS.md", ".gitignore", ".claude/settings.json", f"{PACKAGES}/.gitkeep",
    ".editorconfig", ".nvmrc", ".python-version", "LICENSE", "SECURITY.md", "renovate.json",
    ".github/PULL_REQUEST_TEMPLATE.md",
)
EXPERIMENTAL = (
    "> **Experimental.** Brownfield adoption is new and will change shape while real repositories teach it what "
    "it got wrong: the files under the delivery directory, the facts `project.json` records and the questions "
    "`adopt` asks may change in a MINOR release, and `slipwai migrate` brings each change here with a note "
    "saying what to do. Every place this reaches you says so until it stops being true. What surprised you — a "
    "detection that was wrong, a gate that went red, a sentence this page should have had — belongs on the "
    "public issue tracker."
)


def adopted_files(files: dict[str, str], apps: list[App], layout: Layout, adoption: Adoption) -> dict[str, str]:
    """The assembled and placed files, cut to what an adopted repository takes, with the list of them. The CI
    configuration is written for the forge the adoption recorded, or not at all — never a GitHub workflow into a
    repository whose CI is somewhere else; a record from before the forge was recorded gets the workflow."""
    kept = {path: content for path, content in files.items() if path not in OWN}
    kept.pop(".github/workflows/verify.yml", None)
    gate = adoption.ci.get("gate") if adoption.ci else ACTIONS_GATE
    if gate == ACTIONS_GATE:
        kept[gate] = delivery_workflow(apps, layout, (adoption.ci or {}).get("branch") or "main")
    elif gate:
        kept[gate] = gitlab_job(apps, layout)
    # Spec Kit reads its hooks at the root whatever the layout, so the file is not relocated; the adoption's own
    # hooks — the map before a specification, the pin before a plan, the map again after converge — go in it.
    kept[".specify/extensions.yml"] = adoption_hooks(kept[".specify/extensions.yml"], apps, layout)
    written = layout.under(WRITTEN)
    kept[written] = "".join(f"{path}\n" for path in sorted([*kept, written]))
    return kept


def unavailable(language: str) -> str:
    """What the factory cannot do for a language it cannot generate, said plainly."""
    if language in families():
        return (
            f"`{language}` is a language this factory generates, so `add-service --language {language}` can put a "
            "generated service beside the existing one, with every axis and gate a generated service has."
        )
    return (
        f"`{language}` is not a language this factory generates, so for this application there is no generated "
        "skeleton, no axis to answer (event store, HTTP transport, identity), no production image, no `aws` "
        "target and no hexagonal import rule — only the gate composed from its recorded commands, and the "
        "skills, commands and documentation, which speak of every language."
    )


def commands_table(app: App) -> str:
    rows = "\n".join(
        f"| `{target}` | {f'`{command}`' if command else '*none recorded — a written no; the target passes and says so*'} |"
        for target, command in (app.commands or {}).items()
    )
    return f"| Target | Command |\n|---|---|\n{rows}\n"


def home_paragraph(what: str, record: dict, key: str) -> str:
    home = record.get(key, "unknown")
    repository = record.get("repository")
    tools = record.get("tools") or record.get("describedBy") or []
    said = {
        "here": "versioned in this repository" + (f" ({', '.join(f'`{t}`' for t in tools)})" if tools else ""),
        "elsewhere": f"owned by another repository{f', `{repository}`' if repository else ''} — a contract between "
        "two repositories, which is what to test at the boundary",
        "unmanaged": "not versioned anywhere this survey could see: applied by hand, by a DBA or a console. The first "
        "step of the data or infrastructure work is a versioned baseline, described before it is imported",
        "none": "not part of this system",
    }.get(home, f"recorded as `{home}`")
    return f"**{what}** is {said} (`{record.get('provenance', 'detected')}`)."


def adoption_page(project_name: str, apps: list[App], adoption: Adoption, layout: Layout) -> str:
    """`docs/adoption.md`: what was wrapped, what that forfeits, where the facts came from, and what is next."""
    wrapped = wrapped_of(apps)
    applications = "\n\n".join(
        f"### `{app.path}` — `{app.name}`, {kind_phrase(app)} in {app.language}"
        + (f" ({app.toolchain.get('ecosystem')}{', ' + app.toolchain['packaging'] if app.toolchain.get('packaging') else ''}"
           f"{', ' + app.toolchain['kind'] + ' ' + app.toolchain['version'] if app.toolchain.get('version') else ''})"
           if app.toolchain else "")
        + (f"\n\n{app.purpose}" if app.purpose else "")
        + f"\n\nProvenance: {', '.join(f'{k} `{v}`' for k, v in app.provenance.items()) or 'none recorded'}.\n\n"
        + commands_table(app) + "\n" + unavailable(app.language)
        for app in wrapped
    ) or "No buildable directory was found, so nothing was wrapped: the gate is the method's own checks alone."
    make = layout.make
    why = f"\n\n**Why:** {adoption.why}\n" if adoption.why else ""
    makefile_step = (
        f"Offer the targets as the repository's own: add `-include {where(layout)}Makefile` to the root `Makefile`,\n"
        "   and `make verify` is one word again."
        if adoption.survey.get("makefile")
        else f"`make verify` is one word: the repository had no `Makefile`, so `adopt` wrote one that includes\n"
        f"   `{where(layout)}Makefile`, in a marked block. Targets of the repository's own go around it."
    )
    return f"""# How the delivery method was installed here

{EXPERIMENTAL}

`{project_name}` existed before this method did. `slipwai adopt` surveyed the tree, proposed what it found, and
wrote the method's material under `{where(layout)}` beside the code — nothing of the repository's own was
written over, and `project.json` records every fact with where it came from: `detected` from the tree,
`confirmed` by the person who accepted it, `overridden` by the person who changed it.{why}{converged_paragraph(adoption)}

## What was wrapped

{applications}

## Where the rest lives

{home_paragraph("The database schema", adoption.database, "schema")}

{home_paragraph("The deployment infrastructure", adoption.infrastructure, "home")}

Neither is something the factory manages here: `adopt` owns no environment and applies nothing. Where either
is `here`, the rule is import or reference — never manage a resource in two places. Where it is `elsewhere`,
the other repository is the contract. Where it is `unmanaged`, the finding is written down and the first step
is named.

## What runs

`{make} verify` is the gate: the method's own checks — agent projections, Spec Kit, the constitution floor,
the import rule over anything the factory generates — and then every wrapped application's recorded commands,
in the order above. A target recorded `null` passes with a line saying so; it is a written no, not a gap to
fill by guessing. `lint` and `typecheck` run through the ratchet (`{where(layout)}scripts/ratchet.py`): the
first local run records the findings that are there into `{where(layout)}baseline.json` — commit it — and
from then on the gate fails only on a finding that is new; `make ratchet-tighten` re-records what is left once
somebody has looked. `test` runs through the same ratchet with one difference: a suite that is red on day one
stops the first run and says so — a red suite is a fact a person reads, never one the gate records behind them —
and `make ratchet-tighten`, once they have, records it as **quarantined**: the gate passes on the state it
recorded and says so every run, until the suite is green and `ratchet-tighten` clears it. A new failure is still
a failure, whether the output names a file at a position or the runner names the test (`--- FAIL: TestX`,
`not ok 3 - adds`, `FAILED tests/test_a.py::test_b`, Surefire's `[ERROR]   ShopTest.adds`). `smoke` is the one
command the gate cannot compose from the eight: the application started and proved to answer, recorded as
`commands.smoke` once `{where(layout)}survey/running.md` says how (`/ground` asks; `null` is a written no with
its reason there). `{make} smoke` runs it, `{make} ci` and the gate's own smoke job run it in CI, and `verify`
never does, since it needs what the application needs. A Maven or Gradle build runs through its wrapper
(`./mvnw`, `./gradlew`): where the repository had none, `adopt` wrote one beside the build file, so the machine
needs a JDK and no Maven or Gradle of its own. Any other recorded command whose tool is not on the machine
running it cannot be baselined — the ratchet fails, names the tool, and records nothing until it is installed or
`project.json` records what this machine does run. A suite recorded as `test-full` is too slow for the gate and
has a target of its own. {ci_paragraph(adoption, layout)}

## How a change reaches production

{release_paragraph(adoption)}

## Next

1. `./{where(layout)}init` — first, as in any project the factory made. It installs Spec Kit and asks which
   coding agent to project the skills and commands into (`./{where(layout)}init --integration claude` names it
   outright; `python3 {where(layout)}scripts/agents/project.py --list` shows every agent it knows).
   `./{where(layout)}init --extension codegraph` indexes the code, which is what makes a legacy codebase safe
   for an agent to work in; the two flags go together in one run.
2. `/ground`, in the agent — the question set the tree could not answer: one row of
   `{where(layout)}docs/convergence.md` at a time, the evidence and the rungs shown first, each answer written
   with `confirmed` provenance; then `/survey` so the pages and the strategy recommendation follow. What
   `adopt` asked in the terminal, or `--yes` left `unrecorded`, is settled here rather than one slice at a time —
   or skip straight to `/drive`, whose Ground stage runs the same questions for the rows a slice touches.
3. `{make} verify` — green on day one is the promise for a linter or type checker that arrived after the
   code, and the first run records the ratchet baseline: commit `{where(layout)}baseline.json` with what `init`
   wrote. A test suite that is red on day one is the one exception: the run stops and says so, and
   `{make} ratchet-tighten` quarantines it once you have read the failures. Anything else not green is the
   repository's own command failing, and `project.json` is where to correct what the survey got wrong.
4. {makefile_step}
5. Read `{where(layout)}docs/convergence.md`: where this repository stands on every ladder a generated project
   sits at the top of, what is planned to move each row, and what nobody has established yet; and
   `{where(layout)}survey/structure.md`, the architecture view — where anything starts, what depends on what,
   where change happens — which says what moves the Structure row and where `/strangle` would cut. Then
   `{where(layout)}docs/getting-started.md` and `{where(layout)}docs/architecture.md`, then `/drive`,
   whose ladder here begins at *Ground* (no map, no principles), pins wrapped code before *Implementation*,
   and holds the map to each slice at *Convergence* before offering the next row as a method slice.
   Three more commands are this adoption's own: `/characterise` pins the current behaviour of the code a slice is about
   to change, at the seam where it can be observed (`{where(layout)}survey/pinned.md` is the ledger) — with
   fakes written in the test tree, never a mocking framework it would have to add — and
   `/survey` runs `slipwai adopt --refresh` to reconcile a fresh survey with what `project.json` records.
   How each application is *run* is written, once proven, in `{where(layout)}survey/running.md` — the
   repository's own file, which the `run-the-app` skill points to and the factory never rewrites.
   When the code is ready to move, `{where(layout)}docs/change-strategy.md` opens with the strategy `why` and
   the map recommend for this repository — *leave it* included — then the three strategies and the order to
   change in; an accepted ADR with a `Strategy:` line is the decision, and `/strangle` moves one capability
   at a time only under a decision that says `strangler-fig`, writing `{where(layout)}retirement.md` as it goes.
6. Merge this adoption alone, before the first slice, and from then on one pull request per slice — a slice's
   after-acceptance commits ride in its own PR. A reviewer can read a slice; nobody reads five at once.
7. Later, `slipwai migrate` brings a newer factory's material here as one merge; the files it wrote are listed
   in `{where(layout)}{WRITTEN}`, and nothing else is ever touched.

Profiles, axes and everything else the factory offers a generated project are described in
`{where(layout)}docs/`; `{', '.join(CATALOG['backends'])}` are the backends it can add beside what is here.
"""


def where(layout: Layout) -> str:
    """The delivery directory as a path prefix: `delivery/`, or nothing at the root."""
    return f"{layout.delivery}/" if layout.moved else ""


def converged_paragraph(adoption: Adoption) -> str:
    record = adoption.converged
    if not record:
        return ""
    return (
        f"\n\n**Converged.** With slipwai {record.get('with')}, every row of the map read *as generated* and the "
        f"material moved from `{record.get('from')}/` to the root, as one merge. From here on this repository follows "
        "the generated workflow, `slipwai migrate` included; `origin: adopted`, the survey and this page are its "
        "history.\n"
    )


def kind_phrase(app: App) -> str:
    """How a page names what a wrapped application is: `a service`, `a library` — or that nobody has said."""
    return f"a {app.kind}" if app.kind != "application" else "an application whose role is not recorded"


def ci_paragraph(adoption: Adoption, layout: Layout) -> str:
    """The sentence about where the gate runs in CI, true to the forge that was recorded."""
    ci = adoption.ci
    forge, gate, provenance = ci.get("forge", "github"), ci.get("gate", ACTIONS_GATE), ci.get("provenance", "detected")
    if forge in ("github", "gitea"):
        runner = "GitHub Actions" if forge == "github" else "Gitea Actions"
        return (
            f"The same `verify` runs in CI from `{gate}` on {runner} (`{provenance}`), beside whatever CI this "
            "repository already had."
        )
    if forge == "gitlab":
        return (
            f"The same `verify` runs in CI as the GitLab job in `{gate}` (`{provenance}`) once `.gitlab-ci.yml` includes "
            f"it — `include: [local: {gate}]` — beside whatever jobs it already has; that edit is yours, since the "
            "file is."
        )
    if forge == "other":
        return (
            f"No CI configuration was written: this repository's CI (`{ci.get('evidence')}`, recorded as `other`, "
            f"`{provenance}`) is not one the factory can write a job for. Have it run `{layout.make} verify`; until it "
            "does, the gate runs on the machine that runs it and nowhere else."
        )
    return (
        f"No CI configuration was written: the survey found none in this repository (`{provenance}`). The gate runs "
        f"where somebody runs `{layout.make} verify`, and nowhere else, until a CI runs it — that is the first rung "
        "of the path to production, and `/drive` will ask about it."
    )


def release_paragraph(adoption: Adoption) -> str:
    """What is recorded about how a change reaches production, and what the record's honesty asks next."""
    release = adoption.release
    path, provenance = release.get("path", "unknown"), release.get("provenance", "unrecorded")
    evidence = ", ".join(f"`{e}`" for e in release.get("evidence") or [])
    return {
        "pipeline": f"**A pipeline deploys** (`{provenance}`{f', from {evidence}' if evidence else ''}). Which "
        "environments it passes through, what gates each, and how a release is undone belong in "
        "`docs/deployment.md`; `/drive` asks every slice how it reaches production.",
        "scripted": f"**Somebody runs a script** (`{provenance}`{f', from {evidence}' if evidence else ''}). A "
        "scripted release is one rung below a pipeline: the next step is a CI job that runs the same script on "
        "every commit that passes `verify`, described in `docs/deployment.md` before it is built.",
        "manual": f"**By hand** (`{provenance}`). Nothing here deploys; the first rung of the path to production is a "
        "script that does what the hands do, versioned here, and `docs/deployment.md` is where to write down what "
        "the hands do today.",
        "unknown": f"**Not recorded** (`{provenance}`): nothing in the tree says how a change reaches production, and "
        "nobody has said yet. This is the first Minimum CD fact and the method will not guess it: say it in "
        "`project.json` under `release.path` (`pipeline`, `scripted` or `manual`) or with `slipwai adopt --release`, "
        "and `/drive` asks before the first slice.",
    }[path]


def agents_block(layout: Layout, version: str) -> str:
    """The marked section `adopt` appends to the repository's `AGENTS.md`, in the shape an extension's block has,
    so that a harness reading a copy of the file receives it too (`scripts/agents/project.py`)."""
    return f"""
<!-- extension:delivery:begin -->
## Delivery method (installed by slipwai {version}; experimental)

This repository adopted the factory's delivery method: its material lives under `{where(layout)}`, beside
the code, and `project.json` records what was here and what was confirmed about it. Read
`{where(layout)}docs/adoption.md` first, then `{where(layout)}docs/convergence.md` — where this repository
stands on each ladder a generated project sits at the top of; a rung is claimed only from a fact, an
`unrecorded` row is a question to ask, and `project.json`'s `convergence` is where an answer is written. The
gate is `{layout.make} verify`; the skills are under
`{where(layout)}skills/` and the commands under `{where(layout)}commands/` (`{layout.make} agents`
projects them into your harness). The rules in `{where(layout)}docs/architecture.md` bind code the factory
generates; existing code is held to its own recorded commands and to nothing it did not have before. Change
what `project.json` says only by editing it deliberately, and never edit anything listed in
`{where(layout)}{WRITTEN}` by hand — those files are the factory's, and `slipwai migrate` replaces them.

**Tests written here** — for new code and for code that was here alike — stand in at a seam with a fake
written in the test tree, a class or function implementing the real interface, never with a mocking framework
this repository would have to add: Mockito, Moq, gomock, `unittest.mock` and `jest.mock` are the same last
resort in every language, and "what should I add?" is never answered with one. Where the test framework that
was here is out of support — JUnit 3 or 4, nose, a runner nobody maintains — new tests use the ecosystem's
*current* framework and keep the old tests running beside them (JUnit 5 through its vintage engine; pytest
runs `unittest` suites as they are), as a slice on the map's Platform row: never the next-oldest version,
never an upgrade decided in passing.

**One pull request per slice.** The adoption commit merges alone, before any slice; each slice is its own pull
request, and a slice's after-acceptance commits — the adversary pass, the archive — ride in its own PR, never
the next one's. A first PR of five slices and 566 files was reviewed by nobody, and a framework's major version
moved inside it unseen.
<!-- extension:delivery:end -->
"""


def makefile_block(layout: Layout) -> str:
    """The root `Makefile` `adopt` writes where the repository has none, so that `make verify` is one word from
    the start. Marked like the other appended blocks: targets of the repository's own go around it."""
    return f"""# slipwai:delivery:begin — written by `slipwai adopt`, since this repository had no Makefile
# The delivery method's targets, offered as this repository's own: `make verify`, `make help`. Add targets of
# your own around this block, not inside it.
-include {where(layout)}Makefile
# slipwai:delivery:end
"""


def gitignore_block(ignored: str, layout: Layout) -> str:
    """The marked lines `adopt` appends to the repository's `.gitignore`: what the delivery material writes."""
    lines = "".join(f"{line}\n" for line in ignored.splitlines() if line and not line.startswith("#"))
    return f"\n# slipwai:delivery:begin — what the delivery material under {where(layout)} writes\n{lines}# slipwai:delivery:end\n"

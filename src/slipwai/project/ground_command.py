"""`commands/ground.md`: the questions the tree cannot answer, asked by the agent of the person, one row at a time.

Brownfield adoption. The survey places every row of the convergence map it can from a file, and leaves the rest
`unrecorded` — a question, not a default. `adopt` asks only where CI runs in the terminal, and `adopt --yes` asks
nothing. This is the question set proper, run by the coding agent after `./init` and before the first slice, and again
whenever `/sail` enters at Ground with a row it needs unplaced: the rung meanings and the survey's evidence in front of
the person, one question at a time, the answer written where the record keeps it with `confirmed` provenance and the
person's words as evidence, and `/survey` afterwards so the pages follow and the strategy recommendation is re-made from
what was said. Regenerated with the record, so the table of rows it opens with is the map as it stands.

The page is an asset of the adoption (`assets/adoption/commands/ground.md`); what is left here is what it
may name. The question set below stays: it is one section per axis of `convergence.AXES`, with each rung's
meaning read off the axis, so an axis that gains a rung gains a line and cannot fail to — and a file per
axis under `assets/` would be a fragment landing nowhere in a project.
"""
from __future__ import annotations

from ..assets import ADOPTION_ROOT
from ..convergence import AXES, Axis
from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App, wrapped_of
from .prose import page
from .write_model_prose import rung_question

# Where the pages live. An asset of the adoption rather than of the toolkit, for the reason
# `strangle_command.py` gives: everything under `assets/toolkit/` is copied into every project and
# only an adopted one is written over here, so a page kept there would reach a generated repository
# raw, with its `{{make}}` still in it — and a greenfield project has nothing that was here to ask
# about anyway.
COMMANDS = ADOPTION_ROOT / "commands"

# What to ask for each axis, and where the answer is written. The constitution is not asked: `/speckit-constitution`
# and the gate establish it, and a person saying "ratified" does not make it so.
QUESTIONS: dict[str, tuple[str, str]] = {
    "path-to-production": (
        "How does a change reach production today — and is it the only way one can?",
        "`release.path` in `project.json` (`pipeline`, `scripted` or `manual`) with `release.provenance` `confirmed`, "
        "and the row; `pipeline-decides` and `one-path` are claims about *every* change, so ask for the exception "
        "before recording either",
    ),
    "integration": (
        "How is work integrated: long-lived branches merged when a feature is done, trunk with short branches, or "
        "daily integration with CI on every commit and a build that stops on red?",
        "the row alone — nothing in the tree can say this, so the person's answer is the fact",
    ),
    "safety-net": (
        "Do the recorded tests run green, and would you ship on them? Are they fast enough to run on every change, "
        "deterministic, and do they cover the seams a change would touch?",
        "the row; `tests-pass` and above are contradicted by a quarantined suite in the baseline, and the tree wins. "
        "A repository at `none` reaches `tests-exist` with its ecosystem's own runner and nothing else: the method "
        "never adds a mocking framework, and `/characterise` says what stands in at a seam instead",
    ),
    "structure": (
        "What is each buildable directory for — a service that runs somewhere, a library others import, a tool run "
        "by hand or in CI, a test suite of its own?",
        "`kind` on the application's record in `deployables`, with `provenance.kind` `confirmed`; the row moves "
        "when `/survey` re-reads the record",
    ),
    "build": (
        "Does each application build from a clean clone through its recorded command alone — on a machine with only "
        "the runtime its toolchain file names — and is there anything the build needs that is not in the tree: a jar "
        "copied by hand, an IDE that runs it, a tool installed once and forgotten? `docs/strategies/build-floor.md` "
        "has the eight criteria the row is read from",
        "nothing — the row is read off the tree, and moves when the build does: a declared dependency, a wrapper, a "
        "stated target, an untracked output. What only a person knows (the jar nobody can name, the machine it "
        "really builds on) goes in `survey/running.md`, and the programme's build steps take it from there",
    ),
    "platform": (
        "Where the tree pins no runtime version, which version does it actually run on where it is deployed — the "
        "gate's CI had to guess one and says so with *to confirm*? And of what `survey/structure.md` dates as out of "
        "support (*What it runs on*), is any of it not what actually runs, or under a vendor's paid support the table "
        "does not know? Read them each product's option from that page; each is a method slice for this row",
        "the runtime version in `toolchain.version` on the application's record with `provenance.toolchain` "
        "`confirmed` — it then stands through every `/survey`, which writes it into the gate's CI in place of the guess "
        "and dates it here — and a version the application cannot actually run on is a fact for `survey/running.md`, "
        "not a reason to leave the guess. A product the table does not know stays `unknown` in the evidence: say so, "
        "never fill it in. Support the table is wrong about is the row itself, `confirmed`, with the vendor's terms as "
        "`evidence`; the product's status in `platform` stays what the table says",
    ),
    "data": (
        "Where is the database schema versioned: here, in another repository (which?), nowhere anybody can see "
        "(a DBA, a console), or is there no database?",
        "`database.schema` (`here`, `elsewhere` with `repository`, `unmanaged`, `none`) with `provenance` `confirmed`",
    ),
    "infrastructure": (
        "Where is the infrastructure this runs on described: here, in another repository (which?), nowhere "
        "(ClickOps), or is there none to describe?",
        "`infrastructure.home` the same way, with `provenance` `confirmed`",
    ),
    "strategy": (
        "Two questions, asked apart. First: why is this work happening — what is the business trigger — in their "
        "words, not yours (a slice being built is not a trigger). Second, once `/survey` has re-made the recommendation "
        "from that: which strategy — `leave-it`, `in-place`, `strangler-fig` or "
        "`rewrite` — with all four named, the recommendation read out as one of them with its reasons and what has to "
        "hold `before`, and *not yet* an answer. A strategy the map only *recommends* is this question, every time, "
        "never a default you decide for them",
        "`why` in `project.json`, in their words. The strategy is an accepted ADR under `docs/adr/` with a `Strategy:` "
        "line, *leave it* included — and the word `Accepted` is the person's: you draft the ADR at `Proposed`, show it, "
        "and change its Status only after they have said, of that text, that they accept it, quoting them in the "
        "commit. Never write `Accepted` because the recommendation was not disputed, or because a slice needed the "
        "row moved",
    ),
}


def rung_lines(axis: Axis) -> str:
    return "\n".join(
        f"   - `{rung}` — {axis.means[rung]}" + (" *(a generated project sits here)*" if rung == axis.target else "")
        for rung in axis.rungs
    )


def row_table(adoption: Adoption) -> str:
    rows = {row.get("axis"): row for row in (adoption.convergence or []) if isinstance(row, dict)}
    lines = ["| Axis | Stands at | Provenance | Evidence |", "|---|---|---|---|"]
    for axis in AXES:
        row = rows.get(axis.key) or {}
        lines.append(
            f"| {axis.title} | `{row.get('rung', axis.rungs[0])}` | `{row.get('provenance', 'unrecorded')}` | "
            f"{row.get('evidence') or '—'} |"
        )
    return "\n".join(lines)


def application_lines(apps: list[App], about: str = "kind") -> str:
    """The wrapped applications as the record has them: their roles for the Structure question, their runtime pins
    for the Platform one."""
    def line(app: App) -> str:
        if about == "smoke":
            commands = app.commands or {}
            if commands.get("smoke"):
                said = f"`smoke` recorded as `{commands['smoke']}` ({app.provenance.get('commands', 'detected')})"
            elif "smoke" in commands:
                said = "`smoke` recorded as a written no; `survey/running.md` carries the reason"
            else:
                said = ("no `smoke` recorded — nobody has proved how it starts, and `/sail` refuses to change it "
                        "until somebody has")
            return f"   - `{app.name}` at `{app.path}`: {said}"
        if about == "platform":
            version = (app.toolchain or {}).get("version")
            return f"   - `{app.name}` at `{app.path}`: " + (
                f"runs on {(app.toolchain or {}).get('kind')} {version} ({app.provenance.get('toolchain', 'detected')})"
                if version else "no runtime version is pinned anywhere in the tree"
            )
        return f"   - `{app.name}` at `{app.path}`: recorded as " + (
            f"`{app.kind}` ({app.provenance.get('kind', 'detected')})" if app.kind != "application"
            else "an application whose role nobody has established (`application`, `unrecorded`)"
        )
    return "\n".join(line(app) for app in wrapped_of(apps)) or (
        "   - no application that existed before the method is recorded"
    )


def question_sections(apps: list[App]) -> str:
    sections = []
    for axis in AXES:
        if axis.key not in QUESTIONS:
            sections.append(
                f"### {axis.title}\n\nNot asked. The constitution is established by `/speckit-constitution` and held by "
                "`make check-constitution`; a person saying it is ratified does not make it so. Say where the row "
                "stands and move on."
            )
            continue
        question, written = QUESTIONS[axis.key]
        extra = ""
        if axis.key in ("structure", "platform"):
            extra = f"\n\n   The applications that were here:\n\n{application_lines(apps, axis.key)}"
        sections.append(
            f"### {axis.title}\n\n**Ask:** {question}\n\n   The rungs, from the floor:\n\n{rung_lines(axis)}{extra}\n\n"
            f"**Write:** {written}."
        )
    return "\n\n".join(sections)


def values(apps: list[App] | None = None, layout: Layout = AT_ROOT,
           adoption: Adoption | None = None) -> dict[str, str]:
    """Every value `ground.md` may name, and the whole of what it may name.

    All of it is rendered from a declaration or from the record: the map as it stands, the question set
    from `convergence.AXES` and the table above, the applications as `project.json` has them, what the
    survey found that builds, and the paths that move with the delivery layout. The page's own English —
    the rules, the first question, how each application starts — is the asset's.
    """
    apps = [] if apps is None else apps
    adoption = Adoption() if adoption is None else adoption
    proposed = [row for row in (adoption.candidates or []) if isinstance(row, dict) and row.get("writeModel")]
    return {
        "make": layout.make,
        "convergence-page": layout.under("docs/convergence.md"),
        "running-page": layout.under("survey/running.md"),
        "map": row_table(adoption),
        "questions": question_sections(apps),
        "how-each-starts": application_lines(apps, "smoke"),
        "candidate-rows": candidate_rows(adoption),
        "rung-question": rung_question(proposed),
    }


def candidate_rows(adoption: Adoption) -> str:
    """The directories the survey found that build, one line each, with what the tree says each is for."""
    return "\n".join(
        f"   - `{row.get('name')}` at `{row.get('path')}` — {row.get('language')}, from `{row.get('evidence')}`"
        + (f"; the tree says {row.get('kind')} ({row.get('roleEvidence')})" if row.get("roleEvidence")
           else "; nothing in the tree says what it is for")
        for row in (adoption.candidates or []) if isinstance(row, dict)
    )


def ground_command(apps: list[App], layout: Layout, adoption: Adoption) -> str:
    """The question set, asked of the person one row at a time.

    What the candidates are is a whole section, and it comes before any row because nothing else can be
    answered without it: a Structure row is about applications, and until somebody says which of the
    directories the survey found *are* applications there is nothing for the rows to be about — and
    `verify` refuses (ADR 0003). An adoption with nothing outstanding has no such question, and the
    section is gone rather than empty.

    It is the question the terminal used to ask once per directory with `[Y/n]` and a default of yes,
    which is how asset bundles and a test suite were wrapped as applications on the first real monorepo
    it met.
    """
    candidates = [row for row in (adoption.candidates or []) if isinstance(row, dict)]
    return page(COMMANDS, "ground.md", values(apps, layout, adoption),
                ("candidates",) if candidates else ())


def ground_command_files(apps: list[App], layout: Layout, adoption: Adoption) -> dict[str, str]:
    return {"commands/ground.md": ground_command(apps, layout, adoption)}

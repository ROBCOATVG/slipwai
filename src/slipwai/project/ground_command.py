"""`commands/ground.md`: the questions the tree cannot answer, asked by the agent of the person, one row at a time.

Brownfield adoption (experimental as `AGENTS.md` defines the word). The survey places every row of the
convergence map it can from a file, and leaves the rest `unrecorded` — a question, not a default. `adopt`'s own
interview asks a few of those questions in the terminal, and `adopt --yes` asks none. This is the question set
proper, run by the coding agent after `./init` and before the first slice, and again whenever `/drive` enters at
Ground with a row it needs unplaced: the rung meanings and the survey's evidence in front of the person, one
question at a time, the answer written where the record keeps it with `confirmed` provenance and the person's
words as evidence, and `/survey` afterwards so the pages follow and the strategy recommendation is re-made
from what was said. Regenerated with the record, so the table of rows it opens with is the map as it stands.
"""
from __future__ import annotations

from ..convergence import AXES, Axis
from ..layout import Layout
from ..origin import Adoption
from ..services import App, wrapped_of

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
        "from that: which strategy — `leave-it`, `in-place`, `modular-monolith`, `strangler-fig` or "
        "`rewrite` — with all five named, the recommendation read out as one of them with its reasons and what has to "
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
                said = ("no `smoke` recorded — nobody has proved how it starts, and `/drive` refuses to change it "
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


def candidate_section(adoption: Adoption, layout: Layout) -> str:
    """The candidates, asked about before any row of the map.

    First because nothing else can be answered without it: a Structure row is about applications, and until
    somebody says which of the directories the survey found *are* applications there is nothing for the rows
    to be about — and `verify` refuses (ADR 0003). This is the question the terminal used to ask once per
    directory with `[Y/n]` and a default of yes, which is how asset bundles and a test suite were wrapped as
    applications on the first real monorepo it met.
    """
    candidates = [row for row in (adoption.candidates or []) if isinstance(row, dict)]
    if not candidates:
        return ""
    rows = "\n".join(
        f"   - `{row.get('name')}` at `{row.get('path')}` — {row.get('language')}, from `{row.get('evidence')}`"
        + (f"; the tree says {row.get('kind')} ({row.get('roleEvidence')})" if row.get("roleEvidence")
           else "; nothing in the tree says what it is for")
        for row in candidates
    )
    return (
        "## What is an application here\n\n"
        "Asked first, and before any row: until one of these is confirmed there is nothing for the rows to be\n"
        f"about, and `{layout.make} verify` refuses rather than passing over nothing. `adopt` recorded them and\n"
        "wrapped none of them, because which of them the gate should hold is a question the code answers and a\n"
        "terminal cannot ask.\n\n"
        "   The directories the survey found that build:\n\n"
        f"{rows}\n\n"
        "**Ask, one at a time, having read the directory first:** is this an application the gate should hold —\n"
        "or is it an asset bundle, a test suite for something else here, a sample, a vendored dependency? Say\n"
        "which you think it is *and why, from what you read*, before asking; the person is confirming your\n"
        "reading, not answering a quiz. Where it is one: what should it be called (the directory's name is what\n"
        "the record proposes, and `default` or `ui` is rarely what anybody calls it), what does it own in a\n"
        "sentence or two, and are the commands the survey read the ones that matter?\n\n"
        "Where they asked for the long form, each answer says what confirming it does: which commands join\n"
        "the gate and what running them needs, what a red one would stop, and what declining forfeits\n"
        "instead. *Held as a `library` for its lint \u2014 `make verify` gains `npm run lint` here, which needs\n"
        "only Node* and *declined \u2014 its lint stays in the repository's own CI, which already runs it, and\n"
        "the delivery gate says nothing about this directory* are answers somebody can choose between. *Yes*\n"
        "and *No* are not. Where they asked for the short form, the labels stand alone and your reading above\n"
        "them carries the reasoning.\n\n"
        "**Write:** one `slipwai adopt --confirm <name>` per application — with `--as <name>=<new>` where the\n"
        "directory's name is not its name, and `--kind`, `--purpose` and `--command` for what you established —\n"
        "and `--decline <name>` for each that is not one. The command builds the record and regenerates\n"
        "everything that reads it, so never edit `deployables` by hand. A directory you are unsure of stays a\n"
        "candidate: that is what the state is for, and leaving it is an honest answer where guessing is not.\n\n"
    )


def ground_command(apps: list[App], layout: Layout, adoption: Adoption) -> str:
    page = layout.under("docs/convergence.md")
    return f"""---
description: Ask the person what the tree cannot say — one question per row of the convergence map — and record each answer with its provenance
argument-hint: [axis ...]
---

# Ground

This repository adopted the delivery method around code that was already here. `{page}` says where it stands
on each ladder a generated project sits at the top of. The survey placed every row it could from a file, and the
rows it could not are `unrecorded` — a question, not a default. This command is that question set, asked by you
of the person, one row at a time, with the answers written where the record keeps them. Two ways in, one question
set: run it on its own after `./init` and before the first slice, or let `/drive` run it — its Ground stage is this
command, for the axes the slice touches, and the ladder continues once the rows are placed. `$ARGUMENTS` names the
axes to ask about; empty means every row a person has not yet placed.

## The rules

- **One question at a time.** Ask, wait, write, confirm what was written, then the next. Never a questionnaire
  (`skills/find-gaps/SKILL.md` has the discipline).
- **Evidence and rungs first.** Before asking, show the row as it stands — the evidence the survey found and each
  rung's meaning — so the person places themselves on a ladder rather than answering a quiz.
- **Settle from the tree whatever the tree settles, and say you did.** A question you can answer by reading a
  file is not a question to put: read it, say what you found and where, and record it. Ask only what reading
  cannot reach — what a person intends, what they would ship on, what they know about how the work is done. A
  menu offered for something the tree already states asks somebody to guess at their own repository.
- **Ask how much to explain, first, and hold to the answer.** The opening question is not about this
  repository: it is whether they want each answer's consequence spelled out — what it writes, what moves,
  what it costs — or the short form. Somebody who knows this codebase and this method does not need to be
  told what webpack does, and being told anyway is how a question set becomes a wall to skim; somebody
  meeting either for the first time cannot answer safely without it. Offer both, say which you would pick
  for them and why, and take the answer as standing for the rest of the run unless they change it — which
  they may, at any question, in either direction.
- **In full, every answer on offer says what it does.** The person reads the options, not the paragraph above
  them, so each one names what it writes, what moves because of it, and what it costs. *`library`, and the
  gate holds its lint: `make verify` runs `npm run lint` here from now on, and a red one stops every change
  until it is fixed or quarantined* is an answer. *Yes — hold its lint* is a label, and a label is what gets
  picked by somebody who does not yet know what they are picking. Where two options differ only in a word,
  say what turns on that word. Never offer one whose consequence you have not stated: if you cannot say what
  an answer does, you are not ready to ask it.
- **In short, the labels stand alone — and two things never go.** The short form drops the elaboration, not
  the honesty: what you think and why, from what you read, stays (the next rule), and *I don't know* stays an
  answer on offer. What a short answer costs is a sentence away whenever they ask, and offering that once —
  *say the word and I will spell any of these out* — costs a line.
- **Say what you think, and why, from what you read.** A recommendation with its reasoning is what makes an
  answer a confirmation rather than a guess, and it is what lets somebody disagree with you on the evidence
  rather than on authority. Never a bare menu.
- **"I don't know" is one of the answers, every time, and offered as one.** It is the honest state of most
  rows in most repositories on the first pass, and a question that does not offer it is a question that
  manufactures an answer.
- **A rung is claimed only from a fact.** Here the person is the fact for what only they can know (how work is
  integrated, whether they would ship on the tests). Where the tree can contradict a rung — a release path, a
  quarantined suite, a template constitution, an application's role, no accepted ADR — the tree wins:
  `make check-convergence` fails the row, so say that instead of recording it.
- **"I don't know" stays `unrecorded`,** and is said so in the row's evidence. It is not filled in from context.
- **`detected` is the tree's reading, not the person's answer.** A row the survey placed from a file is asked
  about like an `unrecorded` one the first time; only `confirmed` and `overridden` mean a person has spoken.
- **A row a person already placed** (`confirmed`, `overridden`) is asked about again only if `$ARGUMENTS` names
  its axis; never moved silently.
- **Record, do not paraphrase.** `rung`, `provenance` `confirmed`, `evidence` in the person's own words, and
  `planned` where they name the slice that will move it. Where the answer is a fact under another key — the
  release path, an application's `kind`, a home, `why` — write it there with `confirmed` provenance; the row
  follows when `/survey` re-reads the record.

## The first question

Asked before anything about this repository, once, and answered for the rest of the run:

**Ask:** how much should each answer explain itself? *Long* spells out, for every option, what it writes to
the record, what moves because of it, and what it costs — which is what somebody meeting this repository or
this method for the first time needs in order to answer safely. *Short* gives you the reading, the
recommendation and the answers as labels, on the understanding that you already know what confirming an
application or placing a rung does. Say which you would pick for this person and why, from what you can see:
a repository whose record is entirely `unrecorded` and whose person has not met the method suggests long; a
second or third adoption by the same hands suggests short.

Then say, once: *say the word at any question and I will spell that one out* — and mean it, in either
direction, at any point.

**Write:** nothing. It is how you talk, not a fact about the repository, and it is not a row.

{candidate_section(adoption, layout)}## The rows, as they stand

{row_table(adoption)}

## The questions

{question_sections(apps)}

## How each application starts

Not a row of the map, and asked before any slice changes code that was here: an application nobody has proved
starts is the floor beside the build, and `/drive`'s Pin stage refuses to change one. The first adoptions each
merged a slice that had stopped the application starting — constructor injection the container could not call —
and no suite saw it, because no suite builds the context.

**Ask:** For each application below — how is it started: the command, the port, what has to be seeded first, the
runtime it needs and the ones it cannot run on? What proves it answers — a URL, a command? Has anyone run it that
way since the method arrived, and did it start?

   The applications that were here:

{application_lines(apps, "smoke")}

**Write:** what was proven, with the date, in `{layout.under("survey/running.md")}` — the repository's own file,
which the `run-the-app` skill points to — including the run that failed and why. Then the one command that starts
the application and proves it answers, exiting non-zero when it does not, as `smoke` under the application's
`commands` in `project.json`, with `provenance.commands` `confirmed`: `make smoke` and the gate's smoke job run it
from then on, `verify` never does. An application nobody can start anywhere but production is a written `null`
with the reason in the same file — never a key left unwritten, which reads as a question still open.

## Then

1. `/survey` (`slipwai adopt --refresh`): the pages follow the record, and the strategy recommendation is
   re-made from what was said. Read the person the map's summary line and the recommendation
   `docs/change-strategy.md` now opens with.
2. `make verify` — `check-convergence` holds every row you wrote to the tree.
3. Commit as one change: what the person said, in the rows and the facts, and the pages that followed.
4. Say which rows are still `unrecorded`, and that `/drive` will ask about each before a slice that touches it.
"""


def ground_command_files(apps: list[App], layout: Layout, adoption: Adoption) -> dict[str, str]:
    return {"commands/ground.md": ground_command(apps, layout, adoption)}

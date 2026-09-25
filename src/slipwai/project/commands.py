"""`commands/`: the workflow commands adapted to this project's profile and toolchain."""
from __future__ import annotations

from ..catalog import CATALOG
from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App, backends_of, web_apps
from ..targets import managed
from .add_commands import add_command_files
from .adversary import adversary_command
from .benchmark import benchmark_command, what_each_stage_costs
from .converge_stage import convergence_stage
from .cruise import cruise_command, cruise_settings_command
from .cruise_seat import cruise_status_command, cruise_stop_command, cruise_tell_command, cruise_watch_command
from .demo_stop import demo_stop
from .drive_adoption import adoption_ladder
from .drive_settings import drive_settings_command, implementation_section
from .existing import release_stage
from .flags import PUSH_CHECK
from .mutation import mutation_command
from .parallel_slices import concurrent_slices, done_marker, ready_set_selection
from .stage_models import model_delegation_settings_command, who_runs_each_stage
from .whats_next import whats_next_command
from .where_are_we import where_are_we_command


def drive_command(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> str:
    resolution = "the requested slice in `docs/event-model/model.yaml`" if event else "the requested feature or the active directory recorded in `.specify/feature.json`"
    # A slice with a screen is not finished at browser defaults, and styling it is not a follow-on slice:
    # first slices kept reaching the demo in Times New Roman on white, which answers a question the actor
    # was not asked. Only where there is a browser app to style, and named by its own path — a
    # project whose browser app is `apps/portal` has no `apps/web` for this to point at.
    web = web_apps(apps)
    baseline = ", ".join(f"`{app.path}`" for app in web)
    styling = (
        """ Where the slice puts anything on a screen, its styling is one of the tasks written here rather
   than a follow-on: name the screens it adds or changes and where each takes its styles from."""
        if web
        else ""
    )
    stages = [
        """**Principles** — `.specify/memory/constitution.md` is ratified rather than absent, unfilled, or
   still the template `./init` installed, and `make check-constitution` passes. A passing gate alone is not
   this stage done: the gate lets the untouched template through so the first push can deploy, and says so
   (`nothing drafted yet`). Otherwise run `/speckit-constitution`, then `/constitution-coverage` for
   whatever the gate still reports missing.""",
        """**Product specification** — `specs/<feature>/spec.md` describes the product this slice belongs to.
   Otherwise run `/speckit-specify`, then `/gaps` over what it promises.""",
    ]
    if event:
        stages.append(
            """**Event model** — `docs/event-model/model.yaml` names the commands, events, read models, and
   actors the work needs, and is no longer only the generated placeholder. Otherwise model it with
   `skills/event-modeling/SKILL.md`. An unmodelled event has no name to implement against. With more than
   one service in `project.json`'s `deployables`, every modelled slice also names the service that owns it
   in `service`, chosen against each service's recorded `purpose` (`docs/architecture.md`, *Bounded
   contexts*); where that service holds more than one bounded context (its `contexts`), the slice names
   the one it belongs to in `context` as well. `make check-model` refuses a slice that leaves either
   unsaid. A slice no purpose covers, or a service with no purpose recorded, is a product decision — ask,
   never default to the first service or the first context. Which contexts there are is found here, not
   declared up front: before slices go to `modelled`, apply Conway's law to the model
   (`skills/event-modeling/references/nine-steps.md`, end of Step 9) — lanes with vocabularies of their
   own, joined only by the events one publishes and another reads, are bounded contexts. Record them on
   the service, with the user, as `slipwai describe-service <name> --context <context>` (once per
   context; `--purpose` records what the service owns the same way), and place each slice with
   `context:`. One vocabulary is one context; say so and move on."""
        )
    stages.append(
        """**Split** — the work is ordered vertical slices rather than one undivided outcome. Otherwise run
   `/story-splitting`."""
    )
    if event:
        stages.append(
            """**Example map** — `specs/<feature>/slices/<id>/examples.md` holds the slice's rules, examples,
   and Given/When/Then. Otherwise run `/example-map`."""
        )
    stages.append(
        """**Slice gaps** — %s
   records a gaps review for this slice: the criteria and states it added, or a `Gaps reviewed` note saying
   what was checked. Otherwise run `/gaps` over it. A missing state is a paper edit here and a rewritten
   test later."""
        % (
            "`specs/<feature>/slices/<id>/examples.md`"
            if event
            else "the slice's acceptance criteria in `specs/<feature>/spec.md`"
        )
    )
    context_decision = (
        """ It also names the bounded context inside that service: the one the slice's `model.yaml` entry
   names in `context`, so the code goes under that `src/<context>/`."""
        if event
        else """ It also names the bounded context inside that service, and this is where contexts are
   found in a project without an event model: read the specification's vocabulary the way
   `skills/domain-driven-design/resources/bounded-contexts.md` describes under *The Language Test* — the
   same word meaning two things, qualifiers creeping in ("billing customer", "shipping customer"), rules
   that change for different reasons. Two vocabularies are two bounded contexts: record them on the
   service, with the user, as `slipwai describe-service <name> --context <context>` (once per context), and
   put each context's code under its own `src/<context>/` behind a `public` module — `make check-imports` keeps them apart from then on. One
   vocabulary is one context, and saying so is the whole decision. Neither is a reason for a new service;
   `docs/architecture.md`, *Bounded contexts*, says what is."""
    )
    # Before the plan, where the decision is written down; absent under `--target none`, which has nothing to decide.
    stages += release_stage(apps, target)
    stages += [
        """**Plan and tasks** — `specs/<feature>/slices/<id>/plan.md` and `tasks.md` exist. Otherwise run the
   installed Spec Kit plan and tasks commands — after making the canonical paths they resolve to into links.
   Those commands write `specs/<feature>/plan.md`, `research.md`, `data-model.md`, `quickstart.md` and
   `tasks.md`, one slot per feature, so before running them: `mkdir -p specs/<feature>/slices/<id>` and, for
   each of the five, `ln -sfn slices/<id>/<name> specs/<feature>/<name>`. The commands then write through the
   links, the record lives under `slices/<id>/` from the day it is planned, and every later stage reads it
   there. After each command, `ls -l specs/<feature>/`: a regular file where a link was is a harness that
   replaced the link, and the file is moved under `slices/<id>/` and the link remade before anything else.
   The links are ignored by git and never committed. The plan's *Structure Decision* names the service the
   slice's code lives in;
   with more than one service in `project.json`'s `deployables`, that is a choice made against each
   service's recorded `purpose`, never the first service by default — and a slice no purpose covers is a
   product decision to ask. What `research.md` states about a dependency's behaviour — a default, a limit, a
   version's requirement — cites the artefact it was read from: the library's documentation at the pinned
   version, its source, a run against it. A statement with no citation reads *assumed*, and a plan does not
   rest on it."""
        + context_decision + styling,
        """**Implementation** — tasks remain unchecked. Run the installed Spec Kit implement command."""
        + (
            f""" A screen this slice
   adds or changes is styled as part of it: apply the project's own styles — `docs/design.md`, or the design
   notes in the constitution or under `specs/` — and where they do not cover what this slice needs, extend
   the baseline stylesheet and design tokens in {baseline} rather than leaving browser defaults behind."""
            if web
            else ""
        ),
        convergence_stage(),
        """**Demo** — the actor-visible path is ready to show.""",
    ]
    if adoption is not None:
        stages = adoption_ladder(stages, apps, layout)
    ladder = "\n".join(f"{index}. {stage}" for index, stage in enumerate(stages, start=1))
    return f"""---
description: Drive one slice through planning, implementation, and an actor-visible demo
argument-hint: [slice-id-or-feature]
---

# Drive

Deliver one small vertical slice under `AGENTS.md`. Once the ladder below has produced it, resolve
{resolution}.

## Enter at the first incomplete stage

Read artifacts from disk rather than conversation memory and walk this ladder from the top. The entry stage
is the first one whose artifact is missing, empty, or still a placeholder — **including the stages upstream
of the slice loop**. State the entry stage and the evidence that selected it before changing anything, then
run that stage and every stage after it. Never rerun a completed stage merely to check. Where `.codegraph/` is in
the tree, a caller or blast-radius question is one index call — `scripts/codegraph callers <symbol>`, or
`codegraph_explore` — and not a text search; grep is for words in documents.

**The checkout goes stale the way conversation memory does, so check the branch before the artifacts.**
Every signal the ladder reads — a slice's `status`, whether `examples.md` or `tasks.md` exists, the slice
graph — is a property of this commit, and a branch behind trunk reads exactly like a project where the work
was never done: a `/drive` fifty-seven commits behind wrote a second example map for a slice that had
shipped. So fetch and compare first — `git fetch`, then `git log --oneline HEAD..@{{u}}`, or against
`origin/main` where the branch has no upstream. Behind by anything, stop and say so rather than deriving:
the artifacts about to be read are not the project's current ones. The evidence line names the branch, its
head and its distance from trunk in the same breath as the stage. Where the fetch could not run — no remote,
or a remote this environment cannot reach — the line says *could not verify this checkout is current*, and
that never reads as *current*.

{ladder}

Being invoked before any of this exists is a valid start, not an error: it means the entry stage is near the
top of the ladder. Step back to that stage and say so rather than reporting that the request came too early.
Never invent a principle, specification, event, command, stream, or slice to skip a stage — a missing
artifact is work to do with the user, not a gap to fill from context. A stage needing a real product
decision is a stop.

{who_runs_each_stage(layout)}
{what_each_stage_costs(layout)}
{implementation_section(layout)}
## Once inside the slice

Start the slice from a green `make verify`. During implementation, take one RED-GREEN-REFACTOR increment per
task — one rule of the example map with its examples, where the map numbers its rules — run only the quickest
relevant tests in the same file or area, commit that increment locally, and keep
task checkboxes truthful. A local commit is not a push: it does not run the full gate and it does not start
CI. Do not push increment commits until the actor has accepted the demo. Before an increment that changes a
shared function, ask `codegraph_explore` what calls it and what the change reaches — loaded by name where the
harness defers it — and name those callers in the delegate's manifest; a project without `.codegraph/` answers
with a text search and says so.

When the tasks are done, converge, then stop at the actor-visible demo from the unpushed slice branch. After
acceptance — and only then — a project that has adopted CodeGraph runs `codegraph sync`, then the full
`make verify`, then the first push of those increment commits (and the merge that lands them on trunk).
That push is the integration boundary. A claim of `slice/<id>` at the start of the slice may still push a
lock ref from `main`; that is not the implementation.

{demo_stop(event, baseline)}

### After acceptance, and after Phase 4 clears

After acceptance, run `/adversary`, which decides whether the slice changed attack surface or closed the
split and records the attack or the skip — `make check-decisions` holds every done slice to that row. Close the
adversary benchmark entry after its findings are triaged; implement confirmed defects through failing tests,
each in an `implement` entry. Then run `/mutation`, then `make verify`. `commands/adversary.md` owns the
trigger table; do not spawn before it is in the log. It records that decision in
`specs/<feature>/adversary-log.md` either way, so do not make it here. The order is not arbitrary: the pass
adds tests, and mutation measures whatever exists when it runs. Stop earlier only for a product decision or
unavailable input.

Once that evidence is clean, **continue on the same run**: mark the finished slice done —
{done_marker(event)} — and confirm its
`plan.md`, `research.md`, `data-model.md`, `quickstart.md` and `tasks.md` are under
`specs/<feature>/slices/<id>/` with their relative links pointing at what they cite (they have been since it
was planned; a regular file still at the feature root is moved there now, and the canonical links dropped).
Then select the next slice from the **ready** set and re-enter the ladder at whichever stage that slice's
own artifacts require, which is usually its example map or its plan rather than the top. Do not wait to be
invoked again.

{ready_set_selection(event)}

{concurrent_slices(event, layout)}

The stops are a required product decision, an input that is genuinely unavailable, a split with no ready
slice left in it, and the next slice's own demo. **A slice having finished is not one of them.**

Demo feedback re-enters the ladder at the stage that owns the change, which may sit well above the slice
loop. Re-derive the entry stage from artifacts instead of assuming the loop resumes where it paused.

{PUSH_CHECK if managed(CATALOG, target) else ""}"""


def gaps_command(event: bool) -> str:
    extra = (
        """

Compare event names, schemas, stream identity, and model links with the implementation in the same pass."""
        if event
        else ""
    )
    artifact = "a slice's `examples.md`" if event else "the slice's acceptance criteria in `spec.md`"
    return f"""---
description: Find consequential gaps in an artifact before planning, or in what was built afterwards
argument-hint: [artifact-or-feature-or-diff]
---

# Gaps

Two passes, selected by what is named. Neither invents a requirement, and a clean result is a valid outcome
when it says what was checked.

## Before planning — tighten the artifact

Named an artifact that is not built yet — {artifact}, a specification, mockups — read
`skills/find-gaps/SKILL.md` and run the conversational loop it describes: survey, ask one question at a
time, write the answer back as a new criterion or a recorded state, confirm. Missing states, unhandled
edges, unverifiable wording, and a slice still hiding an "and" are what this pass is for, and this is the
last point at which each of them is a paper edit. A gap needing a product decision is a question for the
user, never a criterion written from context.

## After implementing — trace the promise

Named a feature or diff, or nothing at all — the committed diff — read `skills/acceptance-review/SKILL.md`
and trace each acceptance promise to an observable test and a reachable production path. Report only
missing, contradictory, or unreachable behaviour, and separate a confirmed defect from a product question.
Read-only: no edits.{extra}

Run this pass **after** the installed Spec Kit converge command reports converged, never before it.
Converge appends tasks for work the artifacts require and the code lacks; ahead of it, this pass reports
unbuilt tasks as gaps and buries the findings that actually need judgement.
"""


def constitution_coverage_command(event: bool) -> str:
    scope = (
        """minimum CD, the practices this repository's skills teach, and — because `project.json` claims
the event capabilities — the Event Modeling and event-sourcing obligations."""
        if event
        else """minimum CD and the practices this repository's skills teach. The event-sourcing obligations
are not asked of this profile, and `make check-speckit` rejects a constitution that mandates them anyway."""
    )
    return f"""---
description: Check or print the principles this project's constitution must carry
argument-hint: [--requirements] [requirement-key ...]
---

# Constitution coverage

`.specify/memory/constitution.md` is what every later phase treats as the authority, so a principle
dropped from it is a gate that silently stopped existing. `scripts/check-constitution.py` states the floor:
{scope}

```sh
make check-constitution                                # what is missing, if anything
python3 scripts/check-constitution.py --requirements   # the normative text for every requirement
python3 scripts/check-constitution.py --requirements trunk-based-integration governance
```

Run the check with no arguments. With `--requirements`, print the normative text instead — that is the
drafting path, and passing requirement keys narrows it to the ones a finding named.

Amend the constitution rather than the gate, and rephrase freely: the check reads for the terms an
obligation cannot be written without, not for one wording. Where a finding needs a decision nobody has
made — the domain invariant, a retention period, a compliance scope, an unfilled `[PLACEHOLDER]` — report
which requirement is unmet and ask. An invented obligation reads as ratified afterwards, which is worse
than an open question.
"""


# Every command a generated project carries, in the order `docs/skills-and-commands.md` lists them — the last
# three reaching back out to the factory. One list, so the documentation and the files cannot disagree.
BASE_COMMANDS = ("drive", "where-are-we", "whats-next", "gaps", "adversary", "mutation", "constitution-coverage",
                 "model-delegation-settings", "drive-settings", "benchmark", "cruise", "cruise-settings",
                 "cruise-status", "cruise-stop", "cruise-tell", "cruise-watch", "add-service", "add-frontend",
                 "catch-up")
# Copied whole from `assets/profiles/event-modelling/commands/`; listed because the documentation names them in order.
EVENT_COMMANDS = ("example-map", "validate-code-against-model")


def command_names(event: bool) -> list[str]:
    """The commands this profile ships, in the order they are documented."""
    return [*BASE_COMMANDS, *(EVENT_COMMANDS if event else ())]


def command_files(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT, adoption: Adoption | None = None,
) -> dict[str, str]:
    """`commands/`: one file per command, adapted to this profile and the services' backends."""
    files = {
        "commands/drive.md": drive_command(event, apps, target, layout, adoption),
        "commands/cruise.md": cruise_command(event, apps, target, layout, adoption),
        "commands/cruise-settings.md": cruise_settings_command(layout),
        "commands/cruise-status.md": cruise_status_command(layout),
        "commands/cruise-stop.md": cruise_stop_command(layout),
        "commands/cruise-tell.md": cruise_tell_command(layout),
        "commands/cruise-watch.md": cruise_watch_command(layout),
        "commands/where-are-we.md": where_are_we_command(event, target),
        "commands/whats-next.md": whats_next_command(event),
        "commands/gaps.md": gaps_command(event),
        "commands/adversary.md": adversary_command(event),
        "commands/mutation.md": mutation_command(backends_of(apps)),
        "commands/constitution-coverage.md": constitution_coverage_command(event),
        "commands/model-delegation-settings.md": model_delegation_settings_command(layout),
        "commands/drive-settings.md": drive_settings_command(layout),
        "commands/benchmark.md": benchmark_command(layout),
    }
    files.update(add_command_files(apps, target))
    return files

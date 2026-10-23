"""`commands/sail.md`'s ladder: the rungs, in order, and which stage of the model table runs each.

The ladder is the shape of the loop section 5 of the plan draws, and it lives apart from the page it is
written into because it is the part that keeps changing: slice 5.8 adds the review rung, 5.9 the careen's
stowing, 5.12 how dark a merge is, and 5.17 moves the example map onto both profiles. A rung is named by
`stage_models.STAGES`, never here, so a stage with no rung and a rung with no stage are both refusals
rather than a page and a table that quietly disagree.

Version 1 stopped the ladder at the demo and left what came after it to prose further down the page. Three
things that decide whether a slice may merge were in that prose — the adversary pass, the mutation gate,
and the merge itself — and prose is read once where a numbered rung is walked every time. They are rungs
here, and the prose they came from stays where it is, saying how each one is run.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout
from ..origin import Adoption
from ..services import App, web_apps
from .capability_gates import capability_gates_stage, open_mode_note
from .converge_stage import OPEN_SLICE
from .design_stage import PLAN_STYLING, with_design_rungs
from .existing import release_stage
from .sail_adoption import adoption_ladder
from .stage_models import rung_titles
from .write_model_prose import paths_of, state_services

# Rungs that no stage of the model table names, because a project's own answers add them rather than the
# ladder: two where there is a browser app to style, two where the method was installed around a repository
# that already existed. They run on the stage above them, which is why they have no row of their own.
ANSWER_RUNGS = ("Screen design", "Design review", "Ground", "Pin")


def rung_of_the_slice(apps: list[App]) -> str:
    """What naming the service also settles, where this project has a service that keeps current state.

    Only then. In a project where every service keeps its events, `stream` means one thing and `guard` and
    `folds` are always available, so the sentence would be a paragraph about a choice nobody here has — and
    this rung is already the longest on the ladder. Where both rungs exist, choosing the service is choosing
    which fields the slice may carry, and that is a consequence of a decision taken at this rung rather than
    a gate failure to discover two rungs later.
    """
    stored = state_services(apps)
    if not stored:
        return ""
    return f""" Naming the service also settles the slice's write model, which
   `project.json` records as `eventSourced`: on a service that keeps its events, `stream` is the identity an
   append is made at an expected version of and the slice may carry `guard` and `folds`; on one that keeps
   current state — {paths_of(stored)} — `stream` is the row the write locks and its version, `guard` and
   `folds` are refused, and no `liveBudget` is asked of a `live` read model, there being no log to query, to
   fold or to bound. `docs/event-modeling-to-code.md` has the table each service's slices are written
   against."""


#: The Demo rung's second record, where the project has a service to call: the story `quickstart.md` tells, as
#: the calls that make its records, so `make try` opens on them. Written here because the routes and their
#: answers are settled by now, and the plan that wrote the quickstart knew neither.
TRY_STORY = """Beside `quickstart.md` it writes `try-it.json`: the records that story needs, as the calls
   a person's browser would make — `{"as": "<a declared person>", "open": [{"label": "<whose record>", "path":
   "<the screen it is on>"}], "given": [{"stream": "<stream>", "event": "<Event>", "data": {…}}], "steps":
   [{"say": "…", "method": "POST", "path": "/api/…", "body": {…}, "keep": {"<name>": "<field of the
   answer>"}}]}`, a kept `{name}` filling a later path or body. It makes its own records rather than reaching
   for another slice's. `as` names a person under `specs/<feature>/people/` or in the local realm, and a story
   that needs someone new writes their file beside it — never the realm file, which is the host's. A mark
   this slice steers by whose setter has not merged is **given, not waited for**: `given` is the events the
   story needs, in the model's shape, appended through the service's seed door (`make seed-<service>
   FILE=…`) before the first step, and the card marks those records *given, not made*; a story that gives
   nothing and steers by an unset mark cannot seed, and says why in `plan.md`. `make check-try` holds the
   file to all of that with no app running. Then the live half, against the app this berth runs: `python3
   scripts/agents/try_it.py people --apply`, then `python3 scripts/agents/try_it.py seed --slice <id> --api
   <that service>`. A refused step or a refused given is fixed here, and the slice does not reach the review
   rung until the `seeded` deck line that command writes on a green run exists: the captain holds the slice
   to it as it holds it to its `mark-set` lines, in every release mode. So this rung says one thing — the
   examples proven by tests, the people declared, the story seeded green, the `seeded` line written — and
   then the review. It is the first thing a person sees of this slice once it merges, when `make try` loads
   every slice's. """


def sail_ladder(
    event: bool, apps: list[App], target: str = "none", layout: Layout = AT_ROOT,
    adoption: Adoption | None = None,
) -> str:
    """The numbered ladder, from the first host stage to the merge that ends the slice."""
    # A slice with a screen is not finished at browser defaults, and styling it is not a follow-on slice:
    # first slices kept reaching the demo in Times New Roman on white, which answers a question the actor
    # was not asked. Only where there is a browser app to style, and named by its own path — a
    # project whose browser app is `apps/portal` has no `apps/web` for this to point at.
    web = web_apps(apps)
    baseline = ", ".join(f"`{app.path}`" for app in web)
    stages = [
        """**Principles** — `.specify/memory/constitution.md` is ratified rather than absent, unfilled, or
   still the template `./init` installed, and `make check-constitution` passes. A passing gate alone is not
   this stage done: the gate lets the untouched template through so the first push can deploy, and says so
   (`nothing drafted yet`). Otherwise run `/speckit-constitution`, then `/constitution-coverage` for
   whatever the gate still reports missing.""",
        """**Product specification** — `specs/<feature>/spec.md` describes the product this slice belongs to,
   `spec.md` has a `## Clarifications` section (`None.` when `/speckit-clarify` found nothing to ask),
   `specs/<feature>/checklists/` holds the checklist `/speckit-checklist` wrote, and every directory under
   `docs/intake/` is either specified or was killed. Where `spec.md` is already written, this rung is the
   tail and nothing else: run `/speckit-clarify` when it is missing. Then dispatch `/speckit-checklist` and
   the read-only survey phase of `skills/find-gaps/SKILL.md` in parallel against the same clarified
   `spec.md`. Wait for both, then run the find-gaps conversational loop on the host, using the checklist
   and survey together and writing each confirmed answer back. Parallel workers do not edit `spec.md`.
   Clarify and checklist inform find-gaps rather than replace it. Do not run `/speckit-specify` again. A
   person hands a further feature to `/sail` in the conversation —
   the words, text pasted there, or a document this session can read. This session writes that to
   `docs/intake/<slug>/brief.md`; the person does not create the directory. An argument that names a slice,
   a fairway, or a feature that already has `spec.md` is that work. An argument that names an intake
   directory continues that idea. Anything else is a new idea: capture it, state what was captured, and do
   not run `/speckit-specify` yet. Ask whether this is a new feature. Under `/cruise`, delegate that one
   question to `sail-decide-skipper` and record the decision. A yes is `docs/intake/<slug>/confirmed`, the
   line `yes` and who answered. Then, if the assess commands are not installed, run
   `specify extension add assess`, and run `/speckit-assess-intake`, `/speckit-assess-research`,
   `/speckit-assess-define`, `/speckit-assess-shape` and `/speckit-assess-decide` for that slug. The
   artifacts stay in `.specify/assessments/<slug>/`. `needs-clarification` and `kill` stop. A `go` is handed
   to `/speckit-specify` with the whole of the brief and the documents beside it, then `/speckit-clarify`.
   Against that clarified snapshot, `/speckit-checklist` and the read-only find-gaps survey run in parallel;
   after both return, the host runs the find-gaps conversation and writes confirmed answers. Then
   `specified.json` names the `specs/...` directory and the digest `docs/intake/README.md` describes. Spec Kit specifies it
   on the profile `project.json` already names — `event-modelling` or `standard` — and on the one preset
   `.specify/presets/.registry` enables for it. Do not enable the other preset, do not change
   `project.json`, and do not scaffold again. A matching digest is already specified. A different digest is
   assessed again. A session given a slice id stays on that slice.""",
        """**Mock-up review** — `specs/<feature>/mockups/mock-states.md` exists and every state in it is
   `approved`, `parked` with the question it waits on, or `n/a` with its reason. A feature with no surface
   at all writes `surfaces: none` and that is the whole file. Otherwise run `/mockups`, which researches
   what good looks like for each surface, drafts the mock-ups where nobody handed any over, storyboards
   them, and stops for a person to approve them one at a time. This runs before the work is typed, because
   a surface nobody has seen becomes a read model, a route and a set of tests, and all three are more
   expensive to move than a drawing.""",
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
   declared up front: before slices go to `modelled`, interrogate each stream — its invariants, and
   whether any command needs two groups of its slices in one transaction — and give it its `streams`
   `because`; then run `make seams` and apply the seam tests to what it prints
   (`skills/event-modeling/references/nine-steps.md`, *Interrogate every stream* and *Apply Conway's
   Law*) — a shared noun is evidence for neither side, and a stream is never split. Record what survives
   on the service, with the user, as `slipwai describe-service <name> --context <context>` (once per
   context; `--purpose` records what the service owns the same way), place each slice with `context:`,
   and write the answer, one context included, as a decision entry with its seam table — `make
   check-chart` refuses a chart without one."""
            + rung_of_the_slice(apps)
        )
    if not event:
        stages.append(
            """**Chart** — `specs/<feature>/chart.yaml` names this feature's fairways and types every mark
   they publish, and its `marks` each name a file that is in the tree. Otherwise run `/chart`. This is the
   standard profile's answer to what the event model is on the other one, and it is a stop with a person:
   a mark is set once and never moved, so every entry is a commitment another fairway will build against.
   The chart's `slices` block is filled in at the split, and nothing is claimed until `make check-chart`
   passes over the whole of it."""
        )
    stages.append(
        """**Split** — the work is ordered vertical slices rather than one undivided outcome. Otherwise run
   `/story-splitting`."""
    )
    stages.append(
        """**Example map** — `specs/<feature>/slices/<id>/examples.md` holds the slice's rules, an example
   under each, and the questions nobody here can answer. Otherwise run `/example-map`, which %s. This rung
   is not optional and not profile-specific: a slice with no examples has nothing for a test to be about
   and nothing for the hand to walk at its demo, and the implementation rung refuses one whose map is
   empty rather than implementing against what it inferred."""
        % (
            "derives them from the slice's given/when/then in `docs/event-model/model.yaml`"
            if event
            else "writes them from the slice's story in `specs/<feature>/spec.md` and the marks it sets in "
                 "`specs/<feature>/chart.yaml`"
        )
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
        else """ It also names the bounded context inside that service, which `/chart` found by the seam
   tests (`skills/domain-driven-design/resources/bounded-contexts.md`, *The Seam Tests*) — a shared noun
   is evidence for neither side. Each context is recorded on the service, with the user, as `slipwai
   describe-service <name> --context <context>` (once per context), and its code goes under its own
   `src/<context>/` behind a `public` module — `make check-imports` keeps them apart from then on.
   Neither is a reason for a new service; `docs/architecture.md`, *Bounded contexts*, says what is."""
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
        + context_decision + (PLAN_STYLING if web else ""),
        """**Implementation** — tasks remain unchecked, and this slice's `examples.md` has at least one
   example under a rule. A map with none is a stop, not a licence to infer: go back to the example map rung
   and say which rule is waiting on which question. Before anything is implemented, run `/speckit-analyze`.
   It reads this slice's `spec.md`, `plan.md` and `tasks.md` and writes nothing. A requirement no task
   covers, a task the spec never asked for, or a plan that contradicts the spec goes back to the plan or
   the tasks; a clean reading is what lets implementation start. This is not `/gaps`. The pass before
   planning already tightened one artifact, and the capability's pass after converge traces a promise to a
   test and a path. The task list stays in `tasks.md`. Then run the installed Spec Kit implement command.
   This rung is RED-GREEN-REFACTOR and nothing else: a failing test observed failing for its own stated
   reason, the smallest code that passes it, then the code tidied before the next one. The green step's
   gate is the fast checks — `make unit`, lint and types — and never the full gate, which belongs to the
   merge. Where the project has more than one deployable, the increment runs the fast tests of the one its
   boundary owns — `make unit-<name>`, which the `Makefile` writes per deployable — so a service's domain
   increment does not pay for the browser suite each time; `make unit` over all of them is the slice's,
   before its demo. The refactor beat is the third beat of each cycle and is not the reshape pass further down the
   ladder: dropping it is what makes the big one necessary.
   Read `.specify/sail.json` before delegating — `python3 scripts/agents/sail.py` — and say in the stage
   line which boundary and which cycle this slice is running at. Where a veto narrowed them, say that too
   and which one: tasks carrying no story tag are delegated per `rule`, and a map that does not number its
   rules is delegated per `task` and driven per `example`. A slice that cannot support the configured
   width runs narrower and says so; it does not fail. *How implementation is delegated* explains both."""
        + (
            f""" A screen this slice
   adds or changes is styled as part of it: apply the project's own styles — `docs/design.md`, or the design
   notes in the constitution or under `specs/` — and where they do not cover what this slice needs, extend
   the baseline stylesheet and design tokens in {baseline} rather than leaving browser defaults behind —
   in the screens and elements this slice touches, and nowhere else."""
            if web
            else ""
        )
        + """ When the tasks are done the slice goes straight on to its examples: convergence is the
   capability's first gate, once its slices are all built. """ + open_mode_note(OPEN_SLICE),
        """**Demo** — every example in this slice's `examples.md` is proven by an automated test in the
   slice's own suite that drives it through the slice's outermost boundary — the route, the screen's component
   or browser test, the CLI — and `tasks.md` records it under `## Examples proven`: each example against the
   test that proves it, and the command and commit of the run that passed. That record is what lets the
   slice's commits be pushed; it stands where the hand's verdict stood. An example no test can reach through a
   boundary is recorded as such, with why, and is the first thing the hand looks at when it walks the
   capability. **No person is stopped at this rung, and no browser is opened**: the hand walks the whole
   capability once, at *Capability gates*, and the person's demo follows that. """
   + (TRY_STORY if any(app.transport is not None for app in apps if app.is_service) else "")
   + open_mode_note("the hand also walks this slice's examples against the running thing here and records "
                    "a verdict in three words, and the push waits for that verdict as well"),
        """**Review and reshape** — `specs/<feature>/slices/<id>/` records a review of this slice's whole
   diff with every finding closed. Otherwise run `/review`, which gives a fresh context the diff and the
   examples it was built from and returns findings in the shape the gaps stage uses, so one triage reads
   both. **The review is scoped to what the slice added or changed**: the reviewer is handed the slice's diff
   against its merge base (`git diff <merge-base>...HEAD`) and only as much surrounding code as it takes to
   read it, and every finding points at an added or changed line. A finding about code the slice did not
   touch is not this slice's: it is noted for the capability gates or stowed to the careen, and never fixed
   here — that is how a slice stays small. The reviewer never edits: a reviewer that can write is one that
   edits, and then nobody has read the diff with fresh eyes. This slice's own delegate closes the findings and
   then reshapes — the diff as a whole, not one cycle's code, and only code the slice added or changed, never
   a neighbour "while we're here" — with the fast checks green after each step. This is the big refactor the
   small one inside each cycle is there to make unnecessary; they are not the same pass, and collapsing
   them loses the small one. A slice does not reach the attack-surface rung with a review finding open.
   **Once per slice, over the whole diff** — a delegate's return is verified by the session that sent it,
   by spot-checking its RED evidence against the tree, and is never sent to a reviewer of its own: a run
   that reviewed every return paid eight reviews and eight fix rounds for nine pieces of coding and delivered
   no more for it. The one earlier reading this rung allows is a single read-only review of one story's
   pinned commit, for a story that touches identity, authority or money, said in that slice's brief; so a
   slice records at most two `review` brackets, and `make check-benchmark` says so about a third.""",
        """**Attack surface** — `specs/<feature>/adversary-log.md` carries this slice's trigger record: the
   trigger table `/adversary` asks for, each trigger `widened`, `already covered` or `not present` with the
   diff path or prior row that is the evidence, under a heading ending `trigger record`. **Nothing is
   attacked here**, `--full` included: the attack is the capability's, at *Capability gates*, and it runs only
   where at least one of its slices recorded a trigger `widened` — which is what this record is for. Writing
   it is a read of the diff, not a pass, and spawns nothing. """
   + open_mode_note("a slice whose record has the authorisation, identity or money trigger `widened` is "
                    "attacked here as well, before its push, because the merge is live; nothing else is. "
                    "Everywhere else a merge is held back by a flag or a keystone, so what the capability's "
                    "pass has not yet covered is dark until it has"),
        capability_gates_stage(bool(web)),
        """**Merge to main** — the slice is on trunk. Rebase first, run the full `make verify` on the
   rebased branch, and merge. This is the only rung that runs the full gate, and the only one a person
   holds: until a captain enforces the stage boundaries, nothing here merges itself. In the same breath as
   the push, `make try-update` where Try it is running: it moves to the trunk this merge made, keeps its
   data, and seeds this slice's story, so whatever this slice made observable is reachable from the card
   at once — under `/cruise` the harbourmaster does the same after every merge it grants.""",
    ]
    stages = with_design_rungs(stages, baseline) if web else stages
    if adoption is not None:
        stages = adoption_ladder(stages, apps, layout)
    ladder = "\n".join(f"{index}. {stage}" for index, stage in enumerate(stages, start=1))
    return ladder


def hook_points() -> str:
    """The section naming where an extension's hooks fire, in the order they fire (slice 6.1)."""
    return f"""### Where an extension's hooks fire

A project may have extensions installed, and an extension attaches scripts to moments the keel owns rather
than inventing its own. Under `/sail` those moments are the rungs of this ladder, and they fire in this
order, so that a hook behaves the same with a person present as it does under a captain:

| Point | When it fires |
|---|---|
| `before-stage` | Before each rung, with the stage, slice and fairway |
| `after-stage` | After each rung, with the same |
| `boundary` | At each stage boundary, after the inbox is read |
| `before-merge` | Once, on the rebased branch, before the full gate of the **{rung_titles()["merge"]}** rung |
| `after-merge` | Once, after the slice is on trunk and pushed, with the commit |
| `before-compact` | Whenever this session's context is compacted, mid-rung |
| `after-compact` | When it resumes from a compacted context |

`slipwai hooks` lists what is attached to what, in that order. A hook that fails is reported and is never
fatal to the rung: the rung completes, and the failure is a line naming the extension, the point and the
last thing the hook printed. Nothing in this ladder depends on a hook running at all.

**Guards are the other set, and they are not the same thing.** A guard fires before a single tool call —
a search, a write, a shell command, a fetch — and may *refuse* it, which a hook can never do. A refused
call is not a failed rung: the reason comes back as the tool's result and the next thing is tried. Two of
them are not tool calls at all: `session` fires as a delegate opens and `before-stop` as one tries to end.
`scripts/agents/session.py` is where the harness's own moments arrive and where both sets are fired from.
"""

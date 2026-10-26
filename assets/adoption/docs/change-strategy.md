# How this repository changes

The delivery method is installed. The survey says what is here, `/characterise` can pin any behaviour before
it changes, and `make verify` runs the build's own commands — green on the day it arrives where the ratchet
has a baseline to hold them to, and saying plainly what is red where it does not. Nothing on this page had to
be decided for that to happen, and that was the point: the method makes every later step safe for an agent to
attempt, and only now is the question *which* step. This page is the Choose and Slice stages — four strategies, the order to change in, what
to do about data and infrastructure, and the one rule that holds all of it together.

## Four strategies, and the three decisions an ADR records

The strategy ADR records three separate decisions, and each strategy has a playbook under `__DELIVERY__/docs/strategies/`
that says what follows from it — where a new feature is built, what the spec and the mock-ups show, what the gate
refuses, and the order of the steps:

1. **Strategy** — how the change happens: *leave it*, *in place*, *strangler fig* or *rewrite*.
2. **Where the new home lives** — for the two that build one: a strangler fig grows it `inside` (new modules in the
   same deployable, the seam in code) or `beside` (a new deployable, the seam at the network); a rewrite builds it
   `beside` or in a `new-repo`.
3. **Target shape** — what the system becomes, whichever way it gets there: modules, in one deployable or as
   services, and the layering inside each (`docs/strategies/target-shape.md`).

| Strategy | What it is | When it is right | Playbook |
|---|---|---|---|
| **Leave it** | Keep the system as it is — retain, or sunset by a date — doing what security requires, with the decision reviewed rather than forgotten | The value of change is below its cost; a replacement is coming; the risk is owned by a named person | `docs/strategies/leave-it.md` |
| **In place** | Change the existing code where it stands: the platform ladder one compatible step at a time, then reshaped toward the target | One deployable that mostly works; the trigger is a platform, a delivery path or "cannot change it safely", not a capability that has to live somewhere else | `docs/strategies/in-place.md` |
| **Strangler fig** | A new home grows beside or inside the old system, frozen meanwhile (*The freeze*, below), and takes its traffic one capability at a time; `End: all` deletes the old app, `End: partial` keeps it, frozen, for the rest | The system is alive and cannot stop; there is a seam requests enter through; the old system has to go (`End: all` — the incremental rewrite) or only some capabilities have to change | `docs/strategies/strangler-fig.md` |
| **Rewrite** | A new system is built complete and replaces the old one in one rehearsed cut-over | Coexistence is impossible or costs more than it saves: no seam at all, data that cannot be split by capability, a fixed switch-off date | `docs/strategies/rewrite.md` |

Two of the four replace code, and they differ in two independent ways — how traffic moves (one capability at a
time, both systems live; or all at once) and how much moves (everything; or only what has to change):

| | One capability at a time | All at once |
|---|---|---|
| **Everything moves** | Strangler fig, `End: all` | Rewrite |
| **Only what has to change** | Strangler fig, `End: partial` | — |

**Wanting a new stack is not, on its own, a reason for a rewrite:** a strangler fig with its new home `beside` and
`End: all` gets the same outcome, with the risk going down one capability at a time. A rewrite's ADR says why one
cut-over is right. A programme is allowed to change its mind — a strangler that finds one context is the whole
system may become a rewrite of it — but not to do neither and call the refactoring a strategy.

**First under every strategy: the build floor** (`docs/strategies/build-floor.md`). Each deployable builds from a
clean clone, through one declared build, with every dependency and tool version written down. In place and a
strangler fig `inside` bring the old toolset fully up to date, because new work is built with it; a rewrite and a
strangler fig `beside` pin the old build as it is, because it is being replaced.

## The freeze, which the strangler is not a strangler without

A strangler grows beside a system that is standing still. Where the old system keeps gaining features, the
new home is chasing a target: every capability that moves has to be re-read against what the old one did
last fortnight, the pinned tests go stale on somebody else's release, and the retirement ledger stops
meaning anything — a row that says *moved* is about a capability the old system has since extended. That is
how a strangler quietly becomes a second system beside the first, which is the one failure this page exists
to prevent.

So the strangler has a precondition, and it is an agreement rather than a technique: **no new features in
the legacy system, bug fixes only, no schema changes**, for as long as capabilities are moving. Somebody
with the authority to hold other teams to it agrees to it, by name, and it is recorded on the strategy ADR
as one line:

```
Freeze: agreed — <who agreed it, and when>
```

Where nobody will agree to it — and often nobody will, which is an answer and not a failure — that is
recorded too, with what the programme does instead:

```
Freeze: absent — <what is done instead: re-pinning every legacy release before the next capability moves,
                 a shorter programme, fewer capabilities, a different strategy>
```

`/strangle` asks for the line before the first capability moves and will not invent either answer. A freeze
nobody recorded is one nobody agreed to.

## Be honest about the event model

**Event Modeling and event sourcing are two decisions, and only one of them is hard to reverse.** The model
— the actors, the timeline, the four patterns, the slices — is the same on every rung, and a repository
that was here already pays for it only in the understanding it was going to need anyway. The **rung** is
the other decision, taken per service and recorded in `project.json` as `eventSourced` from the
`write-model` axis: `events`, where the log is the truth and state is a fold of it, or `state`, where the
service keeps current state and the events the model names are contracts raised after the write. That one
cannot be walked back once a service holds data — state cannot be turned back into history it never
recorded — while a log folds down into tables whenever somebody decides.

So a capability that moves out of the code that was here is **modelled from the day it moves, and
event-sourced only where its past is worth keeping**. For the first few capabilities it rarely is, and the
honest answer is **rung 2** of the ladder — explicit returns → **in-process events** → outbox → event
sourcing. That is `--write-model state`: the new home keeps current state, the events are on the timeline
because that is how the slice was found at all, they are raised after the write, and a publisher — an
outbox, the bus, change data capture — is earned when something actually reads one. There is
**no genesis event** on that rung, because there is no log for one to open; the capability's data reaches
its new home by change data capture from the legacy store or by an outbox written in the legacy system's
own transaction, and that is the whole of the data move.

Where the new home is `--write-model events`, and only there, its history starts at a **genesis event** that
records the state the legacy system handed over. Nothing before that genesis is invented.

Neither rung licenses the one thing that is always wrong: **nothing in the legacy tables, and nothing in
their history, becomes an event by being renamed.** The code that was here is an **external system** in the
model where only its outputs are read — an actor and a swimlane, its events marked `external: true` — and a
**state-stored service of this project** where somebody has modelled its behaviour against the code.
`/survey` says the same in the event-modelling profile; do not promise more than this.

## Separate the layers, and do one at a time

Most programmes mix six changes into one and then cannot say which one broke it. The order below is
from the cheapest and most mechanical to the one only a person can decide, and each is a stopping point that
leaves the system better than before.

Under the ladder is its floor: **a build that declares its dependencies and fetches them** — Maven or Gradle
through the wrapper for Java, the package manager for everything else. An Ant build with its jars committed is
below it, and no rung above can be taken from there: nothing dates a jar by its name for long, nothing audits
it, and no CI runner has the tool without being told. So where the survey finds one, the programme opens with
the move — a `pom.xml` that declares each committed jar by its coordinates, sources under `src/main/java`, the
same artifact out of `./mvnw -q package`, then `/survey` reads the tree as Maven — and it is the one step no
strategy paces differently: *leave it* still takes it, because it is the least the method holds any repository
to. The rungs:

1. **Language version** — the runtime the code is compiled or interpreted against. Java 8 → 21, Python 2 →
   3, .NET Framework → .NET. Largely mechanical: **OpenRewrite** recipes for Java (`UpgradeToJava21` and the
   framework migrations beside it), `pyupgrade` and `futurize` for Python, the .NET **Upgrade Assistant**
   for C#. Point the agent at the recipe, not at the files: a recipe applied is a diff to review; an agent
   hand-rewriting a thousand files is a thousand chances to be wrong.
2. **Framework** — Spring 4 → Boot, Struts → anything, AngularJS → Angular through `ngUpgrade`'s hybrid
   mode, Express 3 → 4. OpenRewrite has recipes for the Java rungs (`SpringBootUpgrade`); the others are
   guided and pinned by `/characterise` at the HTTP boundary.
3. **Packaging** — WAR on an application server → an executable jar, a `.NET Framework` site → a self-hosted
   process, a set of scripts → a package. The survey records `packaging: war` where it sees one; this rung
   is where it stops mattering.
4. **Runtime** — VM → container, or the container base image the packaging now allows. The first `Dockerfile`
   is written here, and `make verify` grows a step that builds it.
5. **Host** — where it runs: on-premises → a cloud, or one cloud → another. `docs/deployment.md` records the
   infrastructure's home and the rule (import or reference, never manage a resource in two places); the
   factory's `aws` target is one possible destination for a *generated* service, and never a claim about the
   legacy system's host.
6. **Architecture** — the strangler, the modular monolith, the contexts. Last, because every rung above it is
   cheaper with a green gate and characterisation tests, and none of them needs an architectural decision.

A programme whose `why` is "end-of-life runtime" stops after rung 1 or 2 and has succeeded. One whose `why`
is "cannot ship" usually finds its problem at rung 6 and needs the five below it first. The survey reads
which of these is actually out of support — the runtime the tree pins, the framework and test framework the
manifest declares, the images a `Dockerfile` starts from — and dates each against the factory's support table
(`__DELIVERY__/survey/structure.md`, *What it runs on*); a product past its end of life goes at the head of the
recommendation's `before` list whatever `why` says, with the way up named for it, and is the map's Platform
row climbing `inventoried` → `supported` → `audited`. `/survey` re-dates on the day it runs, so a runtime that
leaves support while the programme goes on shows up without anyone looking.

## Data

- **Schema ownership is the usual blocker.** `project.json`'s `database.schema` records where the schema is
  versioned: `here`, `elsewhere` (a repository that is now the contract), `unmanaged` (a DBA, a console) or
  `none`. Nothing is moved until somebody can answer who else reads these tables; the answer is written in
  `docs/deployment.md` beside the infrastructure.
- **Migration tooling, where there is none.** Flyway or Liquibase for the JVM, Alembic or Django's for
  Python, Prisma or knex for Node, EF migrations for .NET, `golang-migrate` for Go — recommended, not
  scaffolded: the tool belongs to the ecosystem the schema lives in, and a baseline migration that matches
  the database as it is (`baseline-on-migrate` in Flyway's words) is the first migration, never a rewrite of
  the schema from memory.
- **Dual-write is a trap.** Two systems each writing the same fact drift the first time one of them fails.
  Move data with **change data capture** from the legacy store, or an **outbox** written in the legacy
  system's own transaction, and let the new home read that. One writer per fact, always.
- **Rehearse the migration.** Every cut-over is run against a copy first, with a **reconciliation report**
  — counts, sums, samples — between the old and new stores, and a **rollback plan** that has been executed
  at least once in rehearsal. A migration that has not been rolled back in rehearsal has no rollback plan.
- **Dual-run, then cut over.** The new home serves reads in shadow, its answers reconciled against the old
  system's, before it serves anything to an actor; then the flag flips one capability at a time.
- **Some things do not move.** Data residency, audit retention, regulatory constraints on where a record may
  live — find them in the survey stage and write them down, because a strategy that ignores one is cancelled
  the day somebody notices.

## Infrastructure

Three cases, and one rule. **ClickOps**, nothing describes the infrastructure: describe it before anything
imports it, because describing is safe and importing what is not described is how two things end up
managing one resource. **A platform team's IaC in another repository**: that repository is the contract, and
what this one hands over — a tag, an image, a ticket — is written in `docs/deployment.md`. **IaC in this
repository**: the factory adds nothing to it and manages none of it. The rule in all three: **import or
reference** — `tofu import`, data sources — and never manage a resource in two places. `docs/deployment.md`
records which case this is and where the description lives.

## Every step shippable, every step reversible

Most programmes are cancelled halfway. Slice the programme so that stopping at any point leaves the
system better than it was: a runtime upgrade shipped is a win whether or not the strangler ever starts; a
capability moved and routed is a win whether or not the next one moves. A step that only pays off once the
whole programme finishes is a step to split. And every step is reversible while it is fresh: the flag flips
back, the router points back, the migration rolls back — which is why the flag, the router and the rollback
are decided in the slice's plan and not after the code exists.

## The agent's context

A legacy codebase is larger than any context window, and an agent that reads files one at a time in it will
be confidently wrong. Before the first slice: the survey (`survey/survey.md`), the code index
(`./init --extension codegraph`), and a module map — which directories are which contexts, in the agent's
guidance. `/characterise` before each change, `/strangle` for each capability that moves, and the ledgers
they keep are what let a later session pick up where this one stopped.

## The retirement ledger

`__DELIVERY__/retirement.md` is the record of the strangler: one row per capability, from where, to where,
routed by what, pinned by which tests, and its status — *routed*, *moved*, *retired* or *removed*. `/strangle`
writes the rows; the programme is finished when every row is *removed* and nothing else is left. A ledger
that stops being written is the first sign that a programme has quietly become a second system beside
the first, which is the one outcome worse than either.

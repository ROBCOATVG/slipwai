# How this repository changes

> **Experimental.** This page arrived with brownfield adoption and will change as real programmes teach it
> what it gets wrong. What surprised you belongs on the public issue tracker.

The delivery method is installed. The survey says what is here, `/characterise` can pin any behaviour before
it changes, and `make verify` runs the build's own commands — green on the day it arrives where the ratchet
has a baseline to hold them to, and saying plainly what is red where it does not. Nothing on this page had to
be decided for that to happen, and that was the point: the method makes every later step safe for an agent to
attempt, and only now is the question *which* step. This page is the Choose and Slice stages — three strategies, the order to change in, what
to do about data and infrastructure, and the one rule that holds all of it together.

## Three strategies, not two

| Strategy | What it is | When it is right | What it needs |
|---|---|---|---|
| **Strangler fig** | New capability grows beside the old system and takes its traffic one capability at a time, until the old system serves nothing and is removed | The system is large, alive and cannot stop; there is a seam requests enter through; the business trigger (`project.json`'s `why`) is a capability that has to change, not a platform that has to go | A routing seam, a data strategy that is not dual-write, and the retirement ledger |
| **Modular monolith in place** | The code is restructured behind its characterisation tests — contexts found, seams made, layers separated — without a second deployable or a routing seam | The system is one deployable that mostly works, the trigger is "cannot change it safely" rather than "cannot run it", and the team is small | `/characterise` before every move, `refactoring` and `improve-codebase-architecture`, and patience; the import gate's rule can be adopted context by context (`"layout": "hexagonal"`) |
| **Rewrite** | A new system replaces the old one, and the old one is switched off | The system is small enough to hold in one head; there is no seam to strangle through; the platform is dead and cannot be upgraded in place | Characterisation of everything the rewrite claims to preserve, a cut-over plan with a rollback, and the honesty that most rewrites are cancelled halfway |

Rewrite is the exception, chosen when the other two cannot work, not the default because it is cleaner.
A programme is allowed to change its mind: a strangler that finds one context is the whole system may
become a rewrite of that context, and a rewrite that turns out to have a seam after all may become a
strangler. What is not allowed is to do neither and call the refactoring a strategy.

## Be honest about the event model

The generated method carries Event Modeling and event sourcing as one bundle, and the factory's own position
is that "start standard and adopt events where a subdomain earns it" is an option that mostly does not
exist: state cannot be turned back into history it never recorded. Brownfield does not change that. What
event modelling means here is **new slices at the edge**: a capability that moves to a new home is modelled
as events from the day it moves, with its history starting at a **genesis event** that records the state
the legacy system handed over, or with a change-data-capture stream translating the legacy tables into
events the new home reads. The legacy system itself is an **external system** in the model — an actor and
a swimlane, its events marked `external: true`, never a set of events invented by renaming its tables.
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

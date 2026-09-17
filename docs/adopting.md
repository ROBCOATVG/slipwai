# Adopt an existing repository

> **Experimental.** Everything on this page is new and will change shape while real repositories teach it what
> it got wrong. As [AGENTS.md](../AGENTS.md#versioning-is-not-optional) defines the word: the files `adopt`
> writes, the facts `project.json` records and the questions it asks may change
> in a MINOR release, every place this reaches you says so until it stops being
> true, and `slipwai migrate` brings each change to an adopted repository with
> a catch-up note saying what to do. Report what surprised you on the public
> issue tracker — a detection that was wrong, a gate that went red on day one,
> or a sentence a page should have had.

New here? [Adopt an existing repository — learning path](learn-adopt.md) is the short route: install, first
session with terminal screenshots, then upgrade, migrate and `/catch-up`. This page is the full reference.

Most of the projects this method will reach already exist. `slipwai generate` makes a repository; `slipwai
adopt`, run at the root of one the factory did not make, installs the method *around* it — the gate, CI for
the gate, the skills, commands and documentation, the agent projections, and a `project.json` that records
what was there rather than what was chosen. It is **adopt the method**, not **generate the skeleton**: nothing
about strangler-versus-rewrite has to be decided first, and what it installs is what makes any later step
safe for an agent to attempt.

## What it does

**Survey.** It reads the tree and proposes what it finds — and where nothing in the tree starts a build it can
read, it says so by name, lists the manifests it does read, and stops before asking a question ([`src/slipwai/survey.py`](../src/slipwai/survey.py),
with [`ecosystems.py`](../src/slipwai/ecosystems.py) as the table of what it can recognise): every directory
that builds — Node, Python, Go, Maven, Gradle, Ant, .NET, PHP, Ruby, by the manifest that starts the build — with
its language, the toolchain pin the tree carries, and the command its own tools run for each of the eight
Make targets a service owes (`install lint typecheck test integration adversarial audit mutation`). A target
the ecosystem has no answer for is `null`: a written no, never a guess. It also reads whether CI, containers
and infrastructure code are here, whether a database schema is versioned here and with what, and which
database drivers the dependency manifests name. Every fact carries the file that said so.

**Ask.** In a terminal, each finding is a question with the finding as its default: wrap this directory as
an application — its build joins the gate? what is it — a `service`, a `library`, a `tool`, a `tests` suite,
or an `application` whose role nobody has established? this language? these commands, one per Make target?
what does it own? where is the database schema versioned — `here`, `elsewhere`, `unmanaged` or `none`? where
is the deployment infrastructure described? where does CI run — `github`, `gitea`, `gitlab`, `other`, `none`?
how does a change reach production today — `pipeline`, `scripted`, `manual`, `unknown`? why is this work
happening? Every question says what the answer does, and a list question stands above its rows while they
are live. Enter accepts (`confirmed`), another answer overrides (`overridden`). Three of those the tree only
sometimes answers — what a directory is for, which forge, how a release happens — and where it does not, the
default is the honest one: `application`, and `unknown`, recorded as `unrecorded` rather than guessed. The
survey proposes them only from a file that says so: a `Dockerfile` or a start script makes a service, a `bin` a
tool, a `main` a library, a `tests/` name a suite; a CI file or the remote's host names the forge; a CI job
that deploys, or a deploy script, says how a change ships. `--yes` asks nothing and takes every proposal as
`detected`; a flag overrides one answer either way and is always `overridden`. Outside a terminal without
`--yes` it refuses rather than guessing.

**Wrap.** It writes the method's material under `delivery/` (`--delivery` names another directory), beside the
code, exactly as a generated project would have it at the root ([`layout.delivery`](services.md)): the
Makefile, `init`, the gate scripts, the skills, the commands, the documentation. Root-relative pointers in
that material are respelled, the scripts find the repository root by `project.json`, and the gate's CI
configuration is written **for the forge found** — `.github/workflows/verify-delivery.yml` for GitHub or Gitea
(which run the same workflows), setting up the toolchains the wrapped applications recorded;
`delivery/ci/verify-delivery.gitlab-ci.yml` for GitLab, a job to `include:` from their own `.gitlab-ci.yml`;
nothing at all for Jenkins, Azure, Bitbucket or another (`other`), or where the repository has no CI (`none`),
and the report says to have that CI run `make -f delivery/Makefile verify`. Never a GitHub workflow into a
repository whose CI is somewhere else — beside whatever CI the repository already has, never in its place. Three root files are the repository's
own and are never written over: `README.md` is left alone, and `AGENTS.md` and `.gitignore` each receive a
marked block, appended once. `.claude/settings.json` is written only where there is none. The whole
adoption is one commit by the factory, which is how `replay` and `migrate` find their base later;
`git reset --hard HEAD^` undoes all of it.

**Ratchet.** Their linter and type checker are usually red on day one, because the rules arrived after the
code — and sometimes their test suite is too. `verify` runs each recorded `lint`, `typecheck` and `test`
through `scripts/ratchet.py`, which records the findings that are there into `delivery/baseline.json` on the
first local run and from then on fails only on a finding that is new — never on CI without a committed
baseline, and never for fixing something; `make ratchet-tighten` re-records what is left. A red `test` is the
one exception to day-one green: the first run stops, shows the failures and says what quarantining means, and
`ratchet-tighten` — once somebody has read them — records it as **quarantined**: the gate passes on the state it
recorded and says so on every run, until the suite is green and `ratchet-tighten` clears it. A new failure is
new whether the output names a file at a position or the runner names the test (`--- FAIL: TestX`,
`not ok 3 - adds`, `FAILED tests/test_a.py::test_b`, Surefire's `[ERROR]   ShopTest.adds`).
[Gates](verification.md#adopted-repositories-the-ratchet) has the detail. A suite too slow for `verify` is
recorded as `test-full` (`--command NAME:test-full=…`) and gets its own target. The import gate holds a wrapped
application to the hexagonal rule only where `--hexagonal NAME` declared that it keeps the layers.

**Smoke.** The one command the gate cannot compose from the eight is the application started and proved to
answer. It is recorded as `smoke` (`--command NAME:smoke=…`, or by `/ground`, which asks how each application
starts and what proves it answers, once `survey/running.md` says so from a real run), never proposed by the
survey; `null` is a written no — an application nobody can start anywhere but production — with the reason in
`running.md`. `make smoke` runs it, `make ci` and a `smoke` job in the gate's workflow run it in CI, and `verify`
never does, since it needs what the application needs. An application nobody has proved starts is the
programme's step right after the build, and `/drive`'s Pin stage refuses to change one until somebody has: the
first four real adoptions each merged a slice, converged and green, that had stopped the application starting,
because no suite builds the context.

**Choose and slice.** `delivery/docs/change-strategy.md` — an asset of the adoption
([`assets/adoption/docs/change-strategy.md`](../assets/adoption/docs/change-strategy.md)), because a generated
project has no code that predates the method — is the essay: three strategies rather than two (strangler fig,
modular monolith in place, rewrite) and when each is right; the factory's honest position on event modelling in a
brownfield (new slices at the edge, genesis events or change data capture, the legacy system as an external
system); the order to change in — language, framework, packaging, runtime, host, architecture — with
OpenRewrite named for the Java rungs and the equivalents for .NET Framework, Python 2 and AngularJS; data
(schema ownership, migration tooling recommended and never scaffolded, dual-write as the trap, CDC or outbox,
rehearsed migrations and reconciliation, what cannot move); infrastructure's three cases and one rule; and
every step shippable and reversible. `/strangle <capability>` is one turn of the strangler: it refuses to move
what `/characterise` has not pinned, decides the routing seam for the target the project has, decides the data
strategy, names the new home — a generated service beside the code, or a context inside it — and writes the
row in `delivery/retirement.md`, the ledger whose every row must read *removed* before the programme is done.

**Build wrappers.** A Maven or Gradle build is recorded through its wrapper — `./mvnw -B -q test`,
`./gradlew -q test` — whether or not the repository has one yet, and where it has none `adopt` writes it beside
the build file: the Maven Wrapper every generated Java project carries, or the Gradle Wrapper vendored under
`assets/adoption/wrappers/gradle/`. The wrapper fetches its pinned Maven or Gradle on first use, so the laptop
that adopts the repository and the runner that verifies it need a JDK and nothing else; a repository that built
from the IDE, with no `mvn` on any PATH, gets a gate that runs. The files are the repository's own from then on
(committed with the adoption, not in `.written`); the pinned version is an edit to the properties file. A
command overridden to plain `mvn` or `gradle` opts out, and no wrapper is written. An Ant build (`build.xml`, the
NetBeans layout with `nbproject/`) has no wrapper to write: it is recorded as `ant -q compile` for the targets it
defines, `install` a written no because its jars are committed, and the gate's runner installs Ant until the build
moves — which is the programme's first step, because a build that declares its dependencies is the floor under the
ladder (`docs/change-strategy.md`), and the Platform row cannot pass *inventoried* while the jars are committed.

**Report.** The first line says *experimental*. Then what was wrapped and what each is (or that its role is
not recorded), how many targets have a command, what was appended, which forge was recorded and what was
written for it — or that nothing was, and what to run instead — how a change reaches production (or that
nobody has said), any tool a recorded command starts with that is not on this machine's PATH (the gate will
stop there, so it is said before the first `verify` rather than by it), and the next steps in order — `init`
first, always, as a generated project's README has it:

```sh
./delivery/init                             # Spec Kit, and the skills and commands projected into the agent it asks for;
                                            # `--integration claude` names it, `--extension codegraph` indexes the code
make -f delivery/Makefile verify            # green on day one is the promise; the first run records the ratchet
                                            # baseline — commit delivery/baseline.json with what init wrote
# add `-include delivery/Makefile` to the root Makefile, and `make verify` is one word again — or, where the
# repository had no Makefile, `adopt` wrote one that includes it, and `make verify` is one word already
```

`delivery/docs/adoption.md` in the repository says what was wrapped, what that forfeits, and where each fact
came from; `delivery/survey/survey.md` is the survey with its evidence.

## Every flag

Bare, in a terminal, `slipwai adopt` asks with the survey's findings as defaults. Every question it asks has
a flag that answers it instead, which is the form for a script, for CI, and for the second repository that
gets the same three corrections as the first. A flag is recorded `overridden`, whether or not it agrees with
what the survey found — it is a person's answer either way, and the record says so. Outside a terminal,
`--yes` is required whatever else is passed: without it there is a question left to ask and nothing to ask
it of, so `adopt` refuses rather than guessing.

| Flag | Answers |
|---|---|
| `--yes` | Everything, as the survey found it — nothing is asked, and each fact is recorded `detected` |
| `--refresh` | In an adopted repository: survey again, refresh what was only detected, report what disagrees with what a person decided, and regenerate what the record drives. This is what `/survey` runs |
| `--name NAME` | The project's name. Default: the directory's |
| `--profile` | `standard` or `event-modelling`. Default: `standard` |
| `--target` | `existing` — this deploys to infrastructure it does not own — or `none`. Default: `existing`, unless the infrastructure is `none` |
| `--delivery DIR` | Where the method's files go. Default: `delivery` |
| `--why TEXT` | The business trigger behind this work, recorded in `docs/adoption.md` |
| `--skip NAME` | A found application not to wrap. Repeatable |
| `--language NAME=LANGUAGE` | Override a found language. Repeatable |
| `--kind NAME=KIND` | What a found application is: `service`, `library`, `tool`, `tests`, or `application` — the last being the one that says nothing, a buildable directory whose role nobody has established. Repeatable |
| `--purpose NAME=TEXT` | What an application owns. Repeatable |
| `--command NAME:TARGET=COMMAND` | Override one recorded command; `-` records none, which is the written no. The target is one of the eight a service owes, or `test-full` for a suite too slow for `verify`, or `smoke` for the command that starts the application and proves it answers. Repeatable |
| `--hexagonal NAME` | An application that keeps the hexagonal layers, so the import gate holds it to them. Repeatable |
| `--database` | Where the schema is versioned: `here`, `elsewhere`, `unmanaged`, `none` |
| `--database-repository URL` | Where *elsewhere* is. Given on its own it records `elsewhere` as well |
| `--infrastructure` | Where the deployment infrastructure is described, from the same four |
| `--infrastructure-repository URL` | Likewise, and likewise implying `elsewhere` |
| `--forge` | Where CI runs — `github`, `gitea`, `gitlab`, `other`, `none` — which decides what shape the gate's CI configuration can take. Default: what the tree or the remote says |
| `--release` | How a change reaches production today: `pipeline`, `scripted`, `manual`, `unknown`. Default: what the tree says, and `unknown` recorded as `unrecorded` where it says nothing |

## The map

Every adopted repository gets `delivery/docs/convergence.md`, rendered from `project.json`'s `convergence`
rows and never written by hand: one row per axis — path to production, integration, safety net, structure,
platform, constitution, data, infrastructure, strategy — with the rung this repository stands on, the rung a
generated project sits at, the evidence, what slice is planned to move it, and where the row came from. A rung
is claimed only from a fact the record holds: a recorded test command puts the safety net at `tests-exist` and
no higher, a declared hexagonal layout under `apps/` with a type check puts structure at `typed`, a release
path a file or a person gave places the path to production. A rung nothing establishes reads as the ladder's
floor with `unrecorded` provenance — a question, not a gap. `/survey` re-reads the tree and redraws the page
under the provenance rule: a row the tree placed follows the tree, a row a person placed stands, its planned
slice with it. `make check-convergence`, in `verify`, fails a row the tree contradicts — a `tests-pass` while
the ratchet quarantines the suite, a `ratified` constitution that is still the template, a `named` structure
with an application whose role is open — and a page rendered from other rows than the record now holds. The
end of the ladders is `slipwai converge`: every row at its target, and the repository a generated one.

**The constitution is a journey.** A repository on long-lived branches cannot truthfully ratify "trunk MUST be
releasable at every commit", so the constitution template an adopted repository drafts from is the profile's
own with a difference: every principle whose axis on the map stands below the rung it comes into force at is
written as *a target, not yet in force* — the rung this repository stands on, the rung the principle needs,
two lines only this repository can write about what holds today, and the principle itself quoted for the day
it comes into force, under a marker `<!-- journey: <key> at <rung> -->`. `check-constitution` holds the marker
to the map: a marker at another rung is drift, a principle written in full while the map says otherwise is
the fiction this exists to prevent, and a principle the map says is in force is asked for in full. `make
constitution-requirements` — and the `/speckit-constitution` hook — print each target as a target. The
principles that hold from day one whatever the code — agent change meets the same bar, observability,
security, versioning, ADRs, quality gates, governance — are asked for in full from the first edit.

## The question set

The survey reads what a file says; `adopt`'s interview asks about the rest in the terminal, and `--yes` asks
nothing and records `unrecorded`. The question set proper is `/ground`, run by the coding agent — on its own
after `./init` and before the first slice, or by `/drive`, whose Ground stage *is* this command for the rows a
slice touches: the ladder asks, records, and continues in the same run rather than stopping. It walks the
map one row at a time: the survey's evidence and every rung's meaning first, so the person places themselves on a
ladder rather than answering a quiz; one question, wait, write, confirm, next. Each axis has its question and the
place its answer is written — the release path and whether it is the only way a change can reach production;
how work is integrated, which nothing in a tree can say; whether the team would ship on the recorded tests; what
each buildable directory is for; where the schema and the infrastructure live; why the work is happening and,
as a question of its own with the five strategies named and the recommendation one of them, how far it should
go — the word `Accepted` on the deciding ADR is the person's, never the agent's. A row the survey placed
(`detected`) is asked about like an `unrecorded` one: it is the tree's reading, not an answer, and only
`confirmed` and `overridden` mean a person has spoken. The constitution is not asked, since only
`/speckit-constitution` and the gate establish it. A
rung is still claimed only from a fact: the person is the fact for what only they can know, and where the tree
can contradict an answer — a quarantined suite, a template constitution — the tree wins and the command says so.
"I don't know" stays `unrecorded` and is said. Then `/survey` redraws the pages and re-makes the strategy
recommendation from what was said, `make verify` holds every row written to the tree, and the answers are one
commit. The command is regenerated with the record, so it opens with the map as it stands.

## The architecture view

Beside the survey, every adopted repository gets `delivery/survey/structure.md`: per wrapped application, where
anything starts (a `start` script, a `bin`, a console script, a main package, a `Program.cs`, an application
class, a container's `CMD`, a Procfile line — each from the file that says so), what it is made of (its top-level
directories, with file counts and languages), what it declares it depends on (from its manifest), what it runs on
(the runtime, frameworks and images the tree pins, each dated against the factory's support table — a snapshot of
endoflife.date under `assets/adoption/support.json`, refreshed by `scripts/refresh-support.py` — with the way up
named for each product past its end of life: OpenRewrite's recipes for Java and Spring, `jakarta.servlet` and
Tomcat 10.1+ together, JUnit 5 with the vintage engine, the current LTS for Node, .NET's Upgrade Assistant), where change
happens (the files the last commits touched most, with the window; too little history says so), and what the
graph says. That last section is fed by [CodeGraph](https://github.com/colbymchenry/codegraph) where
`./init --extension codegraph` has indexed the repository: the factory reads `.codegraph/codegraph.db` — the
SQLite database `codegraph init` writes, whose `nodes`, `edges` and `files` tables are what its own `--json`
commands print — and lists the files the most other files call, import or reference, and the files that reach
the most others. No index, and the page says how to build one. The page ends with what the reading means for
the map — the Structure row's rung marked on its ladder, and what each rung asks of this repository — and
where `/strangle` would cut: an entry point with little of the shared core behind it; the most-depended-on
files last to move and first to pin. `/survey` rewrites it with the rest.

## The recommendation

`delivery/docs/change-strategy.md` opens with the strategy this repository's trigger and its map recommend, written
on the map's Strategy row as well. The trigger — `project.json`'s `why` — is read for what it names: a
**platform** (end of life, unsupported, a version) recommends changing it in place and stopping after the language
and framework rungs; a **delivery** problem (cannot ship, releases take, outages) recommends the path to production
and the safety net first, because a problem that survives those is the only one the architecture owns; a **host**
problem (cost, licence, cloud) recommends rungs 3 to 5 with the architecture unchanged; a **change** problem
(cannot change safely, coupled, untested) recommends the modular monolith in place; a **capability** problem (a
new market, scale, teams) recommends the strangler fig. A trigger that names none of these, or no trigger at all,
recommends **leaving the architecture where it is** — a first-class answer, not a footnote — and the delivery
rungs regardless. Whatever the strategy, the map lists what has to hold before anything architectural is worth
starting: a pipeline where the path to production is below one, a green suite where the safety net is, every
role recorded, a seam and a data answer for the strangler, pinned seams for either architectural strategy.
Rewrite is never recommended; a person decides it and says why the other two cannot work. The tree is read
for a platform problem too, not only `why`: every product `survey/structure.md` dates as out of support leads
the `before` list — *the platform in support*, with the way up for each — whatever strategy the trigger names,
because rungs 1 and 2 of the ladder come first; and where `why` names nothing, or nothing at all is recorded,
an expired platform is the recommendation itself, *change it in place*. This is the map's Platform row —
`unknown`, `inventoried`, `supported`, `audited` — and `/survey` reads it against the table on the day it runs,
so a runtime that leaves support while the work goes on moves the row down without anyone looking; the reading is
re-dated only when a product, a version, a status or the table moved, so the date is the day something changed.
A version that moved is said in the report — as a disagreement where the Platform row planned nothing, since a
platform move is a slice of its own on that row and never a side effect of another.

A recommendation is not a decision. The decision is an accepted ADR under `delivery/docs/adr/` carrying a
`Strategy:` line, read from the tree like every other fact: `/survey` reads it, the row moves to `decided` — or to
`done`, when the strategy was to leave it or every retirement-ledger row reads *removed* — and
`make check-convergence` fails a `decided` row with no such ADR behind it. `/strangle` refuses to move a capability
until the decision says `strangler-fig`; the command carries what the record says today, so the refusal names the
recommendation and the way to decide rather than a rule.

## What it records

`project.json` gains, beside what a generated project's has ([Services](services.md) describes the fields):

- `"origin": "adopted"`, so every command knows the repository is not the factory's.
- One deployable per wrapped directory, recorded `"generated": false`: its `kind` — `service`, `library`,
  `tool`, `tests`, or `application` where nothing said — its `language` (catalog or not), its `commands`, its
  `toolchain` (`kind`, `version`, `ecosystem`, and `packaging` where a Maven build makes a WAR), its `purpose`,
  and `provenance` per field. No `selection`, no `port`, no skeleton.
- `why`, the business trigger, recorded like a service's purpose because it decides the change strategy more
  than the code does.
- `database` — `schema` as `here`, `elsewhere`, `unmanaged` or `none`, the schema tools and drivers found,
  the repository where `elsewhere` — and `infrastructure` the same way. `elsewhere` is never proposed: only a
  person knows about another repository.
- `ci`: the `forge` (`github`, `gitea`, `gitlab`, `other`, `none`), the `gate` written for it or `null`, the
  `evidence`, and `provenance`.
- `release`: how a change reaches production — `path` as `pipeline`, `scripted`, `manual` or `unknown`, the
  `evidence`, and `provenance`.
- `platform`: what each wrapped application runs on, dated — the runtime from `toolchain.version`, the frameworks
  and test framework from its manifest, the images a `Dockerfile` starts from — each `product` with its `version`,
  the table's `cycle`, a `status` (`supported`, `ending`, `end-of-life`, `unknown` for a cycle the table does not
  know), its `eol` date and the file that pins it; the table's `snapshot` date and the day it was `dated`.
- `strategy`: the strategy `recommended` from `why` and the map (`leave-it`, `in-place`,
  `modular-monolith`, `strangler-fig`), the `trigger` it read, `because`, what has to hold `before`, when it
  `stop`s, and what an accepted ADR `decided` with its path — `null` until one does. `unknown` carries `unrecorded`: the fourth provenance, the written form of
  "nobody has said", which the next survey that can say fills in and `/drive` asks about before the first slice.
- `convergence`: the map's rows — `axis`, `rung`, `target`, `evidence`, `provenance`, `planned` — as above.
- `survey`: the CI files, containers and root files the tree carried.
- `layout.delivery`, where the material went.
- `target`: `existing` wherever the repository deploys somewhere — the infrastructure is `here`, `elsewhere` or
  `unmanaged` — and `none` where it is `none`; `--target` overrides. `existing` provisions nothing and offers
  what `none` offers; it turns on `delivery/docs/deployment.md`, written from the infrastructure facts, and the
  release-constraint rung of `/drive` ([Project shape](axes.md#production-target)).

Three files under `delivery/survey/` are the repository's own from the first commit, never listed in `.written`
and never rewritten: `pinned.md`, what `/characterise` has pinned; `running.md`, how each application is
actually run once somebody has proved it — the `run-the-app` skill points there and holds nothing itself, since
the skill is the factory's and is replaced whenever the factory moves; and `../retirement.md`, the strangler
fig's ledger. `/survey` removes a file the factory wrote that the record no longer calls for — the gate for a
forge the record has left — and says so, rather than leaving it for the next survey to mistake for the
repository's own CI. Any other file the factory wrote can be taken over: delete its line from `.written`, and
from then on it is the repository's — `/survey` leaves it alone and says `owned:`, the next `.written` no longer
lists it, and a newer factory's change to it meets yours in `slipwai migrate`'s three-way merge. The gate's
workflow runs on pushes to the branch `.git` says the repository lands on (`ci.branch`, `main` where nothing
says) and on every pull request; the forge it was written for stands while the gate is the only CI in the tree,
since the survey leaves out what the factory wrote and would otherwise read no CI at all.

## Quick wins, and the programme

The survey also reads for the handful of things that are both big and cheap to fix — a credential written in a
file (a value shaped like a known key anywhere; a keyed literal in a configuration file, Spring's
`<property name="password" value="…"/>` and `<value>` forms included; a keyed quoted literal in source), IDE and build output under version control, a dependency repository fetched over plain HTTP, a
lockfile the package manager would write and nobody committed, a binary archive tracked — and says each with the
file that shows it and the fix, never the value. They are proposals: `survey/survey.md` carries them under *Big
issues that are quick wins*, the report says them first, and `/survey` reads the tree again so a finding fixed
disappears rather than being ticked off.

Those, a build below the floor (Ant with its jars committed, whose step is Maven or Gradle through the wrapper),
an application nobody has proved starts (its run path written in `survey/running.md` and `smoke` recorded, before
any slice changes code that was here), the products out of support, the ladder's rungs the tree shows are behind (a WAR, no container, an
undescribed host, an unversioned schema) and the tooling an ecosystem has and nothing here runs (Checkstyle,
OWASP dependency-check, Ruff, mypy, pip-audit, govulncheck, RuboCop) are one ordered list, **the programme**,
under `docs/change-strategy.md`'s recommendation. Each step is paced by the decided strategy: a quick win is now
whatever the strategy; the build is first whatever the strategy, since nothing above it can be fetched, dated or
audited until it is done; the platform and the rungs are a big bang per rung under changing in place or a
modular monolith, over time under a strangler fig — the new home current from day one, the old home only if it
stays — recorded but not scheduled under *leave it*, and *decide the strategy first* while nothing is decided;
a tool is one slice, green through the ratchet before it is recorded as a command, and never added uninvited.
`/drive`'s Convergence stage offers from the top of that list before the map's rows, a secret the same day; the
whole of it is derived again on every `/survey`, so what the tree shows done is gone.

## What it forfeits, and says so

A language this factory generates (`typescript`, `python`, `go`, `java`) can have a generated service added
beside the existing code with `add-service --language …`, which is the strangler's first slice. A language it
cannot generate gets no skeleton, no axis to answer, no production image, no `aws` target and no hexagonal
import rule — only the gate composed from its recorded commands, and the skills, commands and documentation,
which speak of every language. The report and `delivery/docs/adoption.md` say which applies.

## The loop, with adoption phases

Adoption is a phase of the delivery loop, not a step before it. `/drive` in an adopted repository walks the
same ladder a generated project's does ([The delivery loop](delivery-loop.md)) with three more things in it,
each a stage so that "enter at the first incomplete stage" reaches it:

- **Ground**, before Principles. `delivery/docs/convergence.md` exists and `make check-convergence` is green —
  no map, no principles. The slice names the rows it touches, and a row whose provenance is `unrecorded` on one
  of those axes is a question for the person before anything else, the release path first of all: a slice with
  no known path to production cannot be called releasable. `/ground` asks it, and `/survey` follows the record.
  Nothing is filled in from context.
- **Pin**, before Implementation. Code that existed before the method is changed only once `/characterise` has
  recorded what it does at the seam the slice changes, one behaviour at a time, with a row in
  `delivery/survey/pinned.md`. Generated code needs no pin; a slice that touches no wrapped code says so. What
  stands in at the seam is a fake written in the test tree, never a mocking framework the method would have to
  add: the skills' examples are Vitest, and in a Java or .NET repository their last-resort module seam has a
  counterpart — Mockito, Moq — with the same standing, which `/characterise` now says in as many words.
- **Convergence** also holds the map to what the slice did. A rung the slice reached flips its row — rung,
  evidence, provenance `confirmed`, `planned` cleared — and `/survey` redraws the page; a rung it did not reach
  stays, since the map is never moved to match a hope and `verify` fails a row the tree contradicts. Then the
  lowest row still below its target with nothing planned is offered as the next **method slice**.

A method slice is one rung on one axis, with the team as its actor, and `/story-splitting` places it among
the product slices rather than ahead of all of them — the ordering question is which product slice is blocked
on which rung. It travels the same specify → plan → tasks → implement path, so agent change meets the same bar
either way. Three hooks in `.specify/extensions.yml` say the same things to a session that entered the loop
through a `/speckit-*` command without typing `/drive`: the map before a specification, the pin before a plan,
the map again after converge. All three print rather than run.

## Converging

`slipwai converge --check` says whether the adoption has ended: every row of the map at its target, the tree not
contradicting any of them (`check-convergence` runs), a clean tree, and nothing at the root the move would write
over — a `Makefile` of the repository's own is the usual one, since the root layout's `Makefile` is the factory's.
Every refusal is a line in the report, and nothing moves. `slipwai converge` then does what `migrate` does with the
layout moved: the replay is assembled for the root, everything the factory listed in `delivery/.written` is taken
out and written where the root layout puts it, and the merge — a fast-forward, parented on `HEAD` — carries the
move. A second commit moves what the factory does not list but that lived under the delivery directory — the
survey, the pinned and retirement ledgers, the ratchet baseline, the ADRs a person wrote — and respells the marked
blocks in `AGENTS.md` and `.gitignore` for the root; a third re-derives the harness projections. `project.json`
records `converged` (`with`, `from`) and keeps `origin: adopted`, the survey and the map as history; `docs/adoption.md`
and `docs/convergence.md` say the same. From then on the repository is a generated one: `migrate` measures from the
converge commit and finds `.written` at the root, and nothing an adopted repository carried is regenerated
differently. Experimental, like the rest.

## What comes after

`slipwai migrate`, from a newer factory, brings the method's material forward as one merge, exactly as for a
generated project: `delivery/.written` lists the files the factory wrote, and the replay it merges is the
repository's own tree with those replaced — so nothing of the repository's is ever read as the factory's to
delete, and a change the person made inside a factory file meets the factory's change in a three-way merge.
`add-service` grows the project beside the existing applications; it needs `--language`, since there is no
generated service to inherit one from.

## The gate that proves it

`make test-adoption` ([`scripts/test-adoption.py`](../scripts/test-adoption.py)) adopts each fixture
repository under `tests/fixtures/adopt/` — a JavaScript service with a linter that is red on day one, a Python
worker whose tests the survey guesses wrong and a flag corrects, a Go module, a .NET API whose toolchain the
machine may lack, and a JavaScript service on GitLab with a deploy job and a test suite that is red on day one
— and holds every claim on this page to it: one commit by the factory over theirs, nothing of
theirs written over, `adopt --refresh` a no-op straight afterwards, the gate green on day one (the red suite
quarantined and said), a GitLab job and no GitHub workflow for the GitLab repository, a newer factory's
`migrate` one clean merge that carries its change in, and the gate green again. Then the whole arc, on a
fixture built to reach every target — a Node service under `apps/shop` with a green suite, a type check, a
container file and a deploy job: adopt; the map reads `tests-exist`, `pipeline`, `laid-out` off the tree; one
method slice moves the safety-net row to `tests-pass` with the gate agreeing and the page following; every other
rung established as a person would establish it — the layout declared, the infrastructure answered, the
constitution ratified in full from `--requirements`, the strategy decided by an accepted ADR; `converge --check`
ready; `converge`; then the generated project's own `make verify` at the root, green, and a newer factory's
`migrate` over that, one clean merge and green again. CI runs it as its own job. A fixture that fails there is
the feedback loop this page asks for, working — the journey's first run found that a wrapped application in a
subdirectory had its `cd apps/shop && …` command split by the shell before the ratchet saw it, which every
root-level fixture had hidden.

## What it refuses

A directory that is not a Git repository — `git init`, or a one-way import from Subversion or TFS, is day
zero and not a step to work around. An unclean working tree. A repository that already has a `project.json`:
the method is already there, and `migrate` brings it forward. A `--delivery` directory that would write over
files the repository has.

## Not yet

Named so nobody builds them by accident: lifting existing code into a generated service (`add-service --from`,
which `/strangle` points at as the extraction step once it exists); a multi-repository manifest; SBOM and CVE
beyond the ecosystem's own `audit`; running OpenRewrite recipes (pointed at, never driven); dead-feature
detection beyond what the observability skill says. The adoption guide has the plan and the order.

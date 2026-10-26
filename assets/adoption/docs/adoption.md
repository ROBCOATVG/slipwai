# How the delivery method was installed here

`{{project}}` existed before this method did. `slipwai adopt` surveyed the tree, proposed what it found, and
wrote the method's material under `{{where}}` beside the code — nothing of the repository's own was
written over, and `project.json` records every fact with where it came from: `detected` from the tree,
`confirmed` by the person who accepted it, `overridden` by the person who changed it.
<!-- section: why -->

**Why:** {{why}}

<!-- end section -->
<!-- section: converged -->

**Converged.** With slipwai {{converged-with}}, every row of the map read *as generated* and the material moved from `{{converged-from}}/` to the root, as one merge. From here on this repository follows the generated workflow, `slipwai migrate` included; `origin: adopted`, the survey and this page are its history.

<!-- end section -->

## What was wrapped

{{applications}}

## Where the rest lives

{{database}}

{{infrastructure}}

Neither is something the factory manages here: `adopt` owns no environment and applies nothing. Where either
is `here`, the rule is import or reference — never manage a resource in two places. Where it is `elsewhere`,
the other repository is the contract. Where it is `unmanaged`, the finding is written down and the first step
is named.

## What runs

`{{make}} verify` is the gate: the method's own checks — agent projections, Spec Kit, the constitution floor,
the import rule over anything the factory generates — and then every wrapped application's recorded commands,
in the order above. A target recorded `null` passes with a line saying so; it is a written no, not a gap to
fill by guessing. `lint` and `typecheck` run through the ratchet (`{{where}}scripts/ratchet.py`): the
first local run records the findings that are there into `{{where}}baseline.json` — commit it — and
from then on the gate fails only on a finding that is new; `make ratchet-tighten` re-records what is left once
somebody has looked. `test` runs through the same ratchet with one difference: a suite that is red on day one
stops the first run and says so — a red suite is a fact a person reads, never one the gate records behind them —
and `make ratchet-tighten`, once they have, records it as **quarantined**: the gate passes on the state it
recorded and says so every run, until the suite is green and `ratchet-tighten` clears it. A new failure is still
a failure, whether the output names a file at a position or the runner names the test (`--- FAIL: TestX`,
`not ok 3 - adds`, `FAILED tests/test_a.py::test_b`, Surefire's `[ERROR]   ShopTest.adds`). `smoke` is the one
command the gate cannot compose from the eight: the application started and proved to answer, recorded as
`commands.smoke` once `{{where}}survey/running.md` says how (`/ground` asks; `null` is a written no with
its reason there). `{{make}} smoke` runs it, `{{make}} ci` and the gate's own smoke job run it in CI, and `verify`
never does, since it needs what the application needs. A Maven or Gradle build runs through its wrapper
(`./mvnw`, `./gradlew`): where the repository had none, `adopt` wrote one beside the build file, so the machine
needs a JDK and no Maven or Gradle of its own. Any other recorded command whose tool is not on the machine
running it cannot be baselined — the ratchet fails, names the tool, and records nothing until it is installed or
`project.json` records what this machine does run. A suite recorded as `test-full` is too slow for the gate and
has a target of its own. {{ci}}

## How a change reaches production

<!-- section: release-pipeline -->
**A pipeline deploys** (`{{release-provenance}}`{{release-evidence}}). Which environments it passes through, what gates each, and how a release is undone belong in `docs/deployment.md`; `/sail` asks every slice how it reaches production.
<!-- end section -->
<!-- section: release-scripted -->
**Somebody runs a script** (`{{release-provenance}}`{{release-evidence}}). A scripted release is one rung below a pipeline: the next step is a CI job that runs the same script on every commit that passes `verify`, described in `docs/deployment.md` before it is built.
<!-- end section -->
<!-- section: release-manual -->
**By hand** (`{{release-provenance}}`). Nothing here deploys; the first rung of the path to production is a script that does what the hands do, versioned here, and `docs/deployment.md` is where to write down what the hands do today.
<!-- end section -->
<!-- section: release-unknown -->
**Not recorded** (`{{release-provenance}}`): nothing in the tree says how a change reaches production, and nobody has said yet. This is the first Minimum CD fact and the method will not guess it: say it in `project.json` under `release.path` (`pipeline`, `scripted` or `manual`) or with `slipwai adopt --release`, and `/sail` asks before the first slice.
<!-- end section -->

## Next

1. `./{{where}}init` — first, as in any project the factory made. It installs Spec Kit and asks which
   coding agent to project the skills and commands into (`./{{where}}init --integration claude` names it
   outright; `python3 {{where}}scripts/agents/project.py --list` shows every agent it knows).
   Electing a code-index extension in the same run — `./{{where}}init --extension <key>`, and
   `./{{where}}init --help` lists what this copy offers — indexes the code, which is what makes a legacy
   codebase safe for an agent to work in; the two flags go together in one run.
2. `/ground`, in the agent — the question set the tree could not answer: one row of
   `{{where}}docs/convergence.md` at a time, the evidence and the rungs shown first, each answer written
   with `confirmed` provenance; then `/survey` so the pages and the strategy recommendation follow. What
   the tree could not say, or `--yes` left `unrecorded`, is settled here rather than one slice at a time —
   or skip straight to `/sail`, whose Ground stage runs the same questions for the rows a slice touches.
3. `{{make}} verify` — green on day one is the promise for a linter or type checker that arrived after the
   code, and the first run records the ratchet baseline: commit `{{where}}baseline.json` with what `init`
   wrote. A test suite that is red on day one is the one exception: the run stops and says so, and
   `{{make}} ratchet-tighten` quarantines it once you have read the failures. Anything else not green is the
   repository's own command failing, and `project.json` is where to correct what the survey got wrong.
4. {{makefile-step}}
5. Read `{{where}}docs/convergence.md`: where this repository stands on every ladder a generated project
   sits at the top of, what is planned to move each row, and what nobody has established yet; and
   `{{where}}survey/structure.md`, the architecture view — where anything starts, what depends on what,
   where change happens — which says what moves the Structure row and where `/strangle` would cut. Then
   `{{where}}docs/getting-started.md` and `{{where}}docs/architecture.md`, then `/sail`,
   whose ladder here begins at *Ground* (no map, no principles), pins wrapped code before *Implementation*,
   and holds the map to each slice at *Demo*, where its examples are proven, before offering the next row as
   a method slice.
   Three more commands are this adoption's own: `/characterise` pins the current behaviour of the code a slice is about
   to change, at the seam where it can be observed (`{{where}}survey/pinned.md` is the ledger) — with
   fakes written in the test tree, never a mocking framework it would have to add — and
   `/survey` runs `slipwai adopt --refresh` to reconcile a fresh survey with what `project.json` records.
   How each application is *run* is written, once proven, in `{{where}}survey/running.md` — the
   repository's own file, which the `run-the-app` skill points to and the factory never rewrites.
   When the code is ready to move, `{{where}}docs/change-strategy.md` opens with the strategy `why` and
   the map recommend for this repository — *leave it* included — then the four strategies and the order to
   change in; an accepted ADR with a `Strategy:` line is the decision, and `/strangle` moves one capability
   at a time only under a decision that says `strangler-fig`, writing `{{where}}retirement.md` as it goes.
6. Merge this adoption alone, before the first slice, and from then on one pull request per slice — a slice's
   after-acceptance commits ride in its own PR. A reviewer can read a slice; nobody reads five at once.
7. Later, `slipwai migrate` brings a newer factory's material here as one merge; the files it wrote are listed
   in `{{where}}{{written}}`, and nothing else is ever touched.

Profiles, axes and everything else the factory offers a generated project are described in
`{{where}}docs/`; `{{backends}}` are the backends it can add beside what is here.

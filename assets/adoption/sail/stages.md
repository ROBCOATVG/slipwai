<!-- section: ground -->
**Ground** — this repository adopted the method around code that was already here, so before any
   principle is ratified the map says where it stands: `{{map}}` exists and `make check-convergence` is
   green (`adopt` wrote both; `/survey` redraws the page from `project.json`). No map, no Principles. Read
   the rows and name the ones this slice touches — a slice through {{wrapped-or-one}}
   touches at least *Safety net*, *Structure* and *Strategy* — adding to or changing what was here is
   what a strategy is about, and a strategy the map only *recommends* is a question, never a default; a slice
   that changes how a change reaches production touches *Path to production*. A row whose provenance is
   `unrecorded` — or `detected`, the tree's reading and nobody's answer — on an axis the slice touches is a
   question for the person **before anything else**: the release path first of all, since a slice with no
   known path to production cannot be called releasable. **Asking is this stage's work, not a stop:** run
   `/ground` here, inside `/sail`, for the axes the slice touches — or with no argument, the first time, for
   every row a person has not placed — one row at a time, the evidence and the rungs shown first, each answer
   written where the record keeps it (`release`, `ci`, a deployable's `kind`, `why`, or the `convergence` row
   itself, provenance `confirmed`), then `/survey` so the record is followed. The stage is done when the rows
   the slice touches are `confirmed` or `overridden`, or the person has said they cannot place them; a row
   nobody can answer today stays as it is and is said so in the slice's specification — never filled in from context
   — and an ADR's `Accepted` is the person's word, never yours. Then continue down the ladder in the same run.
<!-- end section -->
<!-- section: pin -->
**Pin** — the slice changes code that existed before the method did (under
   {{wrapped-or-many}}) only once the current behaviour at the seam it changes is
   recorded: `{{pinned}}` carries a row for each behaviour `plan.md` says this slice changes, with the tests
   that pin it and the command that runs them. Otherwise run `/characterise <behaviour>` for each, one at a
   time — it refuses "everything", and so does this stage. Code the factory generated needs no pin: its
   tests are the pin. A slice that touches no code that was here passes this stage by saying so, and a slice
   that reaches a seam nothing can observe deterministically records the smallest seam it introduced in the
   same ledger. What stands in at the seam is a fake written in the test tree, never a mocking framework this
   stage would have to add — `/characterise` says why. This is the *pinned* rung of the safety-net axis,
   held per slice rather than claimed once. **And before any pin, the application has to start.** Where
   `{{running}}` still reads *Not yet proven* for the application the slice changes, or its record in
   `project.json` has no `smoke` command, this stage refuses the slice and says so: proving the run path and
   recording `smoke` is the programme's step right after the build, and it goes first — the one exception is
   the slice that proves it. A suite that never builds the context cannot see a constructor the container
   cannot call, and slices have shipped that way, converged and green, with an application that no longer
   started.
<!-- end section -->
<!-- section: plan -->
 In this repository the decided strategy governs the home too. Under an accepted `strangler-fig`,
   a product slice's *Structure Decision* names a deployable that is **not** one that was here (under
   {{wrapped-or-many}}) — a service `add-service` made beside them, current from day one,
   whose first capability moves through `/strangle` and writes `{{retirement}}` — or it quotes the owner's written
   exception for this slice, in their words. "Confirmed at plan time" by the plan alone is not a decision:
   a strangler that lands every slice in the old home is the old home with a new label, and
   `check-convergence` says so while the ledger stays empty.
<!-- end section -->
<!-- section: map -->
 A slice that touched how an application starts — constructors, dependency injection,
   configuration, module registration, the build — has converged only once that application has started with
   the change in place: `make smoke` where a `smoke` command is recorded, the command `{{running}}`
   holds otherwise, and a converged verdict that rests on the suite alone is not one. A runtime or a
   framework that moved a major version moves on the Platform row, as a slice of its own and never inside
   another — `/survey` reports a version that moved without the row planning it as a disagreement, and the
   slice that moved it is not converged until the row, or an ADR, owns the move. Then, because this repository is converging on what a generated one has, hold
   the map to what the slice did: run `make check-convergence` and read `{{map}}` against the diff. A rung this
   slice reached — a quarantined suite now green, a role now recorded, a release script now run by CI on
   every commit — flips its row: edit that row in `project.json`'s `convergence` (`rung`, `evidence` naming
   what established it, `provenance` `confirmed`, `planned` cleared), run `/survey` so the page follows, and
   `make ratchet-tighten` where fewer findings remain than the baseline records. A rung the slice did not
   reach stays where it is; the map is never moved to match a hope, and `make verify` fails a row the tree
   contradicts. Then offer the next slice. **An open `CRITICAL` in `specs/<feature>/adversary-log.md` comes
   first**, ahead of every product and method slice, until it is fixed or a person has deferred it in that row
   with their name and reason: one adoption pinned a defect that leaked one customer's account to another as a
   failing-if-fixed test and then spent a slice on an icon. Then the next method slice,
   from the programme `{{programme}}` carries (*The programme*), top first: a quick win — a secret in the tree the same day — then a build below the
   floor (Ant with its jars committed, to Maven or Gradle: first whatever the strategy), then an application
   nobody has proved starts (its run path written and `smoke` recorded: before any slice changes code that was
   here), then a product out of
   support, then a rung of the ladder or a tool the ecosystem has and nothing here runs, each paced as the
   decided strategy says; and, with the programme empty, the lowest map row still below its target with nothing
   `planned`. What is offered is written into the row's `planned` (or the step's evidence named in the slice) and
   handed to `/story-splitting` as a method slice for the split to place among the product slices — never ahead
   of all of them by default, a secret and an open `CRITICAL` excepted. A step that needs a decision nobody has
   made (a release path,
   a change strategy — the programme says *decide it first*) is offered as the question, not as work;
   `/survey` derives the programme again, so a step done is gone rather than ticked. Demo feedback that is
   neither a thing an actor does nor a rung of the map — an icon, a colour, a label — is a task in the next
   slice, never a slice with acceptance criteria of its own.
<!-- end section -->
<!-- section: implementation -->
 In this repository new code beside what was here (under
   {{wrapped-or-many}}) is tested the way `AGENTS.md`, *Delivery method*, says: what
   stands in at a seam is a fake written in the test tree, never a mocking framework added for the purpose —
   Mockito, Moq, gomock, `unittest.mock` are the same last resort in every language, and "what should I add?"
   is never answered with one. The runner is the one the application records; where that is out of support
   (JUnit 3 or 4, nose, a runner nobody maintains) new tests use the ecosystem's *current* framework and keep
   the old tests running beside them — JUnit 5 through its vintage engine, pytest running `unittest` as it is
   — as a slice on the map's Platform row, never the next-oldest version chosen because the tree's vintage
   makes it usual.
<!-- end section -->

# Strategy playbook: rewrite

A rewrite builds a complete new system on its new stack, runs it in parallel with the old one, then moves everything across in **one rehearsed cut-over** with a rehearsed rollback, and switches the old system off and deletes it from the tree. In slipwai terms it is `Strategy: rewrite` on an accepted ADR, which the method never recommends: a person decides it and says why a single cut-over beats a strangler fig with `End: all` (`src/slipwai/strategy.py`). The rule it imposes on a new feature: **the feature is built only in the new system, and the frozen legacy app is not changed to carry it.**

---

## 1. What it is

A rewrite builds a second system to take over everything the first one is still needed for. The new system is built complete, beside the old one or in a new repository, and proven against the old system's behaviour; then both run in parallel on live inputs; then traffic and data move across **all at once**, in a single cut-over that has been rehearsed, with a rollback that has been rehearsed too. After the rollback window the old system is switched off and deleted. The rewrite is finished only when *nothing* is served by the old code and the old code is gone from the tree.

Want the old system gone and a new stack, but moved one capability at a time? That is a strangler fig with `End: all` ([strangler-fig.md](strangler-fig.md)) — the recommended route. This playbook is the single cut-over.

The single cut-over is the shape Spolsky warns against and the shape behind most cancelled programmes: no value reaches users until the end, and the switch is large. It earns its place only when moving capability by capability is impossible or costs more than it saves, and then the playbook below makes the one switch as small a risk as it can be: the whole behaviour listed and pinned against both systems, the data migration rehearsed until it is dull, a parallel run on live inputs, and a rollback that has actually been done.

### When it is right

The ADR's `Why:` has to justify **a single cut-over over a strangler fig with `End: all`**. At least one of these must hold, with evidence:

- **The old system cannot be put behind a seam at all.** No interceptable entry point (no HTTP front, no front controller, no message bus, no single write funnel), and no changeable integration point in the database.
- **The data cannot be split by capability.** Every capability reads and writes the same tables through the same rules, so any capability moved early would leave two writers to the same rows.
- **A hard external deadline or contract makes coexistence impossible.** The old host is switched off on a fixed date, a licence ends, or a contract forbids running both.
- **The system is small enough that coexistence costs more than it saves.** A proxy, an auth bridge, contract views and data feeds, each built to be thrown away, would cost more than building the whole thing and switching once.

And the conditions that make any rewrite reachable:

- **The system is small enough to hold in your head.** Roughly under 20k lines, or a handful of capabilities. A team can then list *all* the behaviour to preserve and characterise it in weeks, not quarters. Size is the strongest predictor of whether parity is reachable.
- **The platform cannot be climbed.** Examples: a runtime or framework that is out of support with known security flaws, where the jump to a supported major version is close to a rewrite of that layer anyway; a vendor product with no source; a language nobody can hire for. This argues for *replacing* the system; on its own it argues for a strangler fig with `End: all`, not for a single cut-over.
- **Most of the old behaviour is not wanted.** The business has moved on, and usage logs show most screens unused. Then you are not really rewriting. You are building a new product and migrating its users (Caudill: "build something new next to it").
- **The behaviour is specified outside the code.** Calculations to a standard, regulatory rules, a published protocol. Fowler's *Feature Parity* names this as one of the few cases where parity is reasonable.
- **The old system can be frozen.** The business accepts no new features in legacy until cut-over, because new features go to the new system.

### When it is wrong (warning signs)

| Warning sign | Why it matters |
|---|---|
| The only reason is wanting a new stack, or wanting the old system gone | That is a strangler fig with `End: all` and the new home `beside` ([strangler-fig.md](strangler-fig.md)): the same end, with every capability moved a win on its own. Fowler, Cartwright, Horn and Lewis: incremental delivery of the parts is where the risk goes down. |
| The trigger is "it is ugly", "nobody understands it" or "no tests" | Spolsky: old code "has been used. It has been tested." The fixes are characterisation and refactoring: `in-place`, reshaping the code toward a `Target` (`target-shape.md`), or a strangler fig with its new home `inside`. |
| Nobody can list what the system does | You cannot reach parity with an unknown target. Fowler: defining the "as is" was itself "a huge effort". |
| The business will not freeze legacy | Two moving targets, a parity gap that never closes, double maintenance. |
| There is no dated checkpoint for the new system | Value arrives only at the end, nothing shows progress before it, and the programme is cancelled halfway. |
| The plan says "same as today but on X" | Feature parity by default. Thoughtworks calls this an antipattern: unused features and old workarounds get rebuilt. |
| The team plans every deferred idea into v2 | Brooks's second-system effect. |
| The data model is the problem, and the rewrite also changes it on day one | Data migration becomes the critical path with no rehearsal budget. |
| Many systems integrate with the old database directly | Every integration is hidden parity scope, and all of them move at the one switch. Use a Legacy Mimic, or choose a strangler. |
| Features keep reaching users early through seams and routed pages | The work is already moving capability by capability. Say so: supersede the ADR with a strangler fig, `End: all`. |

The honest prior is that **most rewrites are cancelled or overrun**. The playbook below exists to keep a rewrite cancellable without loss at every step. Each phase leaves the old system working and the new system closer to complete, and the checkpoint review can always switch to a strangler fig with `End: all`, keeping what is built and routing it one capability at a time.

---

## 2. What the ADR records

The strategy ADR (`docs/adr/NNNN-strategy.md`, status Accepted) carries these lines. The method requires `Freeze:`, `Home:`, `Stack:`, `Why single cut-over:`, `Cut-over:`, `Rollback:`, `Parity:`, `Checkpoint:` and `Target:`; a decision missing one is reported incomplete and nothing after it starts. Write `Why:` and `Data:` too; each is a whole `Name: value` line so the tree can read it.

```
Strategy: rewrite
Why: <the trigger, in the business's words — and why in-place cannot meet it>
Why single cut-over: <which holds — no seam possible | data cannot be split by capability | fixed external date or contract | too small to coexist — with the evidence; why a strangler fig with End: all cannot meet it>
Freeze: agreed — <who agreed, when; scope: no new features, bug & security fixes only, no schema changes>
Home: beside — services/<name>        |  Home: new-repo — <url or name>
Stack: <backend> — proposed from survey (the team's current language)   |  Stack: <other> — overridden by <who>: <why>
Target: <the shape the new system is generated in, e.g. "modules in one deployable, hexagonal inside each — module map: <link>" or "services, hexagonal inside each"> (target-shape.md)
Parity: <what "the same" means — e.g. "every behaviour on docs/parity.md passes against both systems; unused screens (list) are dropped, not ported">
Data: <shared-db-first | migrate-at-cutover> — <owner of reconciliation>
Cut-over: single — <date or window>; decided by <named person>, on <go/no-go criteria doc>
Rollback: <how, within what window, and what happens to writes made after the switch>
Checkpoint: <date> — <what is reviewed; what makes us stop, or switch to a strangler fig with End: all>
```

Why each line matters:

- **`Why:`** forces the trigger into the business's words and makes the author say why `in-place` cannot meet it. A "why" that reads "it is ugly" or "no tests" is a warning sign (§1).
- **`Why single cut-over:`** is what separates a rewrite from a strangler fig with `End: all`, which reaches the same end with less risk. It names one of the four reasons in §1 and its evidence. "We want a new stack" is not one of them; a decision without this line is reported incomplete and nothing after it starts.
- **`Freeze:`** should not finish the axis under a rewrite as `absent`. For a strangler, `absent` with a substitute is a legitimate answer. For a rewrite, an unfrozen legacy is a moving parity target. If it is absent, the "what instead" must be a *double-entry rule*: every legacy change also lands as a parity row and a slice in the new system in the same week. A reviewer checks that; no gate does yet.
- **`Home:`** and **`Stack:`** say where new behaviour is built and in what; every spec reads them, and `check-convergence` fails a spec before the new home exists (see the subsections below).
- **`Target:`** names the shape the new system is generated in, so the first service does not set the architecture by accident (`target-shape.md`).
- **`Parity:`** is the single most important line. "Port the behaviour, not the bugs": parity is defined per behaviour for the whole system, and each behaviour is marked *preserve*, *preserve-including-quirk*, *fix* or *drop*. The person who owns the product decides; an agent cannot.
- **`Data:`** fixes how the new system reaches data before and during migration, and who owns reconciliation, so migration is planned and rehearsed rather than left to the cut-over weekend.
- **`Cut-over:`** is always `single`. It names the window and a single decider, so go/no-go is a written decision against criteria, not a mood.
- **`Rollback:`** must cover writes made after the switch; a rollback that ignores them is not a rollback.
- **`Checkpoint:`** makes cancellation, or a change of course, a planned outcome rather than a failure. By the checkpoint the new system must be deployed through its own pipeline and pass an agreed share of the traffic-weighted *preserve* rows, and a data migration rehearsal must have run. If it does not, the ADR is superseded: by a strangler fig with `End: all` that routes what is built, or by stopping.

### Where the new system lives

`Home: beside` puts the new system in the same repository, as `services/<name>`, generated with `slipwai add-service`. `Home: new-repo` puts it in its own repository, generated with `slipwai generate`. The person chooses it in the board's decide form. Either way the new system has its own gate, current runtime, container and IaC from the first commit.

### Its stack

`Stack:` is proposed from the survey, defaulting to the team's current backend language, so the people who know the domain can keep working in a language they know. A person may override it on the board; an override names who chose it and why.

---

## 3. Phases

Each step lists **what**, **who** (P = person, A = agent, B = board control), **evidence** (checkable in the tree) and **unblocks**.

### Phase 0: make the old system safe

Whatever the strategy, the old system is first made safe and observable.

**0.1 Quick wins on the old system.** Remove committed secrets and rotate them. Remove committed build output and jars. Replace hard-coded paths with config.
- Who: A does it, P rotates credentials.
- Evidence: the survey finds no secrets or committed binaries; the convergence map's Build row no longer stops on committed build output; the ledger is untouched (this is not a capability move).
- Unblocks: everything. These fixes are allowed in legacy under any freeze.

**0.2 Build floor, pinned** (`build-floor.md`). A hand-run, IDE-only or script-glued build moves to a declared build tool, with dependencies fetched rather than committed, run inside a build container pinned to the old toolchain. Under rewrite, keep this minimal: the old build only has to be reproducible, not modern — the new system is generated with its own current toolchain and meets the floor on day one. Platform, packaging, container and IaC rungs for the old app are "not in place: the new system starts current".
- Who: A.
- Evidence: `make verify` builds the old app from a clean checkout.
- Unblocks: smoke, characterisation.

**0.3 Prove the old app starts (`smoke`).** A smoke target boots the old app against a disposable database and fetches one page.
- Who: A, with P supplying a database (`/ground`).
- Evidence: a smoke target that boots the app against a disposable DB (e.g. a database container seeded from an anonymised backup) and fetches one page.
- Unblocks: HTTP characterisation and the parallel run. You cannot compare against a system you cannot run.

### Phase 1: decide and freeze

**1.1 Strategy ADR accepted.** The ADR is accepted with the lines in §2, including `Why single cut-over:`.
- Who: P decides; B's decide form offers "Use a strangler fig instead" when rewrite is picked, and asks for `Why single cut-over:` with the other required lines.
- Evidence: an accepted ADR with `Strategy: rewrite`, `Why single cut-over:`, `Freeze:`, `Home:`, `Stack:`, `Parity:`, `Cut-over: single`, `Rollback:`, `Checkpoint:`.
- Unblocks: the drafting stage, and generating the new system.

**1.2 Freeze in force.** Legacy accepts only the change classes the freeze allows.
- Who: P agrees it; `check-convergence` holds it through the `Legacy-change:` trailer.
- Evidence: the legacy-frozen check (§5, Gates) runs in `make verify`.
- Unblocks: a stable parity target.

### Phase 2: know what to preserve

**2.1 Behaviour inventory** (`docs/parity.md`) for the **whole** system. One row per behaviour: entry point (URL / action / database routine / batch job / report / outbound integration), observed usage, owner, decision (*preserve / preserve-quirk / fix / drop*), test id, and status in new. Nothing is left in the old system after cut-over, so nothing may be missing from this table.
- Who: A drafts from the survey: route or action mappings, page templates, database routines the app calls, scheduled jobs, outbound integrations, plus access logs where they exist. P marks each decision in the file.
- Evidence: every entry point the survey finds appears in `parity.md`, and none has a blank decision. Compare the survey's route list with the table by hand; the method does not check this yet.
- Unblocks: characterisation scope and the build order. This is where *drop* earns its keep: Fowler's logistics example spent effort on package types the business had already decided to stop.

**2.2 Usage evidence.** Turn on or collect access logs. Count hits per action for a few weeks if possible.
- Who: P provides logs, A summarises.
- Evidence: a usage column in `parity.md`.
- Unblocks: honest *drop* decisions.

### Phase 3: characterise the old system at its boundary

Characterise at the **boundaries the new system must honour**, not at the inner classes that will be thrown away.

**3.1 HTTP approval tests.** Record request/response pairs for each *preserve* behaviour against the smoke-running old app. Normalise volatile fields (timestamps, session ids, CSRF tokens) and store the approved outputs as golden files.
- Who: A via `/characterise`.
- Evidence: `characterisation/http/<behaviour>/{request,approved}.*` exist and the suite passes against the old app.
- Unblocks: the parity test. The same suite, pointed at the new system's base URL, *is* the parity test.

**3.2 Database characterisation.** For each write path, capture what the app sends to the database (a statement, or a call to a database routine), its result, and the resulting row deltas. For each read, capture the query results for a seeded dataset.
- Who: A.
- Evidence: `characterisation/db/` tests that run against the containerised DB and pass.
- Unblocks: the decision to keep the legacy write path for now behind a Legacy Mimic, and later the data migration reconciliation.

**3.3 Target-agnostic suite.** One parity suite, parameterised by `TARGET=legacy|new`.
- Who: A.
- Evidence: `make parity TARGET=legacy` is green. `make parity TARGET=new` runs and fails honestly.
- Unblocks: per-capability "done" inside the new system, which means "green against both".

### Phase 4: stand up the new system before any feature

**4.1 Generate it.** Beside the old app: `slipwai add-service <name> --backend <stack>`. In a new repo: `slipwai generate`. The stack comes from the survey and `Stack:`.
- Who: A, with P confirming home and stack on the board.
- Evidence: a new service directory or repo with its own gate green, current runtime, container and IaC. These are the rungs marked "starts current".
- Unblocks: the walking skeleton.

**4.2 Walking skeleton to production.** A health endpoint, deployed to the production environment by the same path every later change will use. A router in front of the old app (a reverse proxy, or a DNS or host-name switch) sends every user request to legacy; this is the switch the cut-over will flip, and it exists from the start so the cut-over is a configuration change, not a build.
- Who: A builds, P owns the environment and credentials.
- Evidence: a deploy pipeline file; a smoke check against the deployed health URL; a routing config sending all user paths to legacy; a ledger row `transitional: router`.
- Unblocks: every feature. Fowler's "Build as you mean to continue" applies: the new system's delivery path exists before its first behaviour.

**4.3 Transitional data access.** Decide how the new system reaches data before migration. Usually it reads a copy of the legacy data (`Data: migrate-at-cutover`) or the shared legacy database through its own repository layer (`Data: shared-db-first`). Where the legacy writes go through stored procedures or a shared database, the new system may call them as a Legacy Mimic for a while, rather than re-implementing those rules on day one.
- Who: A proposes, P approves.
- Evidence: an ADR or `docs/transitional.md` listing each transitional component, with a removal condition and a ledger row of its own.
- Unblocks: building capabilities that need existing data.

From here on, new feature requests go to the new system (§4).

### Phase 5: build the complete system

The new system is built capability by capability **inside the new system**, each proven against the parity suite. None of it is released to users until cut-over, except through a transitional route recorded in the ledger (§4, 4.2).

**5.1 Order the build.** Order by risk and dependency, not by release: the hardest and most coupled behaviours (writes into shared tables, the database rules, the reports and exports that aggregate everything) come early, because they decide whether the cut-over date is real.
- Who: A proposes, P sets the order.
- Evidence: the `parity.md` order column; the fleet backlog.
- Unblocks: the build of each capability, in that order.

**5.2 Build each capability** (`/sail`, `/launch`, `/cruise`). Its slice is done when its parity rows pass with `TARGET=new` *and* still pass with `TARGET=legacy`. *Fix* rows carry a new expected output and a note; *drop* rows are removed from both.
- Who: A builds, P approves the slice.
- Evidence: parity rows flip to `new: passing`; ledger row `built` (deployed in the new system, not routed to users).
- Unblocks: shadowing that capability, and the next in the order.

**5.3 Shadow each capability as it lands.** Mirror real requests to the new implementation and discard its responses (reads). Or, for writes, run in compare mode without committing (GitHub Scientist style: legacy stays authoritative, mismatches are logged). Writes must not double-apply: shadow against a copy or a dry-run path. Users still see only legacy.
- Who: A builds the comparator, P reads the mismatch report.
- Evidence: a mismatch report under `docs/shadow/<capability>.md`, with every class of mismatch explained.
- Unblocks: the completeness check.

**5.4 The system is complete.** Every *preserve*, *preserve-quirk* and *fix* row passes with `TARGET=new`; every *drop* row is gone from both; every shadow report is under its agreed threshold.
- Who: A reports, P confirms.
- Evidence: `make parity TARGET=new` green for the whole of `parity.md`; no ledger row below `built`.
- Unblocks: the parallel run (with the rehearsed migration of Phase 6).

### Phase 6: data migration, rehearsed

This starts during Phase 5, as soon as the first write capability is built.

**6.1 Migration scripts and reconciliation spec.** For each table: source count minus approved exclusions must equal the target count. Add checksums or business-level queries (e.g. "open orders per customer", "total invoiced per month"), because matching counts prove little.
- Who: A writes, P owns the thresholds.
- Evidence: `migration/` scripts, plus `migration/reconcile.sql` with pass/fail thresholds.
- Unblocks: rehearsals.

**6.2 Rehearse repeatedly.** Run the migration on a fresh production copy each time. Time each run, and record every difference with an explanation.
- Who: A runs, P reviews the diffs.
- Evidence: `docs/rehearsals/<date>.md` with duration, counts and diffs. The last rehearsal must have run inside the cut-over window with no manual steps.
- Unblocks: the parallel run, and unlocking cut-over.

### Phase 7: parallel run

**7.1 Run both systems on live inputs.** For an agreed period, feed the complete new system the same inputs as legacy: dual-write from the router, or CDC from legacy into the new store. Legacy stays authoritative. Reconcile daily, and compare reports, outputs and cross-functional measures (latency, error rate).
- Who: A runs the reconciliation, P agrees the exit criteria.
- Evidence: daily reconciliation reports; agreed exit criteria met.
- Unblocks: go/no-go.

### Phase 8: cut-over with rollback rehearsed

**8.1 Go/no-go.** Written criteria and the named decider from `Cut-over:`.
- Who: P (the named decider).
- Evidence: `docs/cutover.md` with a runbook, owners, timings, verification steps, a rollback trigger (measurable) and a rollback path. The rollback path covers writes made after the switch: reverse sync, or replay of the new system's write log into legacy.
- Unblocks: the rollback rehearsal.

**8.2 Rollback rehearsal.** Cut over in staging, take writes, roll back, and reconcile.
- Who: A runs, P signs off.
- Evidence: a rehearsal record showing the rollback finished inside its window and reconciled.
- Unblocks: the real cut-over.

**8.3 Cut over.** Run the runbook: the final migration, reconciliation, then the router sends everything to new in one switch. Legacy goes read-only for the rollback window, then is switched off.
- Who: P decides, A runs the runbook.
- Evidence: the router sends everything to new; every capability ledger row reads `moved`, then `retired` when the rollback window closes.
- Unblocks: decommissioning.

### Finish line

The rewrite is finished when the old system and every piece of transitional architecture are gone from the tree.

**F.1 Remove transitional architecture.** Delete the mimics, any transitional seams and routed pages' fallbacks, the proxy rules and the dual-write.
- Who: A.
- Evidence: each transitional ledger row reaches `removed`.
- Unblocks: deleting the old app.

**F.2 Delete the old app from the tree**, along with its build, jars and the characterisation tests that only target legacy. Keep the parity suite, now `TARGET=new` only, as the new system's regression net. Archive the final database backup, and decide the fate of the legacy database routines (drop after the retention window).
- Who: A deletes, P decides retention.
- Evidence: the survey no longer finds the legacy app; every ledger row reads `removed`; the convergence map's Strategy row reads `done`.
- Unblocks: nothing further; the strategy is complete.

---

## 4. How a feature request is handled

**4.1 Every new feature is specified against the new system.** If the PRD says "add X to the dashboard" and the dashboard is legacy, the spec targets the new service. A PRD line that contradicts the strategy is **overridden and said in the spec**. Examples: "add a panel to the existing dashboard page", "add a column to the customers table", "use the existing web framework". The spec opens with a short *Strategy constraints* block that quotes the PRD line and states the override, e.g. "Strategy: rewrite — this feature is built in `services/<name>`; the PRD's placement in the legacy app is overridden. It reaches users at cut-over. The legacy page is not changed except by any transitional seam recorded in `retirement.md`."
- Who: A at draft, P approves the spec.
- Evidence: the spec names the new service and only touches paths under it. `legacy-frozen` stays green.

**4.2 Decide when the feature becomes visible.** A feature built only in the new system reaches nobody until something routes to it. Under a single cut-over the default is that it waits for the cut-over; anything earlier is an exception with a removal condition. The spec records `Visibility: cut-over | seam | page` with the reason:
- (a) **Ship at cut-over** (`cut-over`, the default). The feature is built, passes its acceptance criteria in the new system, is shadowed with the rest, and reaches users with everything else at the switch.
- (b) **Transitional seam** (`seam`, an exception). The legacy page includes a fragment served by the new system. This is a one-line legacy change, allowed only as `Legacy-change: transitional`, with its own ledger row and removal condition (`remove when: cut-over`), and it needs the session to cross to the new system (an auth bridge at the router: another transitional row).
- (c) **Transitional routed page** (`page`, an exception, recorded in the ledger). The router sends one page's path to the new system before cut-over. The page then has to do everything the old one did, so its existing behaviours join the slice as acceptance criteria tagged *parity*, and it needs its own route-back rehearsed. It is a small early cut-over, so it is recorded as a transitional route with `remove when: cut-over` (when the route becomes the normal one).

The person decides, when the spec is approved. The draft proposes `cut-over` unless the inputs below argue otherwise:
1. **How far away cut-over is.** A seam or a routed page is proposed only when the feature is needed before the `Cut-over:` window, and the need is stated.
2. **What else is on the page.** Its rows in `docs/parity.md`: the behaviours characterised at its URL. Few and simple favour `page` over `seam`, if an exception is taken at all. A rich page, where the feature is a small part, favours `seam`.
3. **What the page cannot own:** the shared menu and layout, the login session, the links to other pages. An early page or fragment needs the session to cross to the new system through an auth bridge at the router: a transitional ledger row.
4. **How it looks.** A new-look page among old-look pages, or a new-look panel inside an old-look page. Only a person can judge this, so `/mockups` draws the chosen option, and both where the choice is close; the storyboard's verdict decides.
5. **The freeze.** A seam is a change to the frozen system, and every early route is infrastructure built to be thrown away, so, other things being equal, the draft prefers `cut-over`, which leaves the legacy code alone.

If exceptions keep being taken, the work is moving capability by capability in practice: a reviewer flags it and proposes superseding the ADR with a strangler fig, `End: all`; the board does not count exceptions yet.

- Evidence: `Visibility:` and its reason are in the spec; a `page` brings the page's parity rows into the acceptance criteria and a route-back rehearsal; any seam, routed page and auth bridge are in the ledger with `remove when: cut-over`.

---

## 5. How the method carries it

### Adoption sequence on the board

When a person picks *rewrite*, the board's decide step offers "Use a strangler fig instead": the new home `beside`, `End: all` ([strangler-fig.md](strangler-fig.md)), the same end reached one capability at a time. If the person keeps *rewrite*, the sequence (the board's voyage, and `slipwai adopt --next`) changes shape, not just a label:

1. **Survey**, map, gate and ratchet, as under every strategy.
2. **Decide.** The form asks exactly the rewrite's lines: `Freeze:`, `Home:` (beside / new repo), `Stack:`, `Why single cut-over:`, `Cut-over:`, `Rollback:`, `Parity:`, `Checkpoint:` and `Target:`. The stack is proposed from the survey (the old language's language package, a browser app where the old app served pages, Postgres where there is a database), and a person may override it. A language package that is not installed is said with `slipwai language install <name>`. The board writes the ADR with every line plus a derived `Build:` line, and commits it. The strategy record reads the accepted ADR's `Name: value` lines; a required line that is missing is said by `check-convergence` and on the board, and the decision still stands.
3. **Build floor**, then **`smoke`**: the old system only as far as needed to run it.
4. **The new system**, by where it lives:
   - `beside`: "generate the new home", which the board runs itself: `add-service`, then `add-frontend` when a browser app was chosen, each committed.
   - `new-repo`: "generate the new system" (`slipwai generate`). After it, the voyage hands over to the new project ("continue in the new system at …"), and the old repo's constitution and spec steps are dropped.
5. **Parity**: write `docs/parity.md` for the whole system. An agent step the board names; it does not do it. The person marks each row *preserve / quirk / fix / drop*.
6. **Draft**: constitution plus the first feature spec, targeted at the new system, `Visibility: cut-over` by default.
7. **Fleet** builds slices.

The board shows the `Checkpoint:` date for the whole programme. Once it has passed, the board puts the decision again through the decide form: carry on with a new date, switch to a strangler fig, or stop.

### Draft, spec and mock-ups

- `/draft` reads the strategy and this playbook, and refuses while the decision is missing or incomplete. The spec's **target is the new system**: its paths, its stack, its test conventions.
- A PRD line that contradicts the strategy is overridden in the spec and quoted beside the ADR line it contradicts.
- A schema change the PRD asks for is either made in the new system's own store, or deferred until data migration. It is never made in the frozen legacy schema.
- Every spec ends with `## Strategy fit`, holding `Lands in:`, `Visibility: page | seam | cut-over` with its reason (§4, 4.2), and the `docs/parity.md` rows a `page` brings in. When the ADR's `Target:` is modular, it also holds `Module:`, `Publishes:`, `Consumes:` and `Owns data:`.
- `/mockups` draws the feature in the new system's UI where the spec lands there: for `page`, the whole new page; for `seam`, the old page with the panel; where the choice is close, both, so the person can judge the look.
- `/sail`'s plan stage holds each slice to the rewrite's rules.

### Constitution

The draft writes the rewrite's clause into the constitution from the ADR. In substance:

- "This repository is under a rewrite with a single cut-over (ADR NNNN). New behaviour is built only in `<home>`, on `<stack>`, and reaches users at cut-over. The legacy app accepts security fixes, quick wins, bug fixes with a characterisation test, and transitional seams recorded in the ledger. Nothing else."
- "Parity is defined by `docs/parity.md` for the whole system. A behaviour is done when it passes against both targets."
- "Port the behaviour, not the bugs: a *fix* row needs the owner's decision."
- "The new system's gate, deploy path and observability exist before its features."
- "Nothing is routed to the new system before cut-over except transitional routes in the ledger, each removed at cut-over."
- "Transitional components are listed with their removal condition."

### Gates

`check-convergence`, run by `make verify`:

- **Legacy frozen.** A commit after the strategy ADR that changes the code that was here fails unless it carries a trailer `Legacy-change: security|bugfix|seam|quick-win|build|characterise`.
- **New system first.** A spec fails before the new home exists (`beside`); under `new-repo`, any spec in the old repo fails, because specs belong in the new system.
- **Ledger consistent.** A capability `moved` with no `shadowed` row before it fails, and so does an unknown status.
- The ratchet applies to legacy, and in an adopted repo `check-imports` runs through it (existing violations are a baseline).

### Programme pacing

Under a rewrite the old system climbs only quick wins, a reproducible build and smoke. Every other rung is reached by the new system at generation. The programme has a new-home step, as under a strangler fig, before the first feature. It paces in **checkpoints, not phases**, because a single cut-over gives users nothing to see until the end: by checkpoint 1 the new system is deployed through its own pipeline and an agreed share of the traffic-weighted *preserve* rows pass on new; by checkpoint 2 the system is complete (5.4) and a migration rehearsal has run inside the window; the last checkpoint is the cut-over window. When the `Checkpoint:` date passes, the board puts the decision again: carry on with a new date, *switch to a strangler fig* (keep what is built and route it one capability at a time, so it starts earning), or *stop*.

### Ledgers

`retirement.md` holds one row per capability (grouped behaviour from `parity.md`) and a second table, "Transitional pieces" (`Date | Piece | Why | Remove when | Status`), for each seam, routed page and auth bridge, each with `remove when: cut-over`. The programme is not finished while a transitional piece is live. Capability statuses:

- `routed`: only for a transitional route (§4, 4.2): users reach it before cut-over, with the legacy path still present.
- `shadowed`: the new implementation exists, passes its parity rows, and runs in shadow; users do not reach it.
- `moved`: live traffic is served by new. Under a single cut-over every capability row reaches `moved` at the same switch, and the legacy path is still present for rollback. The gate refuses `moved` without a `shadowed` row before it.
- `retired`: legacy is switched off for it, after the rollback window.
- `removed`: its legacy code is deleted from the tree.

The rewrite is complete when **every** row reads `removed`, including the last one: "legacy app".

**Not built yet:**
- A parity suite runner with `TARGET=legacy|new`, and a parity panel or completeness bar on the board.
- The `no-early-routing` gate (no user path routed to new before cut-over unless the ledger names it).
- Checkpoint tracking of real traffic served, beyond the date itself.
- `homes.yml`, and the `Lands in:` cross-check against it.
- The legacy-size ratchet, and the seam or proxy health route checked in CI.
- Proxy, SSI include and auth bridge scaffolding (the agent writes them per slice).
- Locked migration-rehearsal, parallel-run, cut-over and decommission steps on the board.
- The board's language install as a button (it shows the command).

---

## 6. Anti-patterns and how the method detects each

| Anti-pattern | Detection |
|---|---|
| A rewrite chosen only to get a new stack | A decision without `Why single cut-over:` is reported incomplete and nothing after it starts; picking rewrite on the board offers "Use a strangler fig instead". |
| New features added to legacy "just this once" | Legacy-frozen check in `check-convergence`: a commit touching the old app without a valid `Legacy-change:` trailer fails. |
| Feature parity by default (porting unused screens) | A reviewer questions `parity.md` rows with usage of 0 and decision *preserve*, and holds the draft while rows are undecided; nothing checks this yet. |
| Silent bug-fixing (or silent bug-porting) | A behaviour whose new output differs from approved legacy output fails the parity suite the team runs against both targets, unless the row is *fix* with an owner. |
| Second-system effect (v2 wishlist) | The spec must trace each requirement to a parity row or a PRD feature; untraced scope is listed in review. |
| No visible progress until the end | Checkpoint lines; the board shows the `Checkpoint:` date and re-asks the decision once it passes. The share of `parity.md` passing on new and the last rehearsal date are reported by hand. |
| A strangler in disguise (transitional routes piling up) | Each early route is a ledger row; a reviewer counts repeated `Visibility:` exceptions and proposes superseding the ADR with a strangler fig, `End: all`. No gate or board flag does this yet. |
| Building the feature first, the platform later | `check-convergence` fails a spec before the new home exists (or any spec in the old repo under `new-repo`); hold features until the walking skeleton deploy is evidenced. |
| Data migration left to the cut-over weekend | No go until `docs/rehearsals/` holds a run inside the window with no manual steps and explained diffs; the board does not lock cut-over yet. |
| A rollback that ignores post-switch writes | `cutover.md` carries a "writes after switch" section, and the decider requires a rollback rehearsal record before go. |
| Transitional scaffolding left in forever | Ledger rows for transitional components; the programme is not finished while any is live. |
| The old system never actually switched off | The Strategy row reads `done` only when every ledger row, `legacy app` included, reads `removed`. |
| Shadow writes double-applying | Shadow mode must target a copy or a dry-run path; the comparator's spec says so. |
| Unfrozen legacy drifting from the parity target | `Freeze: absent` requires the double-entry rule; a reviewer flags legacy commits without a matching parity row. |

---

## 7. Worked example: an internal booking app

The context: an internal booking web app of about 10k lines, on an end-of-life runtime and web framework with known security flaws. Business rules live in the database: every booking, resource and account change goes through the same few database routines over the same handful of tables, so no capability can be moved without the others writing the same rows. There are no tests; credentials and machine-specific paths sit in committed config; the build is hand-run with committed libraries. The machine it runs on is in a hosting arrangement that ends on a fixed date about five months away, and the old runtime cannot be installed on the replacement platform. The first request is "a reminders panel on the dashboard". The board suggests a strangler fig with `End: all`; the person records why a single cut-over is justified instead: the data cannot be split by capability, the host is switched off on a fixed date, and the app is small enough to build complete before it. The first ten steps:

1. **Quick wins.** Remove the committed credentials from config and rotate them (P). Move config to environment variables. Delete committed libraries and build output. Replace machine-specific paths with configurable ones. *Evidence:* the survey is clean and `make verify` is green with the ratchet baseline. Commits carry `Legacy-change: quick-win`.
2. **Reproducible build.** Move the build to a declared build tool and pin the old runtime in a container, because it is no longer installable from current sources. *Evidence:* a clean-checkout build in `make verify`.
3. **Smoke.** A compose file with a database container, a schema script exported from production plus seed data (`/ground`: "who can give us an anonymised backup?"), and the old app. *Evidence:* the smoke target fetches the dashboard with HTTP 200.
4. **Strategy ADR, rewrite.** `Why: runtime and framework are out of support with known flaws; app is small enough to list.` `Why single cut-over: the old host is switched off on <date>; every capability writes the same tables through the same database routines, so the data cannot be split by capability; at ~10k lines the app can be built complete before the date.` `Freeze: agreed — <product owner>, <date>: security & bug fixes only, no schema changes.` `Home: beside — services/<name>.` `Stack: <backend> — proposed from survey.` `Parity: rows in docs/parity.md; the unused bulk-import screen is dropped.` `Data: migrate-at-cutover; the new system has its own store; <owner> owns reconciliation.` `Cut-over: single — one weekend, four weeks before the host date; <owner> decides.` `Rollback: route back to legacy within 48 hours, replaying the new system's write log into legacy.` `Checkpoint: <date, 8 weeks out> — half of the traffic-weighted preserve rows pass on new and one migration rehearsal has run; if not, review: switch to a strangler fig or stop.`
5. **Inventory.** The agent lists every route, every scheduled job and every database routine the app calls. Usage logs show which screens are live. The person marks each row. *Evidence:* `docs/parity.md` with no undecided rows.
6. **Characterise.** HTTP approval tests for each *preserve* route against the smoke app, with session and CSRF tokens normalised. For each write, snapshot the database's result and row deltas; for each read, snapshot results on the seed data. *Evidence:* `make parity TARGET=legacy` green.
7. **Generate the new system** with `slipwai add-service <name> --backend <stack>`: a current runtime, its own store and its own gate. It is developed against a nightly anonymised copy of the legacy data, migrated by the first version of the migration scripts (ledger row `transitional: dev-data-copy`). *Evidence:* the service's gate is green.
8. **Walking skeleton.** A reverse proxy in front, with every user path routed to the old app; the new system's health check is reachable only to the team. Both deploy through one pipeline, to the replacement platform. *Evidence:* routing config, a deployed health check, ledger row `transitional: router`.
9. **Draft the reminders feature against the new system.** The PRD says "add a panel to the dashboard"; the spec overrides the placement and builds it in the new service's dashboard. For visibility, the draft weighs §4, 4.2. Cut-over is about four months away and the business agrees reminders can wait for it, so it proposes `Visibility: cut-over`. Had the business needed reminders sooner, the route would have been `Visibility: seam`: one include line in the legacy dashboard (`Legacy-change: transitional`), an auth bridge at the router, and both recorded as ledger rows with `remove when: cut-over`. `/mockups` shows the panel in the new-look dashboard and the person accepts it. The legacy code is not touched. *Evidence:* `Visibility: cut-over` and its reason in the spec, `legacy-frozen` green.
10. **Build the system, capability by capability, inside the new system.** The booking writes and the database rules come first, because they decide whether the date is real; then the dashboard (with the reminders panel), the other pages and the reports. Each capability's parity rows pass against both targets and are shadowed against real requests; each ledger row reaches `built`. *Evidence:* parity rows passing on new, and `docs/shadow/<capability>.md` reports.

That reaches the checkpoint: half of the traffic-weighted *preserve* rows pass on new and the first migration rehearsal has run. What follows is Phases 5.4 to 8: the system is complete, migration rehearsals run until one fits the weekend with no manual steps, a two-week parallel run reconciles daily, the rollback is rehearsed in staging, and the single cut-over moves every row to `moved`, with the reminders panel reaching users with everything else. After the rollback window the old app is switched off before the host date and deleted from the tree.

---

## 8. Sources

- Joel Spolsky, "Things You Should Never Do, Part I" (2000): https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i/
- Cartwright, Horn, Lewis, "Patterns of Legacy Displacement" (martinfowler.com): https://martinfowler.com/articles/patterns-legacy-displacement/
  - Feature Parity: https://martinfowler.com/articles/patterns-legacy-displacement/feature-parity.html
  - Transitional Architecture: https://martinfowler.com/articles/patterns-legacy-displacement/transitional-architecture.html
  - Legacy Mimic: https://martinfowler.com/articles/patterns-legacy-displacement/legacy-mimic.html
  - Event Interception: https://martinfowler.com/articles/patterns-legacy-displacement/event-interception.html
  - Divert the Flow: https://martinfowler.com/articles/patterns-legacy-displacement/divert-the-flow.html
- Martin Fowler, "Strangler Fig Application": https://martinfowler.com/bliki/StranglerFigApplication.html
- Thoughtworks Technology Radar, "Parallel run with reconciliation": https://www.thoughtworks.com/radar/techniques/parallel-run-with-reconciliation
- Thoughtworks, "Breaking out of legacy, nine lessons for business leaders (Part 3)" (feature parity as an antipattern): https://www.thoughtworks.com/insights/blog/breaking-out-of-legacy-nine-lessons-for-business-leaders-part-3
- Herb Caudill, "Lessons from 6 software rewrite stories" (2019), original on Medium (could not be fetched directly); read through summaries:
  - https://simonwillison.net/2019/Feb/19/lessons-6-software-rewrite-stories
  - https://elezea.com/2019/02/when-its-appropriate-to-rewrite-your-software/
- Characterisation / approval testing (Feathers):
  - https://en.wikipedia.org/wiki/Characterization_test
  - https://understandlegacycode.com/blog/characterization-tests-or-approval-tests/
- Second-system effect (Brooks): https://en.wikipedia.org/wiki/Second-system_effect
- Cut-over dress rehearsal and rollback plan (Microsoft Dynamics 365 implementation guide): https://learn.microsoft.com/dynamics365/guidance/implementation-guide/prepare-go-live-cutover-strategy
- Data migration executive checklist (reconciliation spec, go/no-go, rollback rehearsal): https://keyholesoftware.com/wp-content/uploads/Data-Migration-Executive-Checklist.pdf
- Shadow traffic for stateful migration (idempotency keys, no committed state): https://dev.to/son_do_3543eb233b59d424bc/running-two-ach-stacks-in-parallel-the-shadow-traffic-migration-5ann
- Traffic shadowing runbook (duplicate side effects, false readiness): https://www.automq.com/blog/runbook-design-for-traffic-shadowing-for-migration
- Silent database-migration failure modes (counts are not enough): https://sia.hackernoon.com/why-most-database-migrations-fail-silently-5-hidden-failure-modes-in-zero-downtime-replatforming

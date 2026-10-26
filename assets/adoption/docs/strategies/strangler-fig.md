# Strategy playbook: strangler-fig

New capability grows beside the old system, or in new modules inside it, and takes its traffic one capability at a time through a seam, with both systems live. The ADR's `End:` line says how much moves. Under `End: all` everything does and the old app is deleted at the end: this is what people call an *incremental rewrite*, and **it is the recommended way to replace a system on a new stack**. Under `End: partial` only the capabilities that need to change move, and the old home stays, frozen, for the rest. The rule this strategy imposes on a new feature, either way: **once `Strategy: strangler-fig` is accepted, every product change lands in the new home**, and the old home takes only bug fixes, security fixes and seam changes.

---

## 1. What it is

The old system keeps running. A **seam** with a **routing point** (Feathers: "a place where you can alter behavior in your program without editing in that place"; the enabling point is where the choice is made) is put in front of it, or into it. A **new home** is stood up beside it. From then on, two kinds of work flow through the seam:

- **New capability**, meaning feature requests. These are built in the new home and routed or composed into what users already see. Nothing new is added to the old home. AWS puts it bluntly: "When you want to add new features to your application, you implement them as new microservices instead of adding features to the existing monolith. However, you continue to fix bugs in the monolith."
- **Existing capability.** Each one is characterised, rebuilt in the new home, routed behind a flag, dual-run, moved, retired in the old home, then removed.

To make the two systems coexist you build **transitional architecture**: proxies, includes, mimics, views, anti-corruption layers and CDC feeds. It is "code that will go away once the modernization is complete", and you *will* "invest in work that will be thrown away" (Cartwright, Horn, Lewis). It is a first-class, tracked asset with its own removal date.

Why the rule matters: if a strangler's slices land in the old home, it is just the old home with a new label. That is the natural drift when no new home exists yet and nothing says one has to: the old code is where everything already is, so the first feature goes there, and the next. Everything below is ordered to make that outcome impossible rather than merely discouraged.

**How much moves: `End: all` or `End: partial`.** How traffic moves and how much of it moves are separate choices. A strangler always moves traffic one capability at a time, with both systems live; the `End:` line records how much:

- **`End: all`** (the incremental rewrite). Every capability moves, and the strategy is finished only when the old app is deleted from the tree: the last ledger row, "legacy app", reads `removed`. Because nothing may be left behind, this end needs what a rewrite needs to preserve behaviour: a full behaviour inventory in `docs/parity.md`, each row marked *preserve*, *preserve-quirk*, *fix* or *drop* with usage evidence ("port the behaviour, not the bugs"); one parity suite run against both systems; and a dated `Checkpoint:` (Phase 4, §2).
- **`End: partial`.** Only the capabilities that need to change move. The rest stay in the old home, frozen, recorded as staying with an owner and a review date. There is no full inventory: each capability is characterised when it moves.

**Why `End: all` is the recommended way to replace a system.** Wanting the old system gone and a new stack is a reason to replace it, not a reason to switch everything at once. Fowler, Cartwright, Horn and Lewis argue that incremental delivery of the parts is where the risk goes down. In a big-bang plan, "changing business needs would overtake their current tech strategy" and "the majority of the work" is abandoned. Most rewrites are cancelled or overrun, often halfway; under a strangler every capability moved is a win on its own, already serving real traffic on the new stack, so a programme stopped halfway still leaves value behind (and can become `End: partial` rather than a loss). A single, rehearsed cut-over of a system built complete is [rewrite.md](rewrite.md), and its ADR has to say why a strangler with `End: all` cannot do the job.

### When it is right
- The old system has to keep serving while it is replaced, and users or the business will not wait for a rewrite (AWS: "The business wants to add new features and cannot wait for the transformation to be complete").
- Requests can be intercepted: HTTP in front, a front controller, a message bus, a single write entry point in the database (for example a set of stored procedures every change goes through), templates.
- You can change the old system's source a little, to add seams. You can also do it without source access if the database is an integration point (Azure: database-centric apps "can send messages to new services without changing the application code"; change data capture).
- The old platform is a dead end. Examples are an unsupported runtime, an end-of-life framework, or a build that cannot be reproduced. Investment in the old home is waste unless it is going to stay.
- You want the old system gone and the work on a new stack. Choose `End: all` with the new home `beside`: the incremental rewrite.
- Only part of the system needs to change, and the rest is stable and rarely touched. Choose `End: partial`: move what needs to change and leave the rest frozen, with an owner.

### When it is wrong (warning signs)
Do not choose it when (Azure, AWS):
- Requests cannot be intercepted and there is no changeable integration point.
- The system is small and a replacement is simple, so coexistence costs more than it saves. A lift-and-improve (`in-place`) or a single cut-over ([rewrite.md](rewrite.md)) is cheaper.
- The old system cannot be put behind any seam, or its data cannot be split by capability at all. Then capabilities cannot move one at a time, and the honest choice is a single cut-over ([rewrite.md](rewrite.md)).
- The original must be decommissioned fast. A strangler is slow by design.
- The domain is unclear and boundaries would be guessed. Run event modelling or storming first (AWS: "premature decomposition ... is costly").
- Nobody will own the transitional architecture's removal. You will end up with two systems for ever.

Signs that it is going wrong:
- The old home's size or route count goes up after the strategy is accepted.
- No traffic has reached the new home some weeks into the adoption.
- The new home's model mirrors the legacy tables (`TblCustomer` becomes `CustomerEntity`), with no anti-corruption layer.
- "Feature parity" shows up as a goal. Thoughtworks: "In general this is a pattern that we don't recommend ... Overwhelmingly we've seen feature-parity exercises be a tale of frustration". About half of legacy features go unused. Under `End: all` the inventory in `docs/parity.md` exists to prevent exactly this: every behaviour gets a decision, and *drop* is a decision.
- Under `End: all`, the `Checkpoint:` passes with no capability moved, or the date slips without a review.
- Both systems write the same rows (dual-write).
- Ledger rows sit at `routed` for weeks with no dual-run evidence.
- The proxy grows business logic.

---

## 2. What the ADR records

The ADR is accepted before any product slice is drafted. slipwai should refuse `Status: accepted` unless every line below is present.

```
Strategy: strangler-fig
Why: <outcome sought, e.g. "leave an end-of-life runtime and framework with unpatched CVEs; ship features weekly">
Not chosen: <in-place / rewrite, and why not>
End: all — the old app is deleted by <checkpoint date>  | End: partial — only the capabilities that need to change move; the old home stays, frozen, for the rest
Freeze: agreed — <who, when>  | Freeze: absent — <what instead>
Freeze scope: old home accepts bug fixes, security fixes, seam changes only
New home: inside <module path, e.g. src/<module>> | beside <repo path, e.g. services/<name>>
Seam: <the routing point, e.g. "nginx reverse proxy in front of the old app server; SSI for page fragments" (beside) or "the front controller and the central facade, choosing old or new per capability" (inside)>
Seam owner: <person>
New home stack: <beside only: proposed from survey> (override: <person, why> | none)
Target: <e.g. "modules in one deployable, hexagonal inside each — module map: docs/architecture/module-map.md"; see target-shape.md>
Data approach: <e.g. "phase 1 read via contract views; phase 2 CDC → new-home store; legacy owns all writes until a capability's move">
Write ownership rule: one writer per table at any time; never dual-write
Parity: <End: all only — "every behaviour on docs/parity.md is decided (preserve / preserve-quirk / fix / drop) and its rows pass against both targets before its capability moves">
Checkpoint: <End: all only — date — what is reviewed (e.g. "capabilities moved, traffic-weighted preserve rows moved"); what makes us stop or change course (e.g. "nothing moved: stop, or switch to End: partial")>
Finish line: <End: all — "legacy app deleted, legacy schema dropped, proxy reduced to plain ingress or removed"; End: partial — "every capability that needed to change has moved and been removed from the old home; the rest recorded as staying">
Review cadence: <e.g. ledger reviewed fortnightly>
```

Why each line matters:
- **End.** It says what "finished" means before anyone starts, so it cannot drift. `End: all` commits to deleting the old app and brings in the parity inventory and the checkpoint; `End: partial` commits only to the capabilities that need to change, and names what stays. Changing the end later is a superseding ADR, not a quiet slide.
- **Parity** (`End: all`). "Port the behaviour, not the bugs": parity is defined per behaviour in `docs/parity.md`, and each behaviour is marked *preserve*, *preserve-quirk*, *fix* or *drop*, with usage evidence. The person who owns the product decides; an agent cannot. A capability is done when its rows pass against both targets, or are deliberately changed.
- **Checkpoint** (`End: all`). It makes stopping or changing course a planned outcome, not a failure. It is dated, names what is reviewed and what makes us stop, and is where the review "continue / switch to `End: partial` / stop" happens. Since every capability moved already serves real traffic, none of these loses the work done.
- **Freeze.** Without a freeze, the old home keeps gaining features and the target keeps moving. If a freeze is `absent`, the "instead" has to be enforceable, for example "old-home product changes need a ledger row that schedules their move".
- **Seam.** Naming the routing point forces the question "how does a request reach the new home?" to be answered before work starts.
- **New home and stack.** This is a *path*, so it can be checked in the tree. For `beside`, the stack comes from the survey (team language, existing skills, deployment target), and a person can override it. The override is recorded. For `inside`, the stack is the deployable's own.
- **Target.** What the new home is shaped as: modules, how they deploy, and the layering inside each. It is a separate decision from the strategy; see [target-shape.md](target-shape.md). New-home code is born in that shape.
- **Data approach.** Shared DB phases (Newman ch. 4): database view → database wrapping service → CDC or outbox → split. Azure describes the per-domain version: new service on the shared DB → ETL plus CDC into a domain DB with consistency checks → cutover and drop the legacy objects. Rollback stays possible until the drop. For `inside`, the same idea runs within one database: per-module ownership of tables instead of a second store.
- **All of `End:`, `Seam:`, `New home:` and `Data approach:` (and, under `End: all`, `Parity:` and `Checkpoint:`), not only `Strategy:` and `Freeze:`.** Without them the gates in §5 have nothing to check against.

### Where the new home lives: inside or beside

The strangler's new home is either a **new module in the same deployable** (`inside`) or a **new deployable** (`beside`). The per-capability steps (characterise → build new → route → shadow → move → retire → remove) and the ledger are the same either way; what differs is where the seam is and what has to be built to make the two coexist.

```
New home: inside <module path> | beside <path>
```

| | `inside` | `beside` |
|---|---|---|
| New home | New module(s) in the same codebase and deployable, in the target shape | A new application, its own build and deploy |
| Seam | In code: the front controller or central facade chooses old or new per capability, by branch by abstraction | At the network: a reverse proxy routes paths; includes (SSI/ESI) or fragments compose panels |
| Routing point | A code switch or flag (`C.route = legacy\|shadow\|new`) | A proxy rule or flag |
| Transitional pieces | Abstraction layers over old paths, flags, adapters over old tables, in-process events | Proxy rules, the auth bridge, includes, contract views, data feeds (CDC, sync agents) |
| Cost | No new infrastructure; one release; one database transaction is still available | A second deployable and pipeline, network hops and their failure modes, cross-system auth and data sync |
| Constraint | Only as current as the deployable it lives in: new code shares the old runtime, framework and build | None from the old platform beyond the seam |
| Suits | A live or upgradeable platform | A dead platform, or a need for a different stack |

**How to judge it:**
- **Is the platform alive, or upgradeable in rungs?** If yes, `inside` is usually cheaper: new modules ride the rungs as they land. If it is dead (unpatchable runtime, unbuildable dependencies), new code put inside it inherits the dead end, so go `beside`.
- **Does the new work need a different stack** (language, framework, runtime) than the old deployable can host? Then `beside`.
- **What is the appetite for infrastructure?** `beside` adds a proxy, a second pipeline, an auth bridge and data feeds, all of which are ledger rows to remove later. `inside` adds none.
- **How big is the team?** A small team (1–8) rarely has an organisational reason for a second deployable; independent teams with independent release needs may.

Either way the new home is built in the `Target:` shape from its first line. Going `inside` is also how a strangler and a modular-monolith target combine: the new modules are the new home, and the old paths behind the facade are what the ledger retires.

---

## 3. Phases

Each step lists who does it (P = person, A = agent, B = board), the **evidence** (something you can check in the tree or on the board) and what it **unblocks**. Phases 2 and 3 have a `beside` path and an `inside` path; every other phase is shared, with "the proxy" read as "the in-code routing point" when `New home: inside`. Phase 4 applies under `End: all` only, and the finish line differs between `End: all` and `End: partial`.

### Phase 0: make the old system safe
Quick wins and safety, in days.

**0.1 Rotate and remove committed secrets.** Move them to environment variables or a secret store, keep a scanner in the gate, and leave the history-rewrite decision to a person.
- Who: A proposes, P rotates.
- Evidence: the secret scan in `make verify` is green; `.env.example` exists.
- Unblocks: running the legacy app in CI and in containers.

**0.2 Build floor, by where the new home lives** (`build-floor.md`). The old home meets the floor's eight criteria either way; what differs is how far.
- **`beside`:** pinned as it is. For example, the existing build inside a container pinned to the old toolchain, the old app server in a container, and the database in a container with the schema scripted. The old home is *not* upgraded: it only gets runnable, and modernising it is work thrown away.
- **`inside`:** up to date. The new modules are built with the old deployable's toolchain, so the toolset is brought fully current and the target raised as high as the code allows, the ceiling recorded on the ADR's `Build:` line, exactly as under in place. An `inside` home on a toolchain that cannot be brought current is the sign it should be `beside`.
- Who: A.
- Evidence: `make legacy-up` serves the app locally and in CI; the ADR's `Build:` line says `pinned as-is` (`beside`) or `up-to-date` with the target ceiling (`inside`).
- Unblocks: characterisation and the seam.

**0.3 Install the gate and the ratchet.** Baseline existing findings.
- Who: A.
- Evidence: `make verify` green; ratchet baseline committed.
- Unblocks: everything else.

### Phase 1: freeze and decide

**1.1 Accept the strategy ADR** with all the §2 lines. A drafts the ADR from the survey and the convergence map.
- Who: A drafts; P accepts on the board.
- Evidence: an `adr/NNNN-*.md` file with `Status: accepted`, `Strategy: strangler-fig` and a `Freeze:` line.
- Unblocks: the home guard switches on (§5) and the new-home step unlocks.

**1.2 Announce the freeze.** Add a `CODEOWNERS` or PR template note on the old-home paths: "bug/security/seam only".
- Who: A, P agrees.
- Evidence: the old-home paths are listed in `.slipwai/homes.yml` as `role: legacy`.
- Unblocks: the home guard has paths to guard.

### Phase 2: find the seams and the routing point

**Beside path.**

**2.1 Survey for seams**, outermost first (Event Interception: reverse proxies, API gateways, web front ends via progressive enhancement, messaging, DB triggers or CDC). The database is the latest point you can intercept and the riskiest. Record:
- the **HTTP seam** (proxy in front: path, host and header routing),
- the **UI seam** (how new UI reaches old pages: page-by-page routing for whole pages; SSI/ESI or a client-side fragment for panels inside old pages),
- the **write seam** (where state changes funnel: front controller, command handler, database procedures),
- the **read seam** (views or queries the new home may use).

- Who: A runs `/survey`, P confirms.
- Evidence: a `seams` section in the convergence map naming files and lines.
- Unblocks: placing the routing point.

**2.2 Put the routing point in place with zero behaviour change.** The proxy sends 100% to legacy. Characterisation tests run *through the proxy*. Watch that the proxy does not become a single point of failure or bottleneck (Azure, AWS): give it health checks and keep it dumb.
- Who: A.
- Evidence: proxy config is in the repo; `make verify` runs characterisation against the proxied URL; the ledger has a transitional row "proxy → legacy (pass-through)".
- Unblocks: any routing.

**Inside path** (replaces 2.1–2.2 when `New home: inside`).

**2.1i Declare modules and freeze the violation baseline.** From the module map ([target-shape.md](target-shape.md)), give each module a published `<module>/api` (and `api/events`) and a private remainder. Run the boundary checker once and record every existing violation as a ratcheted baseline, plus a `check-data-ownership` baseline for SQL, ORM mappings and wiring the import scan cannot see. Mark the old code's packages `role: legacy` in `homes.yml` and the new modules `role: new`, strict.
- Who: A; P reviews the baseline.
- Evidence: both baselines committed and in `make verify`.
- Unblocks: the routing point.

**2.2i Make the god facade and base class the in-code routing point, with zero behaviour change.** By branch by abstraction: put an interface in front of each capability's entry (the facade method, or the concern the base controller provides), implemented first by delegation to the existing code. The front controller or facade then chooses old or new per capability through a flag (`C.route = legacy|shadow|new|cohort:N%`), default `legacy`. Freeze "no new callers of the facade" and "no new subclasses of the base".
- Who: A.
- Evidence: characterisation green through the abstraction; the ledger has a transitional row per abstraction layer (`remove when: C retired`).
- Unblocks: any routing.

### Phase 3: stand up the new home before any product slice

**Beside path.**

**3.1 Generate the new home**: `slipwai add-service <name> --backend <stack>`.
- Who: A, after P confirms the stack.
- Evidence: `services/<name>/` exists; its tests run in `make verify`; it has a health endpoint.
- Unblocks: deploying it behind the seam.

**3.2 Deploy it behind the seam.** The proxy routes `/next/health` (or similar) to the new home.
- Who: A.
- Evidence: a characterisation or smoke test hits `/next/health` *through the proxy* in CI; the ledger gets a transitional row "proxy route /next/* → new home".
- Unblocks: **the first product slice.** Until 3.1 and 3.2 pass, slipwai refuses to `/sail` any product slice.

**3.3 Build the anti-corruption layer stub** in the new home: a module (`legacy/`) that is the only code allowed to know legacy table names, message formats or database procedure names.
- Who: A.
- Evidence: an architecture test inside the new home ("only `..legacy..` imports the legacy JDBC datasource").
- Unblocks: any new-home code that reads legacy data.

**Inside path** (replaces 3.1–3.3 when `New home: inside`). There is no proxy, include or auth bridge: a new module's code runs in the same request and session. Rollback is a flag flip or a reverted commit.

**3.1i Generate the first new module in the target shape** (strict, and hexagonal inside if `Target:` says so) with its tests in the gate.
- Who: A.
- Evidence: the module exists under the `New home:` path; a smoke test reaches it through the routing point.
- Unblocks: **the first product slice**; the same new-home readiness gate applies.

**3.2i Per-module data ownership.** Each table and DB routine has one owning module in `homes.yml`. New modules own new tables from day one. Old tables are read through adapters in the new module (its anti-corruption layer) until the capability moves; then ownership transfers, cross-module JOINs are replaced by API calls or read models, and only the owner writes.
- Who: A; P approves ownership transfers.
- Evidence: the `check-data-ownership` baseline falls.
- Unblocks: moving write capabilities.

**3.3i In-process events between modules.** Where a new module reacts to something the old code does, the old path publishes a past-tense domain event through an in-process publisher (one added at the abstraction layer, not scattered through legacy code) and the new module subscribes. The new module never calls back into legacy internals.
- Who: A.
- Evidence: no cycles between modules in the checker; listeners tested with the publisher absent.
- Unblocks: new modules that react to legacy behaviour.

### Phase 4: know what to preserve (`End: all`)

Under `End: all` nothing may be left behind, so the whole system's behaviour is listed and decided before the capability order is fixed. This runs after the new home is routed, so the first feature slices do not wait for it. Under `End: partial`, skip this phase: each capability is characterised in 6.1 when it moves, and usage evidence is gathered per capability in 5.1.

**4.1 Behaviour inventory** (`docs/parity.md`). One row per behaviour: entry point (URL / action / database routine / batch job / report / outbound integration), observed usage, owner, decision (*preserve / preserve-quirk / fix / drop*), the capability it belongs to, its characterisation tag, and its status in the new home.
- Who: A drafts from the survey (route or action mappings, page templates, database routines the app calls, scheduled jobs, outbound integrations, plus access logs where they exist); P marks each decision via `/ground` questions on the board.
- Evidence: every entry point the survey finds appears in `parity.md`, and none has a blank decision. A convergence check compares the survey's route list with the table.
- Unblocks: the capability order (5.1) and the `legacy app` ledger row. This is where *drop* earns its keep: Fowler's logistics example spent effort on package types the business had already decided to stop.

**4.2 Usage evidence.** Turn on or collect access logs, and count hits per action for a few weeks where possible.
- Who: P provides logs, A summarises.
- Evidence: a usage column in `parity.md`; a *preserve* row with zero usage carries a reason.
- Unblocks: honest *drop* decisions.

**4.3 One parity suite, two targets.** The characterisation suite is parameterised by `TARGET=legacy|new`, and each *preserve* and *preserve-quirk* row points at its tests. *Fix* rows carry a new expected output and the owner's note; *drop* rows are removed from both.
- Who: A.
- Evidence: `make parity TARGET=legacy` is green; `make parity TARGET=new` runs and fails honestly for rows not yet built.
- Unblocks: per-capability "done" in 6.2, which under `End: all` means "its rows are green against both".

### Phase 5: choose the capability order

**5.1 Rank capabilities.** Use the convergence map and event model. Score each on coupling (fewer inbound callers and tables is better), value of change (the business wants to change it soon), risk (read-only before write), and whether it unblocks others. The guidance:
- Begin with **new features** (no parity risk, real traffic to the new home early), then **read-only** capabilities, then **writes by domain**.
- Consider *Divert the Flow* early: cross-cutting aggregators such as reports and dashboards, when feeding the legacy version is costly.
- Use *Extract Product Lines / Value Streams* to slice by business line rather than technical layer.
- Refuse parity scope: for each capability ask "is this used?" (logs or analytics, or under `End: all` the usage column in `parity.md`) before rebuilding it. Drop it in a ledger row with `status: removed (not rebuilt)`, signed off by P.
- Under `End: all`, every capability in `parity.md` gets a place in the order; under `End: partial`, only those that need to change, and the rest are listed as staying.

- Who: A ranks; P edits and signs off drops.
- Evidence: a ranked `Capability order` table in `retirement.md` or the programme.
- Unblocks: Phase 6 for the top capability.

### Phase 6: per capability (repeat)
For capability C, each status change is a ledger row update (`date | capability | from | to | routed by | pinned by | status`).

**6.1 Characterise.** `/characterise` pins C's behaviour at the *boundary* (HTTP responses, DB effects of writes), through the proxy.
- Who: A.
- Evidence: tests tagged `C` green against legacy; ledger row created with `pinned by: tests/characterise/C`.
- Unblocks: 6.2.

**6.2 Build.** New-home slice(s) implement C behind the ACL; the same characterisation suite runs against the new home, pointing at a different base URL.
- Who: A fleet.
- Evidence: suite green on both targets, except documented intentional differences (under `End: all`, C's `parity.md` rows read `new: passing`, and every difference is a *fix* row with an owner).
- Unblocks: 6.3.

**6.3 Route.** A proxy rule or front-controller flag `C.route = legacy|shadow|new|cohort:N%`.
- Who: A; P approves.
- Evidence: flag in config, default `legacy`; ledger `routed`, `routed by: nginx map / flag C.route`.
- Unblocks: 6.4.

**6.4 Dual-run / shadow.** *Parallel run* (Newman) or *dark launching*: reads are shadowed, responses compared and diffs logged (GitHub Scientist style); writes still go to legacy only, and the new home consumes them via CDC and compares derived state.
- Who: A; P reviews diffs.
- Evidence: a reconciliation report under threshold for an agreed period, linked from the ledger row.
- Unblocks: 6.5.

**6.5 Move.** Flag to `new` by cohort (canary), then 100%. Write ownership transfers: the new home becomes the single writer, and legacy reads via view or mimic if still needed. The migration is rehearsed with reconciliation and rollback.
- Who: P decides, A executes.
- Evidence: flag at 100%; rollback rehearsal log; ledger `moved`.
- Unblocks: 6.6.

**6.6 Retire.** The old code path is unreachable: route removed from the legacy front controller, flag deleted.
- Who: A.
- Evidence: legacy route count down; characterisation of C runs only against new; ledger `retired`.
- Unblocks: 6.7.

**6.7 Remove.** Old code, templates, database procedures and tables deleted (tables only after data ownership has moved and the rollback window has closed, per Azure).
- Who: A; P approves the drop.
- Evidence: the diff deletes files; a schema migration drops the objects; ledger `removed`.
- Unblocks: the next capability, and any transitional rows whose `remove when:` names C.

### Phase 7: data, alongside
This runs alongside Phase 6.

**7.1 Shared DB with contract (D1).** The new home reads only through `views` in a `contract` schema that the legacy DBA owns (Database View). No new-home code touches base tables.
- Who: A writes the views as a legacy-owned migration; the legacy DBA (P) owns them.
- Evidence: a `contract` schema and a read-only login granted SELECT on it only; a transitional ledger row for the views.
- Unblocks: new-home reads of legacy data.

**7.2 Wrap (D2).** Where legacy writes go through one entry point (a front controller, a command handler, or a set of database procedures), treat it as a *database wrapping service* and route new-home writes for not-yet-moved capabilities through it via the ACL. Never insert into the tables directly.
- Who: A.
- Evidence: new-home writes to legacy data appear only in the ACL's calls to the wrapping entry point.
- Unblocks: new-home writes before a capability moves.

**7.3 CDC or outbox (D3).** Use the database's native CDC or Debezium on the legacy tables, or on a write log table if the old home keeps one, to feed new-home projections. When a capability moves, the new home writes to its own store and publishes through a **transactional outbox**. A sync agent applies the changes to legacy tables still read by unmoved capabilities (AWS). This is one writer per row, always.
- Who: A.
- Evidence: CDC feed and outbox in config, each a transitional ledger row; projections reconcile with legacy.
- Unblocks: dual-run of writes (6.4) and moving write capabilities.

**7.4 Split (D4).** After `moved`, migrate historical data (ETL), reconcile counts and checksums, switch reads, then drop the legacy objects at `removed`.
- Who: A; P approves the drop.
- Evidence: reconciliation report; a migration that drops the legacy objects.
- Unblocks: 6.7 for that capability.

**7.5 Record schema ownership** in `homes.yml`: each table is `owner: legacy|new-home` and `readers: [...]`. The gate refuses migrations from a non-owner.
- Who: A; P approves changes of owner.
- Evidence: `homes.yml` ownership entries; the ownership check in `make verify`.
- Unblocks: the single-writer rule being enforced rather than hoped for.

**Event-modelling honesty:** legacy is an *external system* on the board. The requests its write entry point receives are *commands*, not domain events. The ACL translates a *successfully processed* legacy change into new-home events. Do not rename tables into events, and do not model write-model state as events.

### Finish line

The finish line is the one the ADR's `End:` line chose.

**F.1 Remove the transitional architecture whose condition is met.** Each transitional row (proxy rules, includes, mimics, views, CDC feeds, the auth bridge) whose `remove when:` has been reached is deleted. Under `End: partial`, the seam and whatever the staying capabilities still need remain, as standing rows with an owner.
- Who: A; P approves each drop.
- Evidence: every transitional row whose condition is met reads `removed`.
- Unblocks: F.2 or F.3.

**F.2 `End: all` — delete the old app.** Every capability row is `removed` or `removed (not rebuilt)`, and the last row, `legacy app`, reaches `removed`: the legacy deployable is deleted from the tree with its build and the characterisation tests that only target legacy. Legacy-only database objects are dropped after the retention window. The proxy is reduced to plain ingress or deleted (Azure step 4). The parity suite stays, `TARGET=new` only, as the new home's regression net.
- Who: A deletes; P decides retention.
- Evidence: the survey no longer finds the legacy app; `homes.yml` lists no legacy home, so the home guard and strategy checks retire with it; the ADR gets `Finished: <date>`.
- Unblocks: nothing further; the strategy is complete.

**F.3 `End: partial` — record what stays.** Every capability that needed to change has moved and been removed from the old home. What remains is recorded in `retirement.md` as `staying (frozen)`, each row with an owner and a review date, and the old home keeps its freeze, its home guard and its legacy-size ratchet.
- Who: P names the owners and the review date; A writes the rows.
- Evidence: no capability row sits between `routed` and `retired`; every remaining capability has a `staying (frozen)` row with an owner and review date; the ADR gets `Finished: <date> (partial)`.
- Unblocks: the review, which may reopen the strategy (a superseding ADR, for example `End: all`) if a staying capability needs to change.

---

## 4. How a feature request is handled

This is the common case. **Every feature request becomes a new-home slice plus a composition step.** It is built in the new home, never in the old one, and then reaches users in one of these ways:

- **Whole new page:** route the path at the proxy, `/reports` → new home. Navigation links in old pages are a seam change.
- **Panel inside an old page:** use *UI composition* (Newman). The options, in order of preference:
  1. **Server-side include at the proxy** (nginx `ssi on` / ESI). The old template gets a single `<!--# include virtual="/next/fragments/x" -->` line, and the proxy stitches the HTML. There is no JS, it degrades to empty on failure (`ssi_silent_errors`), and it is cacheable. Edge or proxy composition suits migrations in particular (AWS micro-frontends guidance).
  2. **A client-side fragment**: a `<div data-fragment="/next/fragments/x">` plus a 20-line loader (progressive enhancement). Use this when the proxy cannot do SSI.
  3. **iframe**: the last resort, for auth or styling isolation.
- **For `New home: inside`,** the page or the region is simply served by the new module through the routing point; there is no proxy include.

**Auth across the seam.** The proxy authenticates the fragment request against the legacy session (nginx `auth_request` to a tiny legacy session-check endpoint, or a signed header). This is a legacy mimic and is transitional. It goes in the ledger. For `inside` there is nothing to bridge: the new module runs in the same request and session.

**Which of the two, judged per feature.** The spec records `Visibility: page | seam` with the reason (a strangler has no cut-over to wait for). Choosing `page` means the new home serves a new version of the whole page, in its own UI, so the old page's existing behaviours join the slice as acceptance criteria tagged *parity*, pinned by `/characterise` at that URL first, and the page's capability row starts in the ledger. The draft proposes one from what can be measured: how much else is on the page (its characterised behaviours), what it cannot own (the menu and layout, the session, links out — a whole page still needs the auth bridge), how it looks (a new page among old ones, or a new panel inside an old one; `/mockups` draws the chosen option, both where it is close, and the storyboard verdict decides), and the freeze (a seam is a change to the old home). Few behaviours on the page favour `page`: it moves a capability while it builds the feature, and leaves no include to remove later. For `New home: inside` the same judgement holds: `page` means the page is simply served by the new module (the routing point sends that URL to it), and `seam` means the old page's template or controller calls the new module for one region, a one-line `Legacy-change: seam` with no proxy or auth bridge.

**What the spec carries.** The slice's spec names `Lands in: services/<name>` (or the inside module path). Any slice that users must see in an existing screen has a **Composition** section: whole-page route or fragment include, the exact old-home seam line, auth across the seam, and fallback on failure. The evidence that it was done right: the old-home diff contains only the include line, tagged `Legacy-change: seam`, and a ledger row `routed` names the include.

**Data for new features.** Read through the ACL from contract views at first (Newman: Database View). When freshness or load matter, switch to CDC into the new home's own read store. New features that *write* own their own tables in the new home's schema from day one. If the old home must see the data, a service-consuming mimic or sync agent pushes it back (AWS "synchronizing agent"). It never goes the other way through a dual-write.

---

## 5. How the method carries it

### Adoption sequence on the board
The board's voyage, and `slipwai adopt --next`, walk the same sequence. Each step is a card; later cards stay blocked until earlier evidence exists in the tree.

1. **Survey**, then the convergence map, the gate and the ratchet, as under every strategy.
2. **Decide.** The board's decide step is a form that asks exactly the strangler fig's lines: `Freeze:`, `New home:`, `End:` and `Target:`, plus `Parity:` and `Checkpoint:` when `End: all`. The new home's stack is proposed from the survey (the old language's language package, a browser app where the old app served pages, Postgres where there is a database), and a person may override it. A language package that is not installed is said with the command to install it, `slipwai language install <name>`. The board writes the ADR with every line plus a derived `Build:` line, and commits it. The strategy record reads the accepted ADR's `Name: value` lines; a required line that is missing is said by `check-convergence` and on the board, and the decision still stands. A person who picks *rewrite* is offered "Use a strangler fig instead" (`beside`, `End: all`; see [rewrite.md](rewrite.md), §5).
3. **Build floor**, then **`smoke`**, after the decision and before the constitution.
4. **The new home**, by where it lives:
   - `beside`: "generate the new home", which the board runs itself: `add-service` with the chosen stack, then `add-frontend` when a browser app was chosen, each committed.
   - `inside`: "declare the modules and freeze their violations" (`docs/module-map.md`). This is an agent step the board names; it does not do it.
5. **Parity** (`End: all`): write `docs/parity.md`, the behaviour to keep. An agent step the board names; the person marks each row *preserve / quirk / fix / drop*.
6. **Draft**: PRD → constitution + first spec (below).
7. **Sail**: the first slice.

Under `End: all` the board shows the `Checkpoint:` date for the whole programme and, once it has passed, puts the decision again through the decide form: carry on with a new date, change the decision (for example to `End: partial`), or stop.

### Draft, spec and mock-ups
- `/draft` reads the strategy and this playbook, and refuses while the decision is missing or incomplete. The feature is specified where the strategy lands it: the new home.
- Every spec ends with `## Strategy fit`, holding `Lands in:`, `Visibility: page | seam` with the reason (§4), and `Composition:` (whole-page route or fragment include, the exact old-home seam line, auth across the seam, and fallback on failure). For a strangler, the hard part of almost every early feature is how it reaches an old screen, so this section is required rather than optional. When the ADR's `Target:` is modular, the spec also holds `Module:`, `Publishes:`, `Consumes:` and `Owns data:`.
- A PRD line that contradicts the strategy is overridden in the spec and quoted beside the ADR line it contradicts.
- `/mockups` draws in the new home's UI where the spec lands there: for `page`, the whole new page; for `seam`, the old page with the new panel; where the choice is close, both, and the storyboard verdict decides.
- `/sail`'s plan stage holds each slice to the strangler fig's rules.
- The proxy config, SSI include and auth bridge a slice needs are written by the agent in that slice; nothing generates them.

### Constitution
The draft writes the strangler-fig clause into the constitution from the ADR. In substance:
- "Product changes land in `services/<new-home>`. `apps/<legacy>` accepts bug fixes, security fixes, and seam changes recorded in `retirement.md`, nothing else."
- "Only `services/<new-home>/…/legacy/` may know legacy names, formats or procs."
- "One writer per table. Never dual-write."
- "No feature parity by default: a legacy behaviour is rebuilt only if it is shown to be used."
- "Transitional components are ledger rows with a removal condition."
- Under `End: all`: "The old app is deleted by <checkpoint date>. Parity is defined by `docs/parity.md`; a capability is done when its rows pass against both targets. Port the behaviour, not the bugs: a *fix* row needs the owner's decision."
- Under `End: partial`: "Capabilities listed as staying remain in `apps/<legacy>`, frozen, with an owner and a review date."

### Gates
Refuse before, do not warn after. `check-convergence`, run by `make verify`, holds these as hard checks:
- **New home first.** A spec fails before the new home exists (`beside`), or before the module map exists (`inside`).
- **Home guard.** A commit after the strategy ADR that changes the code that was here fails without a trailer `Legacy-change: security|bugfix|seam|quick-win|build|characterise`. This keeps effort off upgrading the old home.
- **Ledger consistency.** A capability `moved` with no `shadowed` row before it fails, and so does an unknown status.
- **Boundaries.** In an adopted repo `check-imports` runs through the ratchet (existing violations are a baseline). With `"layout": "modular"` on the adopted application, only its context-boundary rule applies, which is how an `inside` new home's module boundaries are held.

### Programme pacing
- The build floor comes first. `beside`, the old build is pinned as it is; `inside`, the old platform is brought up as under in-place, because new work is built with it.
- The programme has a new-home step (`beside`) or a modules-declared step (`inside`) before the first product slice.
- Mix the work: each cycle ships at least one new-feature slice in the new home (value) and advances at least one ledger row by one status (displacement).
- Under `End: all`, pace in **checkpoints, not phases**. By checkpoint 1 the new home is serving at least one real capability (a new feature counts) and the inventory has no undecided rows; by checkpoint 2 a set share of the traffic-weighted *preserve* rows have moved; the last checkpoint is the old app's deletion date. Most rewrites are cancelled halfway, so every capability moved is a win on its own: the board puts the decision again when the date passes.
- Under `End: partial`, pacing is by the capabilities that need to change; when they have all moved, the programme goes to F.3.

### Ledgers
- `retirement.md` holds **two tables**: capabilities (moving from old to new), and "Transitional pieces" (`Date | Piece | Why | Remove when | Status`) for the proxy rules, includes, mimics, views, CDC feeds and auth bridge the seam needs. Transitional pieces are needed because Fowler and Thoughtworks treat transitional architecture as the main cost and the main thing left behind. A new feature that is only *composed* into an old page adds a piece for its include, removed when that page itself moves.
- Capability statuses are `routed`, `shadowed`, `moved`, `retired` and `removed`; `moved` needs a `shadowed` row before it.
- **The end shows in the ledger.** The programme is not finished while any transitional piece is live. Under `End: all`, every capability in `parity.md` has a row; under `End: partial`, untouched capabilities stay with an owner and review date.
- **Early rows are new features.** The first ledger rows should usually be new capabilities composed into old pages, not migrations. This gets real traffic onto the new home within the first week with no parity risk.

**Not built yet:**
- `homes.yml`, and the `Lands in:` cross-check against it.
- The legacy-size ratchet (legacy lines, routes and templates may not rise).
- The seam or proxy health route checked in CI.
- Proxy, SSI include and auth bridge scaffolding (the agent writes them per slice).
- A parity suite runner with `TARGET=legacy|new`.
- Checkpoint tracking of real traffic served, beyond the date itself.
- Per-module "strict" (no baseline) and privacy rules.
- A data-ownership check over SQL, ORM and stored procedures.
- Validating the module map.
- Baseline burn-down tracking on the board.
- The board's language install as a button (it shows the command).

---

## 6. Anti-patterns and how the method detects each

| Anti-pattern | What it looks like | Detection |
|---|---|---|
| Old home with a new label | Product slices committed into legacy paths | Home guard trailer check; `Lands in` refusal; legacy-size ratchet |
| No new home | Strategy accepted, slices drafted, `services/` empty | Draft card blocked until the New-home card has three ticks |
| Seam never built | New home deployed separately, users never reach it | Seam smoke test through the proxy required; "traffic to new home = 0" flagged on the board |
| Feature parity | The spec lists every legacy screen to rebuild | The drafter needs usage evidence per rebuilt capability; parity wording in specs is flagged |
| Dual-write | Both homes write a table | `homes.yml` single-owner check; scan for legacy-table writes outside the ACL wrapping path |
| Legacy model leaks | `TblOrder` names in domain code | ACL architecture test |
| Tables renamed into events | `CustomerUpdated` mapped 1:1 from a row change | Event-model review on the board: legacy is an external system; events come from the ACL translation of processed commands |
| Smart proxy | Business rules in nginx or gateway config | Proxy config lint: only `map`, `location`, `include`, `auth_request` allowed |
| Forever transitional | Includes, mimics and views outlive their capability | Transitional rows with `remove when:`; ledger consistency fails when the condition is met but the row is not `removed` |
| Stalled at routed | Flags exist, never flipped | Pacing check: rows unchanged for N cycles |
| Big-bang cutover in disguise | One capability called "everything" | `/strangle` caps capability size (routes/tables) and asks for a split |
| Upgrading the old home | Effort spent bumping the old framework or runtime | Platform-rung rule: legacy dependency changes need `Legacy-change: security` |
| Silent bug-fixing or bug-porting (`End: all`) | The new home quietly differs from, or copies, legacy behaviour | Parity gate: a difference from approved legacy output fails unless the row is *fix* with an owner |
| End drifting unrecorded | `End: all` quietly becomes "we'll leave the rest", or `End: partial` keeps moving untouched capabilities | `End:` is an ADR line; the checkpoint review is the only way to switch, and it supersedes the ADR. Moves of `staying (frozen)` rows are refused |
| Old app never actually deleted (`End: all`) | Everything moved, legacy still deployed "just in case" | The axis is complete only when the survey no longer finds the legacy app and its `legacy app` row reads `removed` |

---

## 7. Worked example: an internal booking app

The app here is invented and stands for any brownfield web app of this shape.

**Survey facts:** an internal booking web app of roughly 10k LOC on an end-of-life runtime and framework. Server-rendered pages from templates. Writes go through business logic in the database, which is a single funnel for every state change. Reads are hand-written SQL. The build relies on committed dependencies. No real tests. Secrets committed. First request: a **reminders panel on the dashboard** showing a user's bookings due in the next few days (read-only, derived from existing booking data).

**Seams found:**
- **HTTP:** the old app server answers on one path prefix, so a reverse proxy can sit in front of it.
- **UI:** the dashboard is one server-rendered template. A panel can be included there.
- **Write:** the database-side business logic is the funnel for every state change. It is a natural interception point (CDC on its tables, or on its log table if it keeps one).
- **Read:** plain SQL over a few booking tables, so contract views are cheap.

**The first ten steps:**

1. **Secrets out.** Rotate the committed credentials, read them from environment variables, add a secret scan to the gate. Evidence: the scan is green and `.env.example` is committed.
2. **Legacy runnable.** Containers for the old runtime, the old app server and the database (schema and seed data scripted), using the existing build as-is. `make legacy-up`. The old platform is *not* upgraded.
3. **Gate and ratchet.** `make verify` runs the secret scan, the legacy build and the ratchet baseline (legacy LOC, route count, template count).
4. **Strategy ADR accepted.** `Strategy: strangler-fig`. `Why: the runtime and framework are end-of-life and unpatchable; features wanted monthly`. `Not chosen: in-place — the platform cannot be climbed; rewrite — the app sits behind one path prefix and its pages can move one at a time, so a single cut-over would hold every gain back to the end`. `End: all — the old app is deleted by <date, about nine months out>` (an incremental rewrite: the business wants the old platform gone, not part of it). `Freeze: agreed — <owner>, <date>`. `New home: beside services/booking-next` (the platform is dead, so new code inside it would inherit the dead end). `Seam: reverse proxy in front of the old app server; SSI for fragments; auth_request to a legacy session check`. `New home stack: <from survey> (override: none)`. `Target: modules in one deployable, hexagonal inside each — module map: docs/architecture/module-map.md` (bookings, resources, accounts, reminders; see [target-shape.md](target-shape.md)). `Data approach: D1 contract views over bookings; D3 CDC when write capabilities move; legacy sole writer until then`. `Parity: every row on docs/parity.md decided and passing against both targets before its capability moves`. `Checkpoint: <date, six weeks out> — reminders panel live from the new home, inventory fully decided, dashboard moved; if nothing has moved, review: continue, End: partial, or stop`.
5. **Characterise the boundary.** `/characterise` pins login, the dashboard, booking view and create-booking at HTTP level, and for writes the resulting rows. The tests use the new stack's tooling and run against the proxy URL.
6. **Seam live, pass-through.** Proxy config in `infra/proxy/` sends everything to legacy; characterisation points at the proxy. Ledger, transitional: `proxy pass-through | remove when: legacy deployable retired`.
7. **New home generated and routed.** `slipwai add-service booking-next --backend <stack>`. Its tests join `make verify`. The proxy routes `/next/*` to it, and a CI smoke test hits `/next/health` through the proxy. The ACL module gets its architecture test. **Draft unlocks here.**
8. **Contract view (D1).** A legacy-owned migration adds a view such as `contract.v_bookings_due (booking_id, owner_id, starts_at, title)` and a read-only login granted SELECT on `contract` only. `homes.yml` records the booking tables as `owner: legacy, readers: [booking-next via contract views]`. Ledger transitional row: `contract views | remove when: bookings capability moved`.
9. **The reminders slice is built in the new home.** `Lands in: services/booking-next`. The ACL maps view rows to new-home types; the domain picks what is due. Open product questions (what counts as "due", time zones) are posted as QUESTION comments. `GET /fragments/reminders` returns an HTML fragment using the old pages' CSS classes. On the event model, legacy is an external system and the panel is a read model fed from it; no events are invented from table rows.
10. **Judge Visibility, then compose.** The dashboard carries many characterised behaviours and owns the layout and navigation, so the spec records `Visibility: seam` (a panel inside the old page; moving the whole dashboard now would pull all of that into the slice as parity). The *only* old-home change is a seam change: the dashboard template gets one include line, `<!--# include virtual="/next/fragments/reminders" -->`, with the trailer `Legacy-change: seam (retirement.md#reminders-include)`. The proxy turns SSI on for the dashboard path with silent errors, so if the new home is down the panel renders empty and the page is unchanged. Fragment requests are authorised by `auth_request` to a small legacy session-check endpoint, a second seam change. A config flag can switch the include off without a deploy. Ledger rows: transitional `reminders include | remove when: dashboard moves to booking-next` and transitional `session-check auth bridge | remove when: login capability moved`. Characterisation of the dashboard is updated deliberately to accept the new panel region, and only that.

**What follows:** because `End: all`, the behaviour inventory comes next (Phase 4): the agent lists every route, scheduled job and database routine in `docs/parity.md`, usage logs show the bulk-import screen unused, and the person marks it *drop* and every other row *preserve*, *preserve-quirk* or *fix*. The parity suite runs with `TARGET=legacy|new`, and a `legacy app` ledger row is opened. The capability order is then ranked from the inventory and the survey. A likely order: (a) the dashboard as a whole page, now that part of it is already new, routed at the proxy with legacy fallback; (b) the other read-only views; (c) booking writes, moved one request type at a time, with the new home as single writer publishing through an outbox and a sync agent applying changes to legacy tables still read by unmoved capabilities, shadow-compared via CDC during dual-run; (d) login last, which retires the auth bridge. Each step is `/strangle`, with ledger rows moving routed → moved → retired → removed, and the legacy-size ratchet falling. At the six-week checkpoint the reminders panel and the dashboard already serve real traffic from the new stack, so even a decision to stop there leaves value behind. The strategy finishes at F.2, when the `legacy app` row reaches `removed` and the old app is gone from the tree.

---

## 8. Sources

- Martin Fowler, "Strangler Fig Application" (2004, rev. 2024): https://martinfowler.com/bliki/StranglerFigApplication.html
- Martin Fowler, "Legacy Seam" (2024): https://martinfowler.com/bliki/LegacySeam.html
- Martin Fowler, "Branch By Abstraction": https://martinfowler.com/bliki/BranchByAbstraction.html
- Cartwright, Horn, Lewis, "Patterns of Legacy Displacement": https://martinfowler.com/articles/patterns-legacy-displacement/
  - Transitional Architecture: https://martinfowler.com/articles/patterns-legacy-displacement/transitional-architecture.html
  - Event Interception: https://martinfowler.com/articles/patterns-legacy-displacement/event-interception.html
  - Legacy Mimic: https://martinfowler.com/articles/patterns-legacy-displacement/legacy-mimic.html
  - Feature Parity: https://martinfowler.com/articles/patterns-legacy-displacement/feature-parity.html
  - Divert the Flow: https://martinfowler.com/articles/patterns-legacy-displacement/divert-the-flow.html
  - Extract Product Lines: https://martinfowler.com/articles/patterns-legacy-displacement/extract-product-lines.html
- Microsoft Azure Architecture Center, Strangler Fig pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig
- Microsoft Azure Architecture Center, Anti-Corruption Layer pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer
- AWS Prescriptive Guidance, Strangler fig pattern: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html
- AWS Prescriptive Guidance, Anti-corruption layer pattern: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/acl.html
- AWS Prescriptive Guidance, micro-frontend composition approaches (edge/SSI/ESI, server-side): https://docs.aws.amazon.com/prescriptive-guidance/latest/micro-frontends-aws/composition-approaches.html
- Sam Newman, *Monolith to Microservices* (O'Reilly 2019). Ch. 3: strangler fig with HTTP proxy, UI composition, branch by abstraction, parallel run, decorating collaborator, change data capture. Ch. 4: database view, database wrapping service, change data ownership, synchronise data in application, tracer write, split table. https://samnewman.io/books/monolith-to-microservices/ and https://www.oreilly.com/library/view/monolith-to-microservices/9781492047834/ch04.html
- InfoQ, Newman on monolith decomposition (QCon London 2020): https://www.infoq.com/news/2020/05/monolith-decomposition-newman/
- Shopify Engineering, "Refactoring Legacy Code with the Strangler Fig Pattern" (new interface → new table → backfill → verify → switch reads → drop): https://shopify.engineering/refactoring-legacy-code-strangler-fig-pattern
- Transactional outbox: https://microservices.io/patterns/data/transactional-outbox.html
- GitHub Scientist (parallel-run comparison library): https://github.com/github/scientist
- nginx SSI module: https://nginx.org/en/docs/http/ngx_http_ssi_module.html ; auth_request: https://nginx.org/en/docs/http/ngx_http_auth_request_module.html

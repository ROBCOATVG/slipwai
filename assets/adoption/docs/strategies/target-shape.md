# Target shape

> A strategy says *how* the change happens. A target shape says *what the code becomes*. They are separate decisions, recorded separately on the strategy ADR. Every strategy except leave-it reaches the same kind of shape by a different route, and a shape is only real once a machine refuses changes that blur it.

---

## 1. What a target shape is, and why it is separate from the strategy

The strategy ADR records three decisions:

1. **Strategy**: how the change happens. `leave-it`, `in-place`, `strangler-fig` or `rewrite`.
2. **Where the new home lives**: only for `strangler-fig` (`inside`: a new module in the same deployable, seam in code; `beside`: a new deployable, seam at the network) and `rewrite` (`beside` or `new-repo`). See [strangler-fig.md](strangler-fig.md) and [rewrite.md](rewrite.md).
3. **Target shape**: what it becomes. This document.

"Modular monolith" used to be listed as a strategy. It is not one. It says nothing about how the old code is changed or replaced; it describes the result. So it is a shape, and a shape has two orthogonal axes.

### Axis 1: modules (vertical boundaries)
A **module** covers one business capability, has an explicit contract (a published API package and/or the events it publishes), keeps everything else private, and owns its data (Grzybek: a module must be independent, have a defined interface, and encapsulate the rest). Simon Brown's version is "package by component": a component's controller, service and repository sit under one top-level package, so deleting the folder deletes the feature.

Modules are deployed one of two ways:
- **`one deployable`**: all modules in one deployment unit. This is a *modular monolith* (Grzybek: a monolith is defined only by having "exactly one deployment unit"). Shopify ran this at scale: ~6,000 classes catalogued into components by business domain, each with a public API, cross-component calls flagged in CI (Wedge, later Packwerk), each component owning its data, and no extra deployment unit.
- **`services`**: each module (or group of modules) deploys on its own. This pays the network tax, so it needs a reason: independent release, scaling or ownership *now*. Fowler's *MonolithFirst* and Shopify both say not to pay it until the boundaries are known.

### Axis 2: inside each module (layering)
- **`hexagonal`**: the domain at the centre, with no imports of framework, database or transport; ports (interfaces the domain owns) and adapters (web, persistence, messaging) at the edge.
- **`as-is`**: the module keeps whatever internal layering it has. Allowed, and honest: it records that layering is not a goal yet.

### Combinations
| Shape | Modules | Inside each |
|---|---|---|
| Modular monolith, hexagonal inside | one deployable | hexagonal |
| Modular monolith, layering untouched | one deployable | as-is |
| Services, hexagonal inside | services | hexagonal |
| Untouched (the leave-it shape) | as-is | as-is |

A modular monolith is also the cheapest *preparation* for services later. Once a module talks only through its API and events and owns its tables, extraction is a move, not a rewrite.

### How the strategy and the shape meet
- **In place** reshapes old code toward the shape.
- **Strangling inside** builds new modules fresh in the shape and retires old paths through the ledger.
- **Strangling beside** and **rewrite** generate the new home in the shape from day one.

In practice an adoption does some of each, and the ledger says which capability went which way.

---

## 2. Recording it: the `Target:` line and the module map

The strategy ADR carries one line:

```
Target: modules in one deployable, hexagonal inside each — module map: docs/architecture/module-map.md
```

or `Target: services, hexagonal inside each — module map: …`, or `Target: as-is (recorded, not pursued)`.

The **module map** assigns every class or package, every table and every database object (view, routine, sequence, trigger) to exactly one module, or to `framework` (composition, web plumbing, cross-cutting concerns; not a module, and it shrinks over time). It also lists allowed dependencies between modules. Illustrative:

```
Modules:
  - orders     — <capability in one line>   owns: <tables, views, DB routines>
  - billing    — <capability in one line>   owns: <tables, views, DB routines>
  - accounts   — <capability in one line>   owns: <tables, views, DB routines>
  - framework  — NOT a module (shrinks over time)
Published contract per module: <module>/api (+ <module>/api/events)
Allowed dependencies: billing -> orders.api, billing -> accounts.api; orders -> (none); accounts -> (none)
Inside each: hexagonal | as-is (per module, if adopted context by context)
```

**The module map is a hypothesis.** It is revised by ADR amendment when discovery or change coupling contradicts it. Record owned tables now, even roughly: data ownership is where modular shapes silently fail.

### Discovering the modules
Use three independent lenses, then reconcile:
- **Event storming** (a person, with an agent as scribe; 2–3 hours for a small app). Lay out domain events on a timeline ("Order placed", "Invoice issued", "Account suspended"). Clusters, language changes and pivotal events suggest contexts. Draw a context map (Vernon): upstream/downstream, shared kernel, anticorruption layer.
- **Static dependency analysis**. Use whatever the ecosystem has: `jdeps` or ArchUnit slices on the JVM, dependency-cruiser or madge for TypeScript, import-linter or pydeps for Python, Packwerk for Ruby. Note who calls the central facade, which data-access code each entry point reaches, and which ORM mappings associate across packages.
- **Change coupling from git history**. Run `git log --numstat` through code-maat's `coupling` analysis (Tornhill). Files that change together across a proposed boundary say the boundary is wrong, or that they share a hidden concept. Files that never change together are safe to separate.

**Reconcile** by writing the table that assigns every class, table and DB routine to one module or to `framework` (Shopify's spreadsheet step). Evidence: `docs/architecture/module-map.md`, the context-map diagram, and the ADR's module map amended to match. Modules drawn without domain knowledge become "package by guess": if nobody can name the capabilities, event-storm first.

---

## 3. Enforcing it

A shape nobody checks decays. These findings hold whatever the strategy.

- **Declare modules with a published `api` package** (`<module>/api`, plus `<module>/api/events`) and a private remainder. Record the modules in project config so the boundary checker applies the context rule.
- **Freeze every existing violation as a ratcheted baseline before the first feature** (Packwerk's `package_todo.yml`, ArchUnit's `FreezingArchRule` store, an import-linter or dependency-cruiser known-violations file). From then on the gate fails on any *new* violation, and the baseline can only shrink. Report its total on every slice. It is a todo list, not a permission slip. A module pair becomes `strict` once its count reaches zero; a new module is born strict.
- **Dependency rules before privacy rules.** Start with who may call whom. Shopify's Packwerk retrospective removed the privacy checks because they turned the tool into "an API design tool", and found "fixes" that silenced a violation by inversion of control and made the code harder to understand.
- **A data-ownership check**, because import scanning cannot see much of the real coupling:
  - framework wiring in XML, YAML or annotations that injects one module's component into another;
  - routing and controller configuration files;
  - ORM mappings with associations across modules (Shopify counted cross-component associations as violations);
  - same-package references, inline fully-qualified names, dynamic loading by string;
  - **raw SQL**: a query in `billing` with `JOIN ORDERS`, or a call to a DB routine another module owns.

  `check-data-ownership` scans SQL strings, ORM mappings and routine names against the module map's owned objects and emits `path:line: billing uses orders table ORDERS`, baselined by the same ratchet. Only the owner's data-access code writes a table. No new cross-module foreign keys.
- **Hexagonal import rules per module** (when `Inside each: hexagonal`): the module's domain imports nothing from its adapters, the framework or the database driver; adapters depend inward on ports. ArchUnit's onion rule, jMolecules annotations, import-linter layer contracts or dependency-cruiser rules express this. Adopt it module by module, each with its own baseline.
- **Events between modules are past-tense facts.** Where A reacts to something in B, B publishes an event and A subscribes; B never calls A. A listener that needs a reply is a disguised RPC; use the API. In one deployable, an in-process publisher is enough; a module framework with durable events (for example Spring Modulith's event publication registry) adds after-commit and async delivery.
- **"The module builds and tests alone"** is a finish-line check. Packwerk found "zero violations" packages that crashed at runtime because wiring hid a dependency. Boot each module's tests with only that module and `framework` loaded.
- **Tool availability follows the platform rungs.** An old language level may support only an import-line scanner; a newer one allows a bytecode- or AST-level checker that catches fully-qualified names, same-package references and inheritance; a newer one still allows a module framework (Spring Modulith's `ApplicationModules.verify()` needs Spring 6 / Java 17). When a stronger checker lands, its first run finds what the weaker one missed; baseline those in an explicit, reviewed commit.

Tool examples by ecosystem: ArchUnit and `jdeps` (JVM), Spring Modulith (Spring), Packwerk (Ruby), import-linter (Python), dependency-cruiser (JavaScript/TypeScript).

---

## 4. How each strategy reaches the shape

### In place
The existing code is reshaped behind characterisation tests at the system boundary (HTTP in, response and DB rows out; no move without a green test covering it). See [in-place.md](in-place.md) for the safety net.
- **Break the god facade by branch by abstraction.** For each facade method, decide its module from the map. Create `<module>/api` with an interface, and an `internal` implementation that first *delegates to the existing facade code*; then move the body across and switch callers one at a time. The facade becomes a delegating shell (frozen: "no new callers") and is deleted when no caller is left.
- **Break the god base class the same way.** Inventory what the shared base controller does (session lookup, auth, flash messages, service accessors, error mapping). Move each concern to the framework's native seam (middleware, filters, interceptors, decorators) and inject collaborators instead of inheriting accessors. Controllers stop extending the base one by one (frozen: "no new subclasses").
- **Move tables to module ownership.** A schema per module where the database supports it, or a prefix convention with views while code moves. Replace each cross-module JOIN with a call to the owner's API or a read model fed from its events. Splitting data is never step 1 (Newman: "far from a simple endeavour").
- **One baseline entry removed per slice** that touches legacy code (the `Leaves better:` field). About one structural card per 1–2 feature slices; platform rungs as their own slices, never in the same slice as a module move. One module per structural slice, `git mv` only, never a big-bang reorganisation.

### Strangler fig, inside
The new home is a set of new modules in the same deployable. They are grown in the target shape from their first line (strict, hexagonal if chosen), and old paths are retired capability by capability through the ledger. The god facade and base class become the in-code routing point. See [strangler-fig.md](strangler-fig.md) for the seam steps.

### Strangler fig, beside, and rewrite
The new home is generated in the shape from day one: modules, published APIs, owned data and (if chosen) hexagonal layering are in the walking skeleton. The old system's shape does not matter beyond the seam; it is retired, not reshaped. The anti-corruption layer is the only place the old system's names appear.

### Leave it
`Target: as-is`, recorded. No shape is pursued; the ADR says so, so nobody mistakes the absence of a shape for an oversight. See [leave-it.md](leave-it.md).

---

## 5. What every spec must state

When the ADR has a `Target:` other than `as-is`, `/draft` ends every spec with `## Strategy fit` holding these
fields beside the strategy's own:

| Field | Meaning |
|---|---|
| `Module:` | existing `<name>` or new `<name>` |
| `Publishes:` | API types and events this slice adds to the module's contract |
| `Consumes:` | only other modules' `api` / `api/events` |
| `Owns data:` | the tables or stores this slice creates or takes ownership of |

The drafter fills them from the module map. `/sail`'s plan stage holds each slice to them. In an adopted repo,
`check-imports` runs in `make verify` through the ratchet, so existing violations are a baseline and new ones
fail; with `"layout": "modular"` on an adopted application, only its context-boundary rule applies. Under a
strangler fig `inside`, the gate fails a spec before `docs/module-map.md` exists.

**Not built yet:**
- A `Leaves better:` field (which baseline entries a slice removes in the modules it touched).
- A spec lint that fails a spec without `Module:`.
- Per-module "strict" (no baseline) registration for a new module, and privacy rules.
- `check-data-ownership`: a data-ownership check over SQL, ORM and stored procedures.
- Validation of the module map.
- The per-checker baseline delta printed in the PR description, and baseline burn-down tracking on the board.
- A nightly change-coupling report, and the QUESTION it would post when coupling passes a threshold or a baseline
  stays flat.

---

## 6. Anti-patterns and how they are detected

| Anti-pattern | Symptom | Detection |
|---|---|---|
| **Big-bang reorganisation** | Lost history, untestable diff; Shopify's single PR lost git history | One module per structural slice; diff size budget; `git mv` only |
| **Package by layer, renamed** (`orders/dao`, `orders/web`, data access still shared) | Checker green, coupling unchanged | Data-ownership check; change-coupling report |
| **Baseline as a permission slip** | Count flat or rising | Ratchet never grows; burn-down on the board; `Leaves better:` required |
| **Indirection to silence the checker** (interfaces in `framework`, reflection, a "shared" module everyone uses) | Violations fall, readability falls; `framework`/`common` grows | Size budget on `framework`; `framework` may not import any module; review question "developer-level or graph-level violation?" (Packwerk) |
| **Shared entities across modules** | Cross-module joins through the ORM | Data-ownership check scans mappings; no field of another module's entity type |
| **Cross-module JOIN or DB routine** | Invisible to import checks | `check-data-ownership` over SQL strings and routine bodies |
| **Events as RPC** | Hidden synchronous coupling, ordering bugs | Listeners return nothing; event names past tense |
| **Cycles between modules** | A depends on B depends on A | Cycle check in the boundary checker |
| **Checker green, module not runnable alone** | Runtime wiring hides the dependency | Per-module test run with only that module loaded |
| **Premature services** ("let's make billing a service") | Network, dual-write, ops for a one-person team | `Target:` changes need an ADR amendment with a reason |
| **Boundaries drawn from nouns, not behaviour** | Every feature touches 3+ modules | Change-coupling report; `/wdyt` on a spec with more than two `Consumes:` |
| **Hexagonal in name only** | `domain/` imports the ORM or the web framework | Per-module layer rule, ratcheted |

---

## 7. Worked example: an internal booking app

The app is invented and stands for any brownfield web app of this shape.

**Starting point:** an internal web app for booking rooms and equipment. One deployable on an old but runnable platform, one relational database. Code loosely grouped into `bookings`, `resources` and `accounts`, plus `framework`. One god service facade every screen calls; every controller extends one base controller. Data access mixes ORM mappings and raw SQL, some joining across all three areas. No tests. The safety-net steps (secrets, build floor, smoke, characterisation) come from the strategy's own playbook and are assumed done.

**First feature:** a "your upcoming bookings" reminders panel on the dashboard.

1. **Discover.** Event storming gives BookingMade, BookingCancelled, ResourceAdded, ResourceRetired, AccountCreated. Static analysis shows `bookings` reaching into `resources` data access through the facade. Change coupling shows the dashboard controller and the bookings queries changing together most of the time. Every class, table and DB routine is assigned in `module-map.md`.
2. **Decide the shape.** One person, one database that must stay consistent, no scaling pressure: services would be premature. The ADR records
   `Target: modules in one deployable, hexagonal inside each — module map: docs/architecture/module-map.md`, with hexagonal adopted per module as each is touched (existing modules start `as-is` inside).
3. **Declare and freeze.** `bookings`, `resources`, `accounts` and (new) `reminders` are declared with empty `api` packages. The boundary checker runs once and its violations become the baseline; `check-data-ownership` is written and baselined too. Frozen: "no new callers of the facade", "no new subclass of the base controller". `reminders` is strict.
4. **The first feature, as the first new module.**

   | Field | Value |
   |---|---|
   | `Module:` | new `reminders` |
   | `Publishes:` | `reminders/api` with `upcomingFor(userId, days)` returning immutable reminder values |
   | `Consumes:` | `bookings/api` (its first published interface), `accounts/api` current-user lookup (new) |
   | `Owns data:` | none in this slice; a projection table is deferred until performance needs it |
   | `Leaves better:` | carves `bookings/api`; moves one existing dashboard query behind it, removing at least one baseline entry |

   *Shape inside `reminders`:* the domain (what counts as "upcoming") is pure code with the codebase's first unit tests; a port `UpcomingBookings` is implemented by an adapter over `bookings/api`; the web adapter renders the panel. The layer rule for `reminders` is strict from the first commit.

   *How it got there depends on the strategy:* in place, `bookings/api` delegates to the existing queries by branch by abstraction and the dashboard sprouts one call into `reminders`; strangling inside, the dashboard's routing point picks the new module's panel behind a flag and a ledger row tracks the old query's retirement; beside, the new home is generated with the same modules and the panel reaches the old dashboard through the seam.

   *Evidence:* characterisation green, the dashboard snapshot changed only in the new panel region; `reminders` has no baseline entries; the PR prints the baseline delta per checker.
5. **Next.** "Detach base class: bookings" and "Decompose facade: bookings" ride as `Leaves better:` items on the next two specs. `accounts` moves its tables into its own schema and replaces its one cross-module JOIN with a call to `bookings/api`. `BookingMade` becomes an in-process event that `reminders` subscribes to when it needs its own projection. A platform rung later enables a stronger checker; its extra findings are baselined in a reviewed commit.

**Finish line for the shape:** every baseline zero and every module strict; the god facade and base class deleted; no SQL names another module's table; each module's tests run with only that module loaded; module documentation (a C4 component view or a module framework's generated docs) matches the code; hexagonal layering present in each module the ADR named.

---

## 8. Sources

- Kamil Grzybek, *Modular Monolith: A Primer*: https://www.kamilgrzybek.com/blog/posts/modular-monolith-primer. Series and sample: https://github.com/kgrzybek/modular-monolith-with-ddd. InfoQ summary: https://www.infoq.com/news/2020/01/monolith-architectural-drivers/
- Simon Brown, *Modular Monoliths* (GOTO Berlin 2018 slides): https://files.gotocon.com/uploads/slides/conference_12/515/original/gotoberlin2018-modular-monoliths.pdf. Package by component / architecture vs code: https://herbertograca.com/2015/11/10/software-architecture-vs-code-by-simon-brown/
- Shopify, *Deconstructing the Monolith*: https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity
- Shopify, *A Packwerk Retrospective*: https://shopify.engineering/a-packwerk-retrospective
- Packwerk usage (todo files, strict mode): https://raw.githubusercontent.com/Shopify/packwerk/main/USAGE.md. Gusto's packs rollout: https://engineering.gusto.com/a-how-to-guide-to-ruby-packs-gustos-gem-ecosystem-for-modularizing-ruby-applications/
- Spring Modulith: https://spring.io/blog/2022/10/21/introducing-spring-modulith · reference https://docs.spring.io/spring-modulith/reference/ · launch baseline (Spring 6 / Java 17): https://www.infoq.com/news/2022/11/spring-modulith-launch/ · ADR example of event-only inter-module communication: https://sprintstart.readthedocs.io/en/latest/explanations/adrs/adr-007-sprintstart-backend-event-based-communication.html
- ArchUnit user guide (FreezingArchRule, slices, onion, PlantUML): https://www.archunit.org/userguide/html/000_Index.html · Flink's frozen architecture tests: https://apache.googlesource.com/flink/+/refs/heads/master/flink-architecture-tests/
- jMolecules (architecture/DDD annotations with ArchUnit rules): https://github.com/xmolecules/jmolecules
- import-linter (Python): https://import-linter.readthedocs.io/ · dependency-cruiser (JavaScript/TypeScript): https://github.com/sverweij/dependency-cruiser
- Alistair Cockburn, *Hexagonal Architecture* (ports and adapters): https://alistair.cockburn.us/hexagonal-architecture/
- Michael Feathers, *Working Effectively with Legacy Code* (seams, characterisation tests, sprout/wrap): https://www.oreilly.com/library/view/working-effectively-with/0131177052/
- Martin Fowler, *Branch By Abstraction*: https://martinfowler.com/bliki/BranchByAbstraction.html · *MonolithFirst*: https://martinfowler.com/bliki/MonolithFirst.html · *Strangler Fig*: https://martinfowler.com/bliki/StranglerFigApplication.html
- Sam Newman, *Monolith to Microservices*, ch. 4 "Decomposing the Database": https://www.oreilly.com/library/view/monolith-to-microservices/9781492047834/ch04.html · decomposition patterns talk: https://gotopia.tech/sessions/1127/monolith-decomposition-patterns
- Schema-per-module vs database-per-module: https://milanjovanovic.tech/blog/schema-per-module-vs-database-per-module
- Adam Tornhill, change coupling: https://adamtornhill.com/articles/aspnetclones/killtheclones.html · code-maat: https://github.com/adamtornhill/code-maat · InfoQ: https://www.infoq.com/news/2017/04/tornhill-prioritise-tech-debt
- Alberto Brandolini, Event Storming: https://www.eventstorming.com/ · Vaughn Vernon, *Implementing Domain-Driven Design* (context mapping): https://www.oreilly.com/library/view/implementing-domain-driven-design/9780133039900/
- OpenRewrite migration recipes: https://docs.openrewrite.org/recipes/java/migrate

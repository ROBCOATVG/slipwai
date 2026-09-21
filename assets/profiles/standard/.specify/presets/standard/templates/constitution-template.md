# [PROJECT_NAME] Constitution

[ONE_PARAGRAPH: what this system does, who it serves, and what breaks if it is wrong. Be concrete —
"moves other people's money", "controls physical access", "records clinical decisions". The rest of this
document exists to protect whatever you write here.]

The numbering below is for reference, not priority.

Continuous delivery is how the rest of this document is enforced rather than merely asserted. Two
questions govern every decision below: **why can we not deliver today's work to production today**, and
**what would let us sleep tonight if we did**. Holding both at once is what makes them useful — optimising
either alone produces a system that is fast and unsafe, or safe and irrelevant. Where a CD practice makes
a problem visible, the practice is the diagnostic and the problem was already there; the obligation is to
fix what it found, never to loosen the gate that found it.

The delivery principles below follow [MinimumCD](https://minimumcd.org/minimumcd/) (CC BY-SA 4.0), the
industry-agreed floor for calling a practice continuous delivery, restated for this domain and extended
with the clause on agent-generated change. Rephrase them freely — `make check-constitution` reads for the
obligation, not for this wording — but a principle deleted here is a gate that silently stopped existing.

## Core Principles

### I. [DOMAIN_CORRECTNESS_PRINCIPLE] (NON-NEGOTIABLE)

[Replace with the one invariant your domain cannot violate, expressed as testable rules. Examples by
domain: no unit of finite inventory held twice; no clinical record attributed to the wrong patient; no
message delivered twice to a payment processor.]

Where the domain involves money:

- Monetary amounts MUST be integer minor units with an explicit currency code. Floating-point types
  MUST NOT appear in any price, fee, tax, or balance.
- A balance MUST be derived from the recorded transactions rather than maintained as a mutable total
  that anything else is allowed to write.
- Corrections MUST be issued as new compensating records. A recorded financial fact MUST NOT be edited
  in place or deleted.

Rationale: [why this specific failure is unrecoverable rather than merely embarrassing].

### II. Idempotency and Retry Safety (NON-NEGOTIABLE)

- Public write endpoints MUST accept a caller-supplied idempotency key and MUST return the original
  result for a repeated key rather than performing the work again.
- Inbound webhooks and queue consumers MUST be treated as at-least-once and MUST deduplicate on the
  provider's message identifier.
- A concurrent write MUST be resolved by an explicit concurrency control — a compare-and-set on a
  version the reader observed, or an equivalent — never by last-write-wins arriving by default.
- A retry MUST NOT be able to duplicate a side effect. A test proving this MUST accompany each new write
  path.

Rationale: at-least-once delivery includes "more than once" and "zero times". Idempotency is the only
defence that survives contact with production, and every retry this document asks for — in the pipeline,
in an adapter, in a rollback — assumes it holds.

### III. Simplicity, and the Rung You Are On

- The smallest design satisfying the specification wins. An additional service, cache, queue, broker, or
  abstraction layer MUST be justified in the plan against a named requirement, not against a shape the
  team is used to.
- **How much of the past this system keeps is a plan-time decision, recorded with its reason.** The rungs
  run from a function that returns its outcome, through in-process notifications, through an outbox, to a
  durable log of everything that happened. Each rung buys auditability and costs operational surface.
- A context MUST NOT be moved up a rung merely for consistency with a neighbouring context. Where history
  is genuinely part of the domain, say so and pay for it; where it is not, a boring table is the correct
  answer and MUST NOT be apologised for.
- Moving *down* a rung is the harder direction, so the rung is recorded as an ADR under the reversal-cost
  test in the workflow section below.

Rationale: complexity added for symmetry is the cheapest kind to add and the most expensive kind to
remove, because nothing ever demands its removal. Naming the rung makes the choice visible while it is
still a choice.

### IV. Hexagonal Architecture — Domain Isolated from Infrastructure

- Domain code MUST NOT import a framework, transport, persistence implementation, clock, UUID generator,
  vendor SDK, or UI concern. Time and identifiers arrive as typed inputs.
- **Driving adapters** parse untrusted input into typed commands and call use cases. They hold no
  business rules and make no authorisation decision.
- **Driven adapters** implement ports owned by their innermost consumer, injected as parameters.
- Persistence is a driven port, not an ambient dependency.
- Ports MUST be named for the business conversation, never the technology, and MUST survive an adapter
  swap. No `I` prefix, no `Interface`/`Port`/`Impl` suffix, no vendor name in the port.
- Ports MUST be role interfaces exposing only what the consumer needs.
- **Every driven port MUST have a usable fake**, so domain and application layers are testable with no
  infrastructure running. A fake that cannot simulate its port's failure modes leaves those failures
  untested.
- The dependency direction MUST be enforced by an automated check — in this project `make check-imports`
  — not by reviewer vigilance.

### V. Acceptance-Driven Development from Given-When-Then

- **Level.** Every slice MUST have at least one GWT scenario whose **When** enters through the
  application's own driving port — **the use case** — and whose **Then** is observable there. A scenario
  satisfiable by calling an internal function is a unit specification, NOT a slice acceptance criterion.
- **Why the use case and not the delivery adapter.** The use case is the whole path a slice has to get
  right: authorise, load, decide, persist, report the outcome. Binding acceptance scenarios to an adapter
  couples every one of them to the thing IV exists to make replaceable, and a project built with no HTTP
  adapter has no such boundary to bind to at all.
- **The outside surface still has to be tested, and it has its own level.** A delivery adapter — HTTP
  route, CLI command, queue consumer — MUST carry a test covering parse, delegate, and the mapping of
  every outcome to a response. It lives in `tests/edge/` and MUST NOT be the level at which a business
  rule is proved.
- **Adversarial testing enters from outside, and this principle does not constrain it.** An attacker
  stands at the external surface, so that is where the red-team pass reproduces (this principle's evidence
  gate, and the `adversarial-testing` skill). Where the rule was right and the *route* got past it, the
  regression test belongs at the edge: a use-case test proves the rule holds and proves nothing about
  whether the surface can be made to skip it.
- **What is NOT a GWT scenario**: format and structure validation. That belongs in the type system,
  which MUST make invalid states unrepresentable. If the compiler can reject it, do not write a scenario.
- **Cycle**: RED-GREEN-REFACTOR. Tests written after the code they cover MUST be sent back.
- **One increment at a time (NON-NEGOTIABLE).** The unit of an increment is **one rule** —
  one numbered rule of the slice's example map, or one acceptance criterion where there is no map,
  with the examples that belong to it — taken RED-GREEN-REFACTOR: its examples
  failing, the smallest code that passes them, refactor on green. Within a rule the examples MAY be written
  together and implemented against, or taken one at a time, as the implementer judges; an increment MUST
  NOT span rules, and the next rule's examples MUST NOT be written until the current rule is green and
  refactored. **Writing a slice's scenarios up front as a batch and then implementing against them is
  prohibited**, however carefully those scenarios were specified — it is a planning artifact executed as
  code, not a test-driven cycle. A task that produces no behaviour — a proof over what an earlier increment
  already built — is a rule cut too small, and belongs inside the increment that produces the behaviour it
  guards.
- At most **one rule's** examples may be failing at a time. Each cycle MUST leave the quickest relevant
  tests in its file or area green. Commit each completed cycle locally; do not push those commits until the
  actor has accepted the demo. The whole suite MUST be green immediately before that first implementation push,
  which is what may land on trunk. A row of pending tests is not RED; it is an unintegrated batch of
  the kind IX exists to prevent.
- **RED is a failing assertion, not a failing build.** Whatever an example names — function, method, type,
  field — MUST exist far enough to compile against before that example is written, as a no-op or a default
  return; that fixes the shape while saying nothing about the behaviour. A red build is not a red test, and
  "it does not compile yet" is never the stated reason a test fails.
- Every example MUST be observed failing, **and failing for its own stated reason, distinct from its
  siblings'**, before the code that satisfies it is written. Examples that all fail for one shared cause
  have been observed once rather than once each, and every one beyond the first is unproven. A test that
  passes the moment it is written is evidence of nothing until it has been observed failing: where the
  behaviour already exists, that observation is the behaviour changed and restored, and the report says so.
- REFACTOR is a step, not an option. It happens on green, before the next test, and it MUST NOT change
  observable behaviour.

Rationale for the increment rule: writing every scenario first looks like rigour and removes the thing
that makes TDD work. Each test is supposed to be a design experiment whose result changes what you write
next; a batch fixes the design before the first result arrives. It also destroys the attribution that
makes a failure cheap — with one rule red you know exactly which change broke it, and with nine rules you
are debugging. The rules discovered during specification are the *list* of increments to drive, their examples
the tests inside each — not a body of code to author in one sitting. The rule is the unit because it is the
smallest thing the example map agrees on: cut finer, the offcuts are tasks that prove what an earlier task
built and produce nothing, and each is a red test that cannot be made red.

- **Behaviour, not structure.** Tests MUST NOT assert private functions, internal call ordering, or mock
  invocation counts where an observable outcome exists. Renaming an internal function MUST NOT break a
  test.
- **One capability per slice, one observable outcome per criterion.** A slice or criterion joining two
  capabilities — with "and", a comma between verbs, or "plus" — MUST be split before it is planned. The
  word "and" in a deliverable's title is a split signal, not a description. Acceptance scenarios MUST be
  checked for capability clusters: more than one cluster means the title under-reports what the slice
  contains. A walking skeleton MAY span layers but MUST NOT span capabilities unless each additional one
  introduces a **new architectural shape**.
- **Evidence gate.** At the end-of-phase point, test effectiveness MUST be evidenced by mutation testing
  where meaningful, otherwise by recorded reachability, contract, or operational evidence with mutation
  marked N/A. A failing test MUST NOT be manufactured to make a behaviour-preserving change look RED.
- Bug fixes MUST begin with a boundary-level scenario reproducing the reported behaviour.
- Coverage percentage is not a gate.

### VI. Contract-Bounded Integrations

- Third-party systems MUST be reached only through a driven port this codebase owns.
- Provider SDK types and vocabulary MUST NOT leak past the adapter boundary.
- External data MUST be translated into this system's own vocabulary at an anti-corruption boundary.
- **Every driven adapter to a third-party system MUST have integration tests against a stub of that
  provider, pinned to a recorded or published contract.** What they cover is the adapter's own work:
  request translation, response translation, status-to-domain-error mapping, retry, and timeout.
- **The provider failure modes the adapter maps MUST be enumerated, and each one MUST have a test** —
  at minimum the 4xx a caller can fix, credential rejection, rate limiting with its retry hint, 5xx, a
  timeout, and a response the contract does not allow. A failure mode with no test is a code path that
  first runs during an incident.
- A retry MUST NOT be able to duplicate a non-idempotent effect. Where the provider offers an
  idempotency mechanism, the adapter MUST use it and a test MUST prove the key reaches the provider.
  This is II applied at the far side of the boundary rather than the near side.
- **A stub is not a fake and is not held honest the same way.** A fake implements a port this codebase
  owns and is validated by that port's contract suite. A stub impersonates a system nobody here owns, so
  what validates it is the contract its responses are pinned to, plus a recording refreshed against the
  live provider **outside the merge gate** — the obligation XII already places on every test double.
- **Automated test runs MUST NOT call live third-party endpoints**, which is a consequence of the above
  rather than a separate discipline: an adapter reached through a stub has nowhere to call. A test that
  needs a live endpoint to pass is reporting a missing stub, not a network policy.

### VII. Observability and Auditability

- Logs MUST be structured and carry a correlation identifier propagated across every hop, projection,
  and background job.
- Every recorded fact MUST carry the actor that caused it plus causation and correlation identifiers,
  both of them UUIDs, and audit records MUST be queryable without restoring a backup.
- Audit records MUST be retained for [RETENTION_PERIOD].
- **A read model is not detection.** An endpoint is where someone looks once told; an alert is what tells
  them. Where a criterion promises a problem is surfaced within a time bound, the alert satisfies it.
- Background jobs MUST emit a heartbeat, and a missing heartbeat MUST itself be alertable — a silent job
  and a healthy system otherwise look identical.
- Personally identifying data MUST NOT be written to application logs.

### VIII. Versioning and Breaking Changes

- Published artifacts and APIs MUST be versioned MAJOR.MINOR.PATCH.
- A breaking API change MUST ship as a new version and keep the prior version serving for
  [DEPRECATION_WINDOW] after announcement.
- **A persisted schema is a contract with every future version of this system.** Changes MUST be
  additive; readers MUST tolerate unknown fields. Removing or retyping a stored field requires a new
  schema version plus a translation that maps old records forward on read.
- Migrations MUST be backward compatible with the previously deployed application version.
- **If the deployment strategy runs two versions concurrently** (rolling deploy), the previous version
  MUST also tolerate what the new version writes — forward compatibility, which is stricter than the
  tolerant-reader rule above.

### IX. Security, Privacy, and Compliance

- [Sensitive data class, e.g. card numbers, credentials, clinical identifiers] MUST NOT enter, transit,
  or be logged by this system. Capture MUST be delegated so that [COMPLIANCE_SCOPE] stays minimal.
- **Personal data MUST be erasable**, and where a store is append-only or a record is otherwise
  immutable, that mechanism MUST be designed — by reference-not-embed, or crypto-shredding behind a
  per-subject key — **before the first record carrying personal data is persisted**. Immutability and the
  right to erasure only coexist if designed for up front.
- Secrets MUST come from the environment or a secret manager. Committed secrets are a build-breaking
  failure.
- Authorisation MUST be enforced server-side on every request, **inside the application** rather than in
  a driving adapter alone. Cross-tenant access MUST return not-found, not forbidden — existence is not
  leaked.
- Dependencies MUST be scanned in CI; a known-exploitable critical finding blocks release.

### X. Continuous Integration on Trunk (NON-NEGOTIABLE)

- Every engineer MUST integrate to trunk at least once per day. Work that has not reached trunk is
  unintegrated no matter how often the build server ran against the branch it sits on.
- Where branches are used they MUST be cut from trunk, MUST re-integrate to trunk, and MUST live less than
  a day. Long-lived `develop`, `test`, integration, or per-feature branches MUST NOT exist.
- Trunk MUST be releasable at every commit. Automated verification runs before the merge and again on
  trunk after it.
- **A red trunk stops the line.** While the build is failing the only permitted work is restoring it. New
  feature work MUST NOT start on a red build, and a failure MUST NOT be carried into a later change.
- A work item MUST be codeable, testable, reviewable, and integrable within **two days**. An item that is
  not MUST be split before it is started — carrying it is how a two-day item becomes a two-week merge.
- Fixes MUST travel forward through trunk. Cherry-picking a change onto a release branch MUST NOT be the
  route to production.
- **A stack of dependent pull requests is a symptom, not a technique.** Every branch in a stack is waiting
  on the one below it, which means every branch in it is living longer than a day — the thing this
  principle exists to prevent. A stack is evidence of exactly one of two defects: the work was never
  decomposed into independently shippable slices, or review latency grew until building on unmerged work
  looked cheaper than waiting for a merge. **The defect is the finding; the stack is the workaround.**
  Where one is used anyway it MUST name which of the two it is compensating for, MUST be treated as
  temporary, and MUST NOT become how the team normally ships.

Rationale: batch size is the variable every other guarantee here depends on. A large change is not merely
slower to review — it defeats bisection, hides the regression it introduced among unrelated edits, and
makes rollback an all-or-nothing decision. Integration frequency is the cheapest available control on it.

Rationale for treating stacks as a symptom: the technique works, which is the problem. It makes an
undecomposed batch comfortable enough to keep, so the decomposition never happens and the review queue
that caused it never gets fixed. A practice that relieves the pain of a constraint without removing the
constraint will keep the constraint indefinitely.

*Practice: `story-splitting` to find the vertical slice, `planning` to sequence it. Where a slice still
looks too large to review, that is a decomposition result, not a branching problem — go back to
`story-splitting` rather than reaching for `stack-pull-requests`.*

### XI. One Path to Production, and the Pipeline Decides (NON-NEGOTIABLE)

- Exactly **one** automated pipeline MUST deliver every change to every environment. Hotfixes, rollbacks,
  configuration changes, schema migrations, and emergency work use it too. A second route, even one used
  once, invalidates every claim the first route makes.
- **The pipeline is the release authority.** If it passes, the artifact is deployable; if it fails, it is
  not. A human MUST NOT be able to override the verdict, and a passing pipeline MUST NOT require a further
  sign-off to proceed.
- The Definition of Deployable MUST be automated in full and identical for every environment. Adding a
  quality criterion means adding a gate, not adding a sentence to a review checklist. In this project the
  definition is what `make ci` runs.
- **Deterministic**: the same inputs MUST produce the same outputs and the same pass/fail verdict.
  Everything the pipeline consumes MUST be in version control — source, pipeline definition,
  infrastructure, migrations, alert and dashboard definitions, policies, test data, tool and runtime
  versions, and a dependency lockfile. Floating versions (`latest`, open ranges, mutable tags) MUST NOT
  appear anywhere the pipeline reads.
- If a change can be made to a running environment without a commit, that thing is not managed. Bring it
  into the repository or accept that it is undefined.
- Every pipeline step MUST be runnable locally by the same command CI runs. A step only CI can perform is
  a feedback loop an engineer cannot close.
- **Flaky tests are defects, not weather.** A test that passes and fails on the same commit MUST be fixed,
  quarantined, or deleted the day it is noticed. Re-running a build to obtain a pass is prohibited: it
  trains the team to disbelieve the one signal that is supposed to be authoritative.

*Practice: `ci-debugging` when the pipeline is the thing that is broken; `evaluate-existing-solutions`
before a bespoke pipeline mechanism is written.*

### XII. Build Once, Deploy Anywhere; Deploy Is Not Release

- One artifact MUST be built once per commit and promoted unchanged through every environment. Rebuilding
  per environment discards the evidence the pipeline produced and MUST NOT happen.
- Artifact identity MUST be unique and immutable. Snapshot versions and mutable tags MUST NOT be deployed.
- Configuration that varies between environments MUST come from the environment; configuration that does
  not vary MUST ship inside the artifact and be tested with it. The two MUST NOT be conflated — see IX for
  secrets, which are always environment-supplied.
- **Deployment and release are separate decisions.** Incomplete work reaches production dark, behind a
  flag. Holding a deployment back is not a release control; it is an integration debt accruing interest.
- Every release flag MUST be created with an owner and a removal date, MUST have both paths covered by
  tests, and MUST be removed once the rollout completes. A release flag older than [FLAG_MAX_LIFETIME,
  e.g. 90 days] is a defect. Permanent operational switches (kill switches, circuit breakers) are a
  different thing and MUST be named and governed as such.
- **Rollback MUST be a single automated action completing within [ROLLBACK_TARGET, e.g. 5 minutes]**,
  executable by anyone on the team without approval, and exercised on a routine schedule. A rollback path
  first attempted during an incident is a hypothesis, not a capability.
- Schema change MUST follow expand/contract across separate deployments: add, then write, then read, then
  stop using, then remove. An additive and a destructive step MUST NOT ship in the same deployment. This
  is the same forward-compatibility obligation as VIII, applied to storage rather than to a published API.
- A migration MUST be reversible, or MUST be paired with a tested restore path. "Reversible in principle"
  is not reversible; the rollback rehearsal above is what makes the claim true.

*Practice: `twelve-factor` for the config boundary and process model. `make check-migrations` is the gate on the
expand/contract rule: a contracting migration names the expand it completes and lands in a later change.*

### XIII. Fast Feedback, or It Is Not Feedback

- Feedback budgets, each a gate on the suite rather than an aspiration: unit tests in watch **under one
  second**; the pre-push deterministic set **under two minutes**; the full deterministic pre-merge suite
  **under ten minutes**. Exceeding a budget is a defect in the suite — fix the suite. Extending the budget
  or moving tests out of the gate to meet it is prohibited.
- The deterministic suite MUST NOT depend on any system the team does not control: no live third-party
  calls, no shared mutable environment, no ordering between tests, no wall-clock sleeps. This is the same
  obligation as VI, stated as a property of the pipeline rather than of an adapter.
- Test doubles used in the deterministic suite MUST be validated against the real system by contract tests
  that run outside it, on a schedule or on demand. An unvalidated double is a second implementation of a
  system nobody checked.
- **Test changes MUST ship in the same commit as the code they cover.** Tests arriving in a later commit
  are documentation, not a gate.
- Non-deterministic checks — end-to-end smoke, load, resilience, exploratory testing — run after deploy.
  They MUST NOT gate merge, and exploratory testing MUST NOT be a release gate.
- Pre-production environments MUST be created from version control and destroyed after use. A long-lived,
  hand-tuned environment MUST NOT be the reference for "it works" — it is the one machine nothing else
  resembles.
- A production problem MUST be detected by alerting within [DETECTION_TARGET, e.g. 5 minutes], not by a
  customer. See VII: an endpoint is where someone looks once told; an alert is what tells them.

*Practice: `testing` and `tdd` for the suite itself, `test-design-reviewer` when tests assert the wrong
thing, `mutation-testing` at the end-of-phase evidence gate per V, `characterisation-tests` before changing
code that has none, `production-parity-skill-builder` to catch environment drift, `observability` for
detection.*

### XIV. Agent-Generated Change Meets the Same Bar (NON-NEGOTIABLE)

- An agent-generated change MUST clear the same pipeline and the same Definition of Deployable as a
  human-generated one. There MUST NOT be a fast lane for agent output, and there MUST NOT be an extra
  manual gate applied to it because of its origin.
- **Humans own intent.** The specification, the acceptance criteria, the architectural constraints, and
  this constitution are human-authored and human-amended. An agent MUST NOT edit them to make its own
  change pass. Where they conflict with an implementation, they win.
- Every change MUST carry its intent as versioned artifacts delivered in the same commit as the code: the
  problem being solved, the observable behaviour as GWT scenarios, the constraints that bound the
  implementation, and the acceptance criteria the pipeline enforces. These are pipeline inputs, not
  documentation written afterwards.
- **One scenario, one session, one commit.** An agent session MUST be scoped to a single acceptance
  scenario and MUST end at a green commit. While the pipeline is red, the only permitted agent work is
  restoring it — the same stop-the-line rule as X.
- An agent MUST stop and ask when a decision falls outside its constraints — **a name in the domain
  vocabulary, a persisted field, a new dependency, or a change to a published contract**. Guessing to keep
  moving is prohibited: per VIII those decisions are contracts with every future version of this system,
  and an agent that invents one has made a migration nobody scheduled.
- Review of agent-written code MUST examine intent alignment, architectural conformance, and complexity.
  "The tests pass" is the pipeline's finding, not the reviewer's.
- An automated reviewer MUST NOT replace a human check until it has run alongside that check for at least
  [PARALLEL_REVIEW_CYCLES, e.g. 20] changes at an agreed accuracy. Removing the human first produces
  confidence without evidence.

Rationale: an agent cannot silently route around a vague specification, an unreliable suite, or a coupled
architecture the way an experienced engineer does without noticing. Agentic delivery does not create these
weaknesses; it removes the human compensation that was concealing them. Every failure it surfaces is a
failure that was already being paid for somewhere less visible.

*Practice: `specification` and `find-gaps` before an agent implements anything, `acceptance-review` to
judge a change against its criteria rather than against itself, `ubiquitous-language` for the conversation
that agrees a name.*

### XV. Ubiquitous Language and Domain Types

- The vocabulary is agreed with the people who own the domain, and **one term MUST have exactly one meaning**
  inside a bounded context. Where the business renames something, the code is renamed with it — a translation
  layer that exists only in people's heads is a defect, and it is paid for again at every handover.
- Types, functions, modules, tests, and user-facing copy MUST use that vocabulary. A technical synonym for a
  domain term MUST NOT be introduced, and a name that says nothing about the domain — `data`, `info`,
  `manager`, `helper` — MUST NOT survive review.
- Where two contexts genuinely mean different things by one word, the boundary MUST be named and the term
  translated at an adapter. Picking a winner and overloading the word MUST NOT be the resolution.
- Domain concepts MUST be modelled as types rather than primitives: identifiers, quantities, and monetary
  values are branded or wrapped so one cannot be passed where another is required.
- **Constructors MUST make illegal states unrepresentable.** Untrusted input is parsed into a valid domain
  type once, at the boundary; code past that point MUST NOT re-validate the same primitive. A rule validated
  in two places is a rule with two versions, and they will disagree.
- A term nobody can define without reaching for an example is not understood yet. Modelling it further is
  cheaper than encoding the misunderstanding, because per VIII a name that reaches a persisted schema or a
  published API is expensive to take back.

Rationale: every other principle here is written in domain words — an invariant, a published field, a
consistency boundary. Those words end up in stored data and in contracts other people depend on, so
vocabulary drift does not produce a naming inconsistency, it produces a migration.

*Practice: `ubiquitous-language` to agree the terms with the domain expert, `domain-driven-design` for the
modelling, `functional` for the types that hold the result.*

## Additional Constraints

- All timestamps MUST be stored in UTC. Where a time has local meaning to a user, the IANA timezone MUST
  be retained as a **domain field**, not treated as a formatting concern.
- Domain time (`occurredAt`, injected) MUST be stored separately from storage time (`recordedAt`).
  Conflating them makes clock problems unreconcilable.
- Persisted data MUST record facts true on any machine. Runtime context — file paths, hostnames, process
  ids, working directories — MUST NOT appear in it.
- Simplicity governs, per III: the smallest design satisfying the spec wins, and not every interface is a
  port.

### Technology Stack

- [LANGUAGE_AND_RUNTIME], pinned in the repository and identical across local, CI, and production. A pin
  nobody can satisfy is worse than no pin — pin what the environments actually run, and change it by
  upgrading environments rather than editing the pin.
- Strict type checking MUST be enabled at its maximum practical setting from the first commit.
  Retrofitting strictness is expensive; enabling it on an empty codebase is free.
- Escape hatches (`any` and equivalents) MUST NOT appear in domain or application code. Untyped external
  data enters as `unknown` and is narrowed by a runtime schema.
- **Schema-first at trust boundaries.** Every crossing MUST be validated by a runtime schema: inbound
  requests, third-party responses, and **anything read back out of storage** — because stored data
  outlives the code that wrote it.
- Identifiers and monetary values MUST use branded types, so one identifier cannot be passed where
  another is required.
- **The persistence product is a plan-time decision, not fixed here.** Whatever backs it, the port MUST
  express the concurrency control II requires and MUST be exercised by the same contract suite as its
  fake. A product that cannot offer both MUST NOT be adopted.

## Development Workflow and Quality Gates

- Every plan MUST include a Constitution Check naming which principles the feature touches, which rung it
  sits on per III, and how it complies.
- Every pull request MUST pass: automated tests including at least one boundary-level scenario per slice,
  linting, dependency vulnerability scan, the domain→infrastructure import check, and review by an
  engineer who did not write the change.
- A pull request MUST NOT be merged while the pipeline is red, and MUST NOT be merged by disabling a gate.
- **Review is a flow constraint, not a queue.** A change MUST be reviewed within [REVIEW_SLA, e.g. two
  working hours]; a pull request waiting longer than a working day MUST be escalated rather than
  tolerated. Pair or ensemble programming satisfies the review obligation without a separate step.
- A pull request SHOULD change fewer than 200 lines. Beyond roughly that size reviewer defect detection
  falls off sharply, so a large diff does not buy more scrutiny — it buys less, more slowly.
- Formatting and style MUST be enforced by tooling. A review comment about style is a missing lint rule.
- Any change touching [HIGH_RISK_AREAS, e.g. money, inventory, authentication, tenancy] MUST be
  reviewed by a second engineer.
- Deviations from a principle MUST be recorded in the pull request under a "Complexity / Deviation"
  heading, naming the principle and the reason. Silent deviation is a defect.
- Where a slice is delivered with stubs, the stubs and their consequences MUST be recorded explicitly.
  Stubs belong at the edges — anything expensive to retrofit MUST be real from the start.
- **A decision that would cost a migration to reverse MUST be recorded as an ADR** in `docs/adr/`, using
  Nygard's five sections (Title, Status, Context, Decision, Consequences). The test is reversal cost, not
  importance: stored data must change shape, another team or customer must coordinate, a contract must be
  versioned, or history would have to be rewritten. The rung chosen under III always qualifies. So do the
  tenancy model, the personal-data classification and its erasure mechanism, the identity and
  authorisation model, the persistence product, a new runtime dependency, and any published contract.
  **An accepted ADR MUST NOT be edited**; a decision is changed by a new ADR that supersedes it, with links
  resolving in both directions. An ADR drafted by an agent MUST start at `Proposed` — accepting an
  architecture decision is a human act.
  A slice-scoped design decision stays in that slice's `research.md`; when one turns out to outlive its
  slice, it MUST be promoted to an ADR. Recording something reversible as an ADR costs a page nobody needed;
  failing to record something permanent loses the reasoning entirely, so the bias is deliberately towards
  writing one.

## Governance

This constitution supersedes other development practices in this project. Where a style guide, template,
skill, or prior decision conflicts with it, this document wins.

**Amendment procedure.** Amendments MUST be proposed as a pull request modifying this file, MUST state
the rationale and the version bump with its justification, and MUST be approved by the maintainers.
Amendments invalidating existing code MUST include a migration plan.

**Versioning policy.** MAJOR — a principle removed or redefined such that compliant work would now
violate it. MINOR — a principle or section added, or guidance materially expanded. PATCH —
clarification changing no obligation.

**Compliance review.** Every review MUST verify compliance with the principles the change touches.
Maintainers MUST review this constitution against actual practice at least quarterly; a principle
routinely ignored MUST be enforced or amended away, never left as decoration.

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]

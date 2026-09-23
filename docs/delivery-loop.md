# The delivery loop

Spec Kit supplies the phases — constitution, specify, plan, tasks, implement, converge. What a generated
project adds is the **method around them**, and one command that drives it.

- [The loop](#the-loop)
- [`/drive`: the ladder](#drive-the-ladder)
- [Cruise: the driver as owner](#cruise-the-driver-as-owner)
- [The commands](#the-commands)
- [Story splitting](#story-splitting)
- [Example mapping](#example-mapping)
- [Spec Kit's own phases are hooked from both sides](#spec-kits-own-phases-are-hooked-from-both-sides)
- [Spec Kit is never edited in place](#spec-kit-is-never-edited-in-place)
- [The constitution is gated from both sides](#the-constitution-is-gated-from-both-sides)

## The loop

![The delivery loop at a glance: run once — principles, specify, gaps, model the events, split into slices — then once per slice: example map, gaps, plan, tasks, implement, converge, gaps, demo, adversary, mutation, next slice](images/delivery-loop.svg)

Solid edges are the path forward; dashed edges are feedback. Every event-profile project ships this loop
as its own `docs/workflow.md`, drawn for the profile it was generated with and carrying the full detail
the picture leaves out: the command behind each stage, and every feedback edge — which stage a gap, an
unnameable event, or a demo's verdict sends you back to.

A `standard` project gets the same loop with the event-modeling and example-map stages removed: the
slice enters the loop at its own `/gaps` pass over the acceptance criteria instead.

Three stages in it are deliberately not the shape they look like:

- **Converge is append-only.** Its only write is new tasks, so repeating it costs a read and is always safe.
  Loop it until it reports converged — or until the bound the ladder sets, two passes by default, after which
  what is still open is appended as Phase 4 tasks: a loop whose exit condition is the judgement of the thing
  being looped has no other end. An open `CRITICAL` finding is the one thing the bound does not hold
  against; it re-opens the loop however many passes have run.
- **The second `/gaps` runs after the converged verdict, not before it.** Ahead of converge, every unbuilt
  task reads as a gap and buries the findings that actually need judgement.
- **`/adversary` is an end-of-phase pass, not a per-slice one.** It runs when the diff changed attack
  surface, and at the close of the split regardless, recording the decision either way in
  `specs/<feature>/adversary-log.md` — which is what lets a later slice decline on evidence rather than on
  judgement. The trigger table is in that row before any spawn: skip unless a surface was `widened`, or
  the slice closed the split, or `--full`. `/mutation` runs on every accepted slice; where both run,
  adversary goes first, since it adds tests and mutation measures whatever exists when it runs.

## `/drive`: the ladder

`/drive` reads artifacts from disk rather than conversation memory, and enters at the first stage whose
artifact is missing, empty, or still a placeholder. That is what makes it resumable, and what makes "invoked
too early" a valid start rather than an error: it steps back to the stage that is actually incomplete, states
the evidence that selected it, and runs from there.

| # | Stage | Satisfied by |
|---|---|---|
| 1 | **Principles** | A ratified `.specify/memory/constitution.md`, `make check-constitution` green — otherwise `/speckit-constitution`, then `/constitution-coverage` |
| 2 | **Product specification** | `specs/<feature>/spec.md` — otherwise `/speckit-specify`, then `/gaps` |
| 3 | **Event model** *(event profile)* | `docs/event-model/model.yaml` naming the commands, events, read models and actors — the slice also names its service and bounded context |
| 4 | **Split** | Ordered vertical slices — otherwise `/story-splitting` |
| 5 | **Example map** *(event profile)* | `specs/<feature>/slices/<id>/examples.md` — otherwise `/example-map` |
| 6 | **Slice gaps** | A recorded gaps review — otherwise `/gaps`. A missing state is a paper edit here and a rewritten test later |
| 7 | **Release constraint** *(production target)* | The flag that holds this slice back from the actor, named in the plan: the key of the releasable capability the slice belongs to, declared in `infra/service/flags.auto.tfvars` seeded `off`. One flag covers a capability, not a slice — the stage says to recommend which, and to ask only where it is genuinely a product question |
| 8 | **Plan and tasks** | `plan.md` and `tasks.md`, whose *Structure Decision* names the owning service and bounded context |
| 9 | **Implementation** | Spec Kit's implement command, one RED-GREEN-REFACTOR increment per task — one rule of the example map with its examples — starting from a green `make verify` |
| 10 | **Convergence** | A converged verdict for the current commit, then `/gaps` over the slice diff |
| 11 | **Demo** | The actor-visible path, ready to show — a stop for feedback, not a report. It opens with a progress board in the actor's words (✅ works now · 🆕 new in this demo · ⬜ still to come, `N of M slices accepted` · ⚠️ not working yet · 🔀 ready (parallel) · ➡️ next (this session) · ⛔ blocked) and ends with the command to paste and a question only the actor can answer. Slices are counted, tasks are not: a slice is a thing the actor can use. `/where-are-we` draws the same board on demand between demos |

It never invents a principle, event, or slice to skip a stage: a missing artifact is work to do with the
user, and a stage needing a real product decision is a stop.

In a repository that adopted the method around existing code ([Adopt an existing repository](adopting.md)), the
same ladder has three more things in it, as stages so that the entry rule reaches them: **Ground** before
Principles — the convergence map exists and is green, and an `unrecorded` row on an axis the slice touches is a
question before anything else; **Pin** before Implementation — wrapped code is changed only once `/characterise`
has recorded what it does at the seam; and **Convergence** re-checks the map after the slice, flips the row a rung
was reached on, and offers the next unplanned row as a *method slice* for the split.

Stages 3 and 8 are also where a project's **bounded contexts** get decided, because that is where the
question actually arrives — which service owns this slice, and which context inside it. Neither is defaulted
to the first entry in the list; a slice no service's recorded purpose covers is a product decision to ask
about. See [Services](services.md).

### Who runs each stage

Every stage used to run on whatever model the harness was set to, at one price for gauging whether a slice
converged as for turning `examples.md` into tests. A generated project carries the choice in
`.specify/models.json`, versioned with it: a role per stage, keyed by the command the stage runs — `strong`
where a stage decides what to build or whether it was built (principles, specify, the event model, the split,
the example map, both `/gaps` passes, the plan, converge's verdict, the demo stop, adversary), `fast` where the
input is already fully specified on paper (tasks, implement, mutation) — and, per harness, what each role maps
to. Roles rather than model names, because identifiers are provider-specific and go stale; `host` means the
model running `/drive` itself, and `strong` maps to it everywhere.

Whether a harness can act on the table at all is the registry's business (the same file records under
`headless` how each harness runs one prompt and exits, which is what `/cruise`'s runner drives, and under
`hooks` whether it can refuse the end of a turn; [Cruise](cruise.md) says how both are used). `scripts/agents/registry.json`
records under `subagentModel` how each harness lets a sub-task run on a chosen model — read from that
harness's own documentation on the date the row names, for Claude Code, Codex CLI, Gemini CLI, Cursor, GitHub
Copilot and opencode — or `null` where none was verified. `python3 scripts/agents/models.py <stage>` resolves
the two into the one line `/drive` reads before a stage: the model to delegate to and the mechanism, or why the
stage runs on the host model — the role maps to `host`, no identifier is mapped for this harness, or the
registry records no way to switch. `/drive` delegates when the line names another model and runs the stage
itself otherwise, and in both cases says which model ran the stage.

Each stage the ladder sends to a fresh context is a **named agent type** the project carries in `agents/`:
`drive-tasks`, `drive-implement`, `drive-converge`, `drive-gaps`, `drive-adversary`, `drive-mutation`, with `drive-slice` for
the whole-slice delegate the concurrent fan-out spawns, and `drive-skipper`, `drive-hand` and `drive-bosun` for the
product owner, the actor and the unblocker that `/cruise` puts in a person's place — the first and last on a
`skipper` role of its own, so a project can run a bigger model on deciding than on driving. The type declares what
its delegate may write and what it may run, in words no harness owns, and carries that stage's standing brief
so a per-call brief adds only the task, its contract and the file manifest. `make agents` renders each into
the installed harness's own agent file with the model the table resolved, and with as much of the scope as
that harness can express — Codex's sandbox mode, Cursor's `readonly`, Copilot's and Gemini's tool lists,
opencode's permissions, Claude Code's `disallowedTools`. Read-only was a sentence in a brief until this, which
is the anti-pattern the adversarial-testing skill lists first; it is now a file the harness reads, and where
the harness cannot hold part of it — the shell is one tool on four of the six, and an adversary has to run a
reproduction — the projection's stamp says so rather than leaving the gap to be assumed away, as the
project's own `docs/agent-harnesses.md` explains. Because five of the six harnesses name a sub-task's model
only in that file, `/model-delegation-settings` rewrites the types as part of the change. `make models` prints the whole table, and
`make check-agents` refuses a malformed edit. Nothing about what a stage produces changes with who runs it.
Nor is a delegated stage always one delegate: `tasks.md`'s `[P]` markers and its parallel-opportunities section
are the tasks command's plan for what may run alongside what, and `/drive` reads them before delegating
implementation — independent tasks go out as concurrent siblings, none of which writes `tasks.md`, so the host
ticks the checkboxes.

Nor is a session one slice at a time. Slices that share only an event schema are independent, and once the
contract is settled — every ready slice `planned`, its events' attributes, guard and example map written —
one `/drive` session runs every unclaimed ready slice at once, the way Nebulit's build kits and Dilger's Ralph
loop do: a claim, which is a `slice/<id>` branch pushed to the forge with `--force-with-lease` expecting
it not to exist, so two drivers never take the same slice; one delegate per slice in its own worktree, running
the slice's ladder from example map to converged verdict, strictly sequential inside; a written shared-surface
rule — the slice's own record and model block, the service and context that own it, the events module
additively, new timestamped migrations only, the composition root — held by `make check-slice-scope` on every
`slice/<id>` branch; and merges in split order, each followed by its own demo stop. A slice's plan and tasks
live under `specs/<feature>/slices/<id>/` from the day they are written, the canonical slot being a link the
Spec Kit commands write through, so being there no longer means shipped: `status: implemented` does on the
event profile, a row in `slices/README.md`'s register otherwise. `docs/event-model.md` says why the contract
comes first; a harness that cannot delegate takes one slice at a time and names the rest.

The table is the owner's to change as and when. `/model-delegation-settings implement=strong claude.fast=haiku` — the command over
`python3 scripts/agents/models.py --set` — edits it checked — a stage's role, or what a role maps to on a harness; a role a stage newly
names is added as `null` under every harness until it is mapped, and a harness the registry records no
mechanism for is refused rather than given a row nothing reads. A hand edit works the same way, held by
`make check-agents`. `/drive` reads the table before every stage, so a change takes effect at the next one;
the file is committed, so a change is a diff; and `slipwai migrate` merges a newer factory's table over the
edited one the way it merges every generated file, with the project deciding any conflict.

The split is a hypothesis. Only Claude Code's `fast` is seeded — `sonnet`, an alias its Agent tool takes; on
every other harness the table is inert until the owner maps an identifier, and the script says so rather than
guessing one. The benchmark is what turns the hypothesis into a decision: if the cheaper model on
implement costs more in converge passes and mutation failures than it saves, the default moves — which is why
the model each stage ran on is said out loud, where a benchmark can read it.

### What each stage costs

Nothing recorded what a slice cost or how well each stage did its job, so whether a change to a stage prompt, a
skill or a generated project's layout made slices cheaper or better was a matter of impression. A project
now keeps one record per slice — `specs/<feature>/slices/<id>/benchmark.json`, beside the slice's other
artifacts — and one per feature, `specs/<feature>/benchmark.json`, for the stages above the slice loop, which are
the feature's cost and not the next slice's. `/drive` opens an entry before each stage and closes it after with
`scripts/agents/benchmark.py start|end <dir> <stage>`, and the record is append-only: a stage run twice is two
entries, which is how converge passes and rework are counted rather than declared.

**What is read, and from where.** Wall time, from the two timestamps. Tokens by model, from the harness's own
transcript between the two cursors: `scripts/agents/registry.json` records under `usage` where each harness keeps
one — Claude Code's `~/.claude/projects/<slug>/<session>.jsonl`, whose every assistant line carries
`message.usage` and `message.model` and is written once per content block, so a request is counted once by its
id, plus the sub-agent transcripts beside it, which is where a delegated stage's tokens are; Codex's rollout under
`~/.codex/sessions/`, its `token_usage_record` lines or the difference between two `token_count` totals — and
`null` on the other thirty-four, with the reason. The session is named by what the harness puts in the
environment (`CLAUDE_CODE_SESSION_ID`, `CODEX_THREAD_ID`), never guessed from the newest file, and a session that
changed mid-stage is `null` too. Which model ran and whether the stage was delegated, from the same lines. The
tasks `tasks.md` gained during a converge pass, from its checkbox counts at start and end. Files touched and lines
added and removed, from `git diff` against the commit the slice started at, when the record is closed. What
nothing on disk can say is passed to `end` by the stage that knows it — `gaps=N`, `findings=N`,
`seams=N`,
`mutation_score=…` copied from the tool's own line, `verify_failures=N`, `outcome=accepted|behaviour|implementation`
— and a number that was not read is not written.

`/benchmark` is the reader's entry point: it redraws `specs/<feature>/benchmark.md` from the records — one row per
slice (wall, tokens in and out, the models that ran, converge passes, tasks appended, gaps before and after
converge, mutation score, adversary findings, demo outcome, verify failures, rework, tasks, files, lines), then
every stage of every slice, the notes, and how to read the numbers — and reads it back: where the cost sits, what
moved between slices, whether the `fast` role paid for itself, what is unknown and why. Closing a slice redraws the
same page, so it is never older than the last slice. `make benchmark` prints the table in the terminal and
`--json` gives anything that wants to plot it the summaries. None of it goes on the demo board, which is the
actor's view of the product.

**What the numbers can and cannot be used for.** They compare stages across the slices of one project on one
harness, and one slice before and after a change to a prompt, a skill or the layout — which is what turns the
model split above into a decision: if the cheaper model on implement costs more in converge passes and mutation
failures than it saves, the default moves. They are tokens, not prices: a price is a provider's table on a date
and would be wrong within the month. They do not compare harnesses, whose transcripts count different things, or
projects, whose slices are not the same size — the shape columns are there to normalise, not to equate. A
stage's tokens are a floor: the turn that runs `end` is itself still being written when `end` reads the
transcript. And the factory's own gate runs no fixed benchmark slice: that is an agent run in CI, with credentials
and a bill, and it is comparable only when the same harness and model run it every time — a decision for an issue
of its own, once real records show what varies between two runs of the same slice.

### How implementation is delegated

Two settings in `.specify/drive.json`, beside the models table and changed the same way — through
`/drive-settings`, checked, at any time. `delegate` is how much one implementation delegate is handed:
`story`, every rule of one user story run as its own cycle in one context, which is what stops a fresh
delegate re-reading the same four files per rule; `rule`; or `task`. `cycle` is how many RED tests one
RED-GREEN-REFACTOR cycle opens with: `rule`, a rule's examples together, each failing for its own stated
reason and stub-first so none fails on a build; or `example`, one at a time. The defaults are `story` and
`rule`; a story is never a cycle unit, since that is the batch Principle V prohibits. Two vetoes override the
defaults on a slice: no story tags falls to `rule`, and a map without numbered rules falls to `task` and
`example`. Whatever the boundary, siblings with disjoint manifests run concurrently and a delegate may fan out
inside its boundary; one cycle is never parallel. The delegate reports both settings and its fan-out, and the
implement entry records them as `delegate=`, `cycle=` and `split=N`, so `make benchmark` can say what a wall
time was a wall time *of*.

### Cruise: the driver as owner

`/drive` stops for a product decision and at every demo, because both belong to a person. `/cruise` runs the
same ladder — `commands/drive.md`, every rule as written — with nobody at the wheel. It decides as the product
owner: on the host where the stage recommends an answer or a standing decision covers the question, and through
a `drive-skipper` delegate where the question is open. It runs each demo as the actor through a `drive-hand`
delegate, with a browser where the slice has a screen. A block is work before it is a stop: a `drive-bosun`
delegate stubs the missing thing behind its port, takes the reading that keeps every MUST, or repairs the run,
and writes down what it did, so a run parks only at the catastrophic. When the split runs out it audits the specification
against what shipped, so *done* means satisfied rather than exhausted. Every decision is written where `/drive`
would have written a person's and again in `specs/<feature>/decisions.md`; every demo in the slice's
`demo-log.md`. A script re-invokes it with a fresh context until it says `done`, and it stops only for a human.
It ships disabled. [Cruise](cruise.md) says how to start, watch and stop a run, what the settings are, and where
it parks rather than guesses.

## The commands

Seventeen in the event profile, fifteen in `standard`, and four more in a repository that adopted the method
around existing code. None of them is copied: each is generated against this
project's profile, languages, frameworks and services, so the paths and toolchains named in them are real.

| Command | Does |
|---|---|
| `/drive` | The ladder above: one slice from wherever it currently stands to an actor-visible demo |
| `/cruise` | The same ladder with nobody at the wheel: the agent decides as the product owner and runs each demo as the actor, iteration after iteration, until the specification is satisfied — stopping only for a human ([Cruise](cruise.md)) |
| `/whats-next` | One slice, one stage, one command and the reason, in at most six lines — the board's ➡️ *Next* line on its own, for the start of a session or after an interruption |
| `/where-are-we` | The demo stop's progress board on demand — ✅ works now · 🔧 in progress, and the ladder stage it has reached · ⬜ still to come, `N of M slices accepted` · ⚠️ not working yet · 🔀 ready (parallel) · ➡️ next (this session) · ⛔ blocked — read off the same artifacts, running nothing |
| `/gaps` | Adversarially review a written artifact — spec, criteria, examples, a slice diff — for holes before they become rewritten tests |
| `/adversary` | Direct an independent agent to try to break a finished slice: hostile inputs, replays, interleavings, authorisation paths |
| `/mutation` | Run the backend's native mutation testing, or explain the project decision that is missing |
| `/constitution-coverage` | Check a ratified constitution against the floor this project depends on, or print the floor |
| `/model-delegation-settings` | Show which model runs each stage of `/drive`, or change it — a stage's role, or what a role maps to on this harness — through the checked path |
| `/drive-settings` | Show how `/drive` delegates implementation — the boundary a delegate is handed and the cycle it runs — or change either, through the checked path |
| `/benchmark` | Draw `specs/<feature>/benchmark.md` from the slice records — what each slice cost and how each stage did — and read it back: where the cost sits, what moved, whether the model split paid, what is unknown and why |
| `/cruise-settings` | Show how `/cruise` runs on its own — who decides, how it releases, what it demos with, when it parks — or change any of it, through the checked path |
| `/cruise-status` | Say whether a `/cruise` runner is running, how the last iteration ended, whether it is parked and why, and show the tail of its feed |
| `/cruise-stop` | End a `/cruise` run after the iteration in flight, or at once with `now` |
| `/cruise-tell` | Queue a message for a running `/cruise` — a steer, a fact it lacked, a scope — which the next iteration carries; `--now` ends the iteration in flight for it |
| `/add-service` | Add a service — its own language, framework and axis answers — without hand edits |
| `/add-frontend` | Add a browser application the same way |
| `/catch-up` | After `slipwai migrate`, work through what the newer factory now asks of code it did not write — the changelog notes for the versions crossed, and the gates that are now red because of them |
| `/example-map` *(event)* | Turn one model slice into rules, concrete examples and Given/When/Then |
| `/validate-code-against-model` *(event)* | Check code and tests against the event model for semantic drift |
| `/survey` *(adopted)* | Re-survey the repository with the factory and reconcile what it finds against what `project.json` records: a fact recorded as detected is refreshed, a fact a person confirmed or overrode is never changed behind their back |
| `/ground` *(adopted)* | Ask what the tree cannot say — one question per row of the convergence map, the rung meanings and the survey's evidence in front of the person — and record each answer where the record keeps it, with the person's own words as the evidence |
| `/characterise` *(adopted)* | Pin what the code a slice is about to change does today, at the seam where it can be observed, before it changes — and refuse "full coverage first", which is where these programmes die |
| `/strangle` *(adopted)* | Move one capability out of the code that was here into a new home, behind a routing seam, with the data answer decided and a row written in the retirement ledger — refusing a behaviour nothing has pinned |

The last four arrive only where `slipwai adopt` installed the method around code that was already there,
and they are experimental with the rest of adoption, as `AGENTS.md` defines the word:
[Adopt an existing repository](adopting.md) is what they are for.

Commands live in `commands/` at the repository root, which is canonical; `./init` projects them into
whichever agent harness you use. See [Bootstrap Spec Kit](spec-kit.md).

## Story splitting

Stage 4, ahead of any plan, because a plan written over an undivided outcome plans the wrong thing. The goal
is not smaller tickets: it is **N% of the system 100% done and demonstrable, rather than 100% of the system
N% done**.

The split stays *vertical*. If the actor in a child story is a component, layer, queue, database or service,
it is a task wearing a story's clothes. The one exception is named rather than smuggled: in an adopted
repository, a **method slice** — one rung on one axis of the convergence map, the team as its actor — sits in
the same split as the product slices and travels the same path (the skill's *Method Slices* section says what
keeps one honest):

```text
Good:  Buyer can pay one invoice by card and receive a confirmation.

Bad:   Backend exposes payment endpoint.
       Frontend calls payment endpoint.
       Database stores payment rows.
```

### The seven dimensions to split along

Used as prompts rather than a checklist — run through them, then take the split that creates the most value
and the most optionality:

| Dimension | The question to ask |
|---|---|
| **Capability** | Which narrower customer capability still delivers value? |
| **Path** | Which happy path, alternate path, branch or operation can stand alone? |
| **Interface** | Which channel, consumer, UI level, device or integration can prove the behaviour first? |
| **Data** | Which data subset, file type, entity type, field subset or quantity can we support first? |
| **Rules** | Which business, validation, permission, compliance or policy rules can be scoped safely? |
| **Quality** | What is the simplest acceptable quality level — manual, batch, low fidelity, small scale, slower, generic UI? |
| **Risk** | What spike, tracer bullet or walking skeleton would answer one specific risky unknown? |

Stuck in technical decomposition anyway? The **Hamburger method**: list the technical layers, list
simpler-to-richer options within each, then take a first bite that crosses *every* layer. The failure it
prevents is eating one layer down to the plate.

### Choosing which slice goes first

- Prefer the split that lets you deprioritise or delete at least one follow-up story.
- Prefer the split producing more similarly sized children, where the value is comparable.
- Prefer the end-to-end slice that burns down integration or architecture risk early.
- **Prefer the product's core, differentiating capability over infrastructure that merely feels
  foundational.** Auth, user management, admin and settings are the classic trap: they feel like they have
  to come first, but they are not the value the product exists to deliver. Stub them — a hardcoded user, a
  fixed role — until a real core-capability slice needs them to be real, then build that piece for real in
  its own slice.
- If the first slice cannot be useful to anyone, make it useful for learning, ops or validation, and say so
  explicitly.

### The bar each child story has to clear

INVEST, used as a check rather than a template — **I**ndependent enough to build, test, release, reorder or
drop; **N**egotiable in scope and quality; **V**aluable to a real actor; **E**stimable because the unknowns
and deferrals are visible; **S**mall enough to finish inside the planning horizon; **T**estable through
observable examples.

Then the feedback triad: a good slice **works**, **delivers value**, and **can generate feedback**. A slice
that only makes internal progress is a task. A slice that works but can produce no feedback or learning is a
sign that a thinner or different slice would be worth more.

## Example mapping

`/example-map` takes one slice and works four items with you — the **story**, the **rules** that govern it,
**concrete examples** of each rule, and the **questions** nobody can answer yet. The output lands in
`specs/<feature>/slices/<id>/examples.md`, and the slice's `gwt` field in the model links it.

The rule that makes it worth running: **it will not invent an event, field, stream identity or policy to
close a product question.** An unresolved question stays a question on the card, rather than becoming a
decision nobody made that reads as agreed three slices later.

### What one looks like

```markdown
## Story
Buyer places an order for the items in their cart and gets a confirmation.

## R1 — An order cannot be placed from an empty cart
- empty cart → rejected, nothing recorded

## R2 — The order total is the sum of the cart's line totals at the moment it is placed
- 2 x £29.99 → order total £59.98, and later price changes do not move it

## R3 — A cart that has been ordered from cannot be ordered from again
- placing twice on CART-001 → the second is rejected

## Questions
- Does a cart expire, and if so does expiry reject or silently empty it?  → for the product owner
```

**Rules own their examples.** Each numbered rule carries its examples and, below them, their scenarios, rather
than every rule in one section and every scenario in another. The rule is the unit of a RED-GREEN-REFACTOR
increment — its examples may be written together or one at a time, but an increment never spans rules — so
this grouping is the boundary the tasks are cut on and the converge verdicts cite. Rules are never renumbered
once cited, and the shape is not retrofitted onto a map already implemented.

Then each agreed example becomes a Given/When/Then scenario in the vocabulary of the event model, under its
rule — prior events, one command, the events produced:

```markdown
### Scenario: Successfully place an order

**Given** (prior events):
- CartCreated { cartId: "CART-001", customerId: "CUST-123" }
- ItemAddedToCart { cartId: "CART-001", productId: "PROD-42", quantity: 2, unitPrice: 29.99 }

**When** (command):
- PlaceOrder { cartId: "CART-001", paymentMethod: "card_ending_4242" }

**Then** (events produced):
- OrderPlaced { orderId: "ORD-789", cartId: "CART-001", totalAmount: 59.98, timestamp: "2026-01-15T10:30:00Z" }
```

An error case carries an error and **no events**, never both:

```markdown
### Scenario: Cannot place order with empty cart

**Given** (prior events):
- CartCreated { cartId: "CART-001", customerId: "CUST-123" }

**When** (command):
- PlaceOrder { cartId: "CART-001", paymentMethod: "card_ending_4242" }

**Then** (error - no events):
- Error: "Cannot place order: cart CART-001 contains no items"
```

### Which rules earn a scenario, and which do not

The test that keeps the map from filling with noise: **does this error depend on what has already
happened?**

| Write a scenario | Let the type system handle it |
|---|---|
| "Cannot archive an already-archived task" | "Email must contain @" |
| "Cannot withdraw more than the balance" | "Title cannot be empty" |
| "Maximum 100 items per order" | "Amount must be positive" |

The left column depends on prior events, and a different business could rule differently. The right column
is true everywhere and belongs in a domain type, where invalid states are unrepresentable rather than
tested for.

Use concrete, realistic values throughout — `CART-001` and `£29.98`, never "a valid cart" and "some amount".
An example that could be satisfied by two different behaviours is not yet an example.

**`/gaps`** then runs over the result, and again over the slice diff after convergence — the last point
before a demo where a promise that cannot be reached is still cheap to find.

## Spec Kit's own phases are hooked from both sides

The generated `.specify/extensions.yml` gives every `/speckit-*` command a before and after hook, so the
method applies even to a session that never typed `/drive`:

| Hook | Does |
|---|---|
| before `constitution` | Prints the floor this project's constitution cannot ship without, so the drafting session sees it before it writes rather than at `make verify` |
| after `constitution` | Runs `/constitution-coverage` against what was just written — the one phase that could still fix a gap in a single edit |
| after `tasks` | Suggests a host compact (`/compact` where the harness has it): everything the next phase reads is now on disk, which makes this the cheapest point in the workflow to do it. The agent cannot run it. |
| after `implement` | Suggests convergence, because checked-off tasks are evidence about the task list rather than about the spec |
| after `converge` | Runs `/gaps`, tracing each promise to an observable test and a reachable production path |

Most are `optional` on purpose — a hook that *runs* a command is a second route through the workflow, and
the constitution principles ask for one. The two that are not optional both re-check an artifact the phase
above just wrote, which adds no route to production.

## Spec Kit is never edited in place

Spec Kit records a SHA-256 for every file it installs, and those hashes are what make
`specify integration upgrade` automatic: untouched files are replaced, edited ones are preserved and
reported. So editing one in place does not fail loudly — it quietly converts every future upgrade into a
manual reconciliation.

Customisations go in `.specify/presets/<profile>/` instead, which shadows a core template by name at a
declared priority. Core stays pristine and anything not overridden keeps inheriting upstream improvements.
`make check-speckit` fails an in-place edit, a deleted managed file, a preset with no or invalid
`preset.yml`, and a declared override whose file is missing — and it reads the committed manifests directly,
so it needs no Spec Kit CLI and no network.

## The constitution is gated from both sides

`make check-constitution` fails when a ratified `.specify/memory/constitution.md` stops carrying
[minimum CD](https://minimumcd.org/minimumcd/), the practices the shipped skills teach — strict typing,
ubiquitous language and domain types, the hexagonal boundary, acceptance-driven testing, observability,
security, compatibility, ADRs, and a governance clause — or, in the event profile, the Event Modeling and
event-sourcing obligations.

`make check-speckit` guards the other direction: an event-sourced mandate pasted into a `standard` project
is a mismatch it names, with the two valid resolutions.

The gate deliberately passes while the file is still the untouched template `./init` installed — it reports
`nothing drafted yet`, so the first commit can go through `verify` before a principle has been written,
which matters under a production target where that push is the first deploy. One edited byte and it applies
in full. `make constitution-requirements` prints the normative text; `/constitution-coverage` runs the same
check from an agent session.

Full detail, including how Spec Kit itself is obtained: [Bootstrap Spec Kit](spec-kit.md).

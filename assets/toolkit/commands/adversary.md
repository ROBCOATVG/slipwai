---
description: Record the attack surface a slice widened, and attack what a whole capability widened
argument-hint: [feature-or-diff-or-capability] [--full]
---

# Adversary

Read `skills/adversarial-testing/SKILL.md`. This is the end-of-phase pass that skill describes, not a
per-increment one, and it is not a pipeline check: nothing in CI asserts that it happened. What survives a
pass is the tests it leaves behind, and those keep paying on every later slice.

**A slice records; a capability is attacked.** Per slice, at the ladder's *Attack surface* rung, this command
writes the slice's trigger table and attacks nothing — `--full` included. Once per capability, at *Capability
gates*, when its last slice has merged, it runs one pass over every boundary the capability's slices widened,
with the capability's diff as the diff — **only where at least one of those slices recorded a trigger
`widened`**, or the capability was given `--full`. Otherwise the capability's row is a skip, and the skip
clears the gate. The slice that closes a feature's split no longer takes a full pass of its own: a pass runs
only when something widened.

**One exception, under the `open` release mode.** Where a merge reaches the actor at once, a slice whose table
has the authorisation, identity or money trigger `widened` is attacked at its own rung, before its push.
Everywhere else a merge is held back by a flag or a keystone, so what the capability's pass has not yet
covered is dark until it has; under `open` it would be live. Nothing else is attacked per slice in any mode.

## Record the slice's trigger table

`specs/<feature>/adversary-log.md` is the record of every surface already attacked and every slice's table.
Read it, then compare it with the slice's diff. A trigger is `widened` when the diff does any of these:

- adds or changes a driving adapter — an HTTP route, a CLI command, a queue consumer
- adds or changes a driven adapter, or the provider types behind one
- adds an authorisation decision, or changes who can reach one that already exists
- changes who an actor is taken to be — a credential, a session, a token, an account link
- changes an amount, a balance, a price, a payment, or who is charged
- makes a claim about concurrency, idempotency, ordering, retention, or time
<!-- section: logged-surface -->
- changes an event schema, a stream identity, or what a projection is scoped to
<!-- end section -->
<!-- section: stored-surface -->
- changes an event schema, or the version a state-stored write is saved at
<!-- end section -->

Write the trigger table as this slice's row, headed `## <slice-id> · <commit> · <date> · trigger record` — one
line per trigger, each `widened`, `already covered`, or `not present`, with the diff path or the prior log row
that is the evidence:

| Trigger | Status | Evidence |
|---|---|---|
| driving adapter (HTTP route, CLI command, queue consumer) | widened / already covered / not present | diff path or prior log row |
| driven adapter or the provider types behind one | widened / already covered / not present | diff path or prior log row |
| authorisation decision (who can reach one that already exists) | widened / already covered / not present | diff path or prior log row |
| identity: a credential, a session, a token, an account link | widened / already covered / not present | diff path or prior log row |
| money: an amount, a balance, a price, a payment | widened / already covered / not present | diff path or prior log row |
| concurrency, idempotency, ordering, retention, or time | widened / already covered / not present | diff path or prior log row |
<!-- section: logged-trigger -->
| event schema, stream identity, or projection scope | widened / already covered / not present | diff path or prior log row |
<!-- end section -->
<!-- section: stored-trigger -->
| event schema, or the version a state-stored write is saved at | widened / already covered / not present | diff path or prior log row |
<!-- end section -->

A slice that only adds a rule behind a surface the log already covers widens nothing, and says so: name the
rows that cover its boundaries and state that the diff did not widen them. The table is a read of the diff,
not a pass, and spawns nothing. It is what the capability's pass is decided by, so a trigger written
`already covered` names the row that covers it, and a table nobody wrote is a capability that cannot be
skipped.

## Decide whether the capability owes a pass

At *Capability gates*, read every trigger record of the capability's slices. **A pass is owed when at least one
of them has a trigger `widened`, or `--full` was passed**; it covers every seam any slice widened, alone and
together — a seam one slice opened and the next one reached. When none widened anything, write the
capability's row as a skip — headed `## <capability> · <commit> · <date> · skipped: no slice widened a
trigger`, naming each slice's trigger record it relied on, `Spawned:` empty — and the gate is cleared.
**Skipping is a reported decision, not silence.** A seam a slice's own pass already attacked under `open` is
cited rather than probed again, unless a later slice changed it.

## Triage the seams

The trigger table is what `/sail` must see in the log before any `sail-adversary-privateer` spawn. Name each seam
the diff widened against that table and the attack catalogue. Spawn one adversary per widened seam, not one
per catalogue category. A seam whose brief has no explicit file manifest is not spawned: record it as
omitted, with why. Record every seam not spawned in `specs/<feature>/adversary-log.md` with the prior rows
or diff evidence that show why it was not widened. For `--full`, select every applicable catalogue seam, not
every seam in the catalogue file.

For each selected seam, derive an explicit file manifest from the diff: the external boundary, production
path, tests, schemas, migrations and configuration the adversary needs. Put those paths in its brief so it
does not spend turns rediscovering the repository. Each seam goes to the `sail-adversary-privateer` type
(`agents/sail-adversary-privateer.md`), which is the standing brief and carries the read-only scope into the harness
itself; the per-seam brief adds only that seam's contract, manifest, non-goals and attack question, and does
not restate the scope or `docs/delegated-agent-safety.md`.

Seams whose manifests are disjoint are concurrent siblings, delegated in the same turn the way `[P]`
implementation tasks are. The host writes the log after the batch reports; it does not re-attack.

## The pass

Start the `adversary` benchmark entry immediately before spawning. Build each brief from the specification,
tests, external interface, and stated non-goals, **bounded to the boundaries the diff touches**. Probe parsing,
authorization, concurrency, time, partial failure, and operational boundaries as far as those boundaries can
express them; a category this surface cannot reach is not a hole in the pass. Do not re-probe a surface the log
covers unless the diff changed it. **Time-box it.** An hour of agent attack on one slice is generous. Breadth
first across the selected seams, then depth on whatever felt soft; stop when those seams have been probed, not
when the catalogue is exhausted. A finding must reproduce a broken promise through a reachable boundary and
state the consequence. Fixes follow through a failing test after triage, under a new `implement` entry.
<!-- section: logged-pass -->

Replay, optimistic concurrency, stream identity, projection scoping, and schema evolution are in scope
wherever the changed boundary can express them.
<!-- end section -->
<!-- section: stored-pass -->

On a service that keeps current state, the same pass asks what a stale version lets through, whether a
retried command raises its event twice, and what a reader sees between the write committing and the event
being raised — the window a replay would not have left open.
<!-- end section -->

Resolve the stage's role first. Each seam may use another role where its work is mechanical and its answer
checkable; otherwise it inherits the adversary stage's role. The type carries the resolved model on every
harness whose agent file names one; anywhere else, set every delegate's model explicitly through the harness
mechanism — never rely on its default — and record the actual model per seam. Do not change the
stage default to `fast`: a per-seam choice is evidence for later slices, not a new global conclusion.

## Record it

Append to `specs/<feature>/adversary-log.md` either way. Copy this shape; an unwritten row is a pass that
has to be run again. A slice's trigger record is the heading and the table; a capability's pass, or the
`open` exception's, adds the lines below it:

```markdown
## <slice-id or capability> · <commit> · <date>

| Trigger | Status | Evidence |
|---|---|---|
| … | widened / already covered / not present | `path` or prior row |

Spawned: <seam> · `sail-adversary-privateer` · <model> · delegated, fresh context · manifest: <paths>
Omitted: <seam> · <why>
Findings: none | …
```

Each selected seam records its file manifest, the type that ran it, its model, and `delegated, fresh
context`; each omitted seam records why it was not spawned. A skip is a row too, naming the rows it relied
on, with `Spawned:` empty, and so is a slice's trigger record — its heading ends `trigger record` and it
attacks nothing. A `predates the adversary gate` row — written once by `check-decisions.py
--adversary-baseline` for slices finished before the log was held — records that nothing was attacked, and is
never a row a skip may rely on. Findings include **no findings**, since an empty result is exactly what makes the
next slice's skip decidable.

Once every adversary has reported, triage each finding as confirmed, question, duplicate or declined, then
end the `adversary` benchmark entry with `findings=N` `seams=N` **before writing any fix**. `seams=N` is
delegates spawned; a recorded skip is `0`. Confirmed defects re-enter normal RED-GREEN-REFACTOR
implementation under a new `implement` entry. This boundary is what lets the benchmark answer what the pass
itself cost.

Each finding carries a severity — `CRITICAL` (data of one actor reaches another, or an actor gains a role),
`HIGH`, `MEDIUM`, `LOW` — and a state: `open`, `fixed` with the commit, `stowed` into the fairway's careen,
or `deferred` with the person's name and their reason, in their words.

**One round, and a bar.** The pass runs once per capability — and per slice only for the `open` exception —
not until it converges: in the experiment it ran 21 rounds and produced 129 findings, 64 of them LOW and most of those about wording, and slice S20 still ended
with five open. A finding at or above the fairway's severity bar closes before the person's demo, in a follow-up slice in
the same fairway — or, for the `open` exception, before the slice's push. One below it is **stowed** — a row
in `fairways/<name>/careen.md` naming the capability or the slice — and the work goes on. The careen is a
hardening slice the fairway runs when its planned slices are done, and its demo is that the findings are
closed. Work is never dropped; it is moved somewhere a person can see the size of it. The bar is the
harbour's to set and defaults to `MEDIUM`, because the experiment's LOWs were genuinely wording and its
MEDIUMs genuinely were not.

**An open `CRITICAL` is the next slice**, placed ahead of every product and
method slice in the split until it is fixed or a person defers it in that row; the ready set
offers it first and `/story-splitting` places it there. A triage row that states what a dependency does by
default — a driver's TLS mode, a framework's role prefix, a runner's reporter — cites the artefact it was
read from: the jar disassembled, the documentation at the pinned version, a test against the real thing.
Without one, the row reads *assumed*, and an assumed row closes nothing. Two real adoptions each recorded a
confident default that the artefact contradicted, and one of them was the fix.

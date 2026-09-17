"""`commands/adversary.md`: select and attack only the seams a slice widened."""
from __future__ import annotations


def adversary_command(event: bool) -> str:
    extra = (
        """

Replay, optimistic concurrency, stream identity, projection scoping, and schema evolution are in scope
wherever the changed boundary can express them."""
        if event
        else ""
    )
    trigger_rows = """| driving adapter (HTTP route, CLI command, queue consumer) | widened / already covered / not present | diff path or prior log row |
| driven adapter or the provider types behind one | widened / already covered / not present | diff path or prior log row |
| authorisation decision (who can reach one that already exists) | widened / already covered / not present | diff path or prior log row |
| concurrency, idempotency, ordering, retention, or time | widened / already covered / not present | diff path or prior log row |"""
    if event:
        trigger_rows += """
| event schema, stream identity, or projection scope | widened / already covered / not present | diff path or prior log row |"""
    surface = """- adds or changes a driving adapter — an HTTP route, a CLI command, a queue consumer
- adds or changes a driven adapter, or the provider types behind one
- adds an authorisation decision, or changes who can reach one that already exists
- makes a claim about concurrency, idempotency, ordering, retention, or time"""
    if event:
        surface += "\n- changes an event schema, a stream identity, or what a projection is scoped to"
    return f"""---
description: Attack the attack surface a slice changed, and record what was attacked
argument-hint: [feature-or-diff] [--full]
---

# Adversary

Read `skills/adversarial-testing/SKILL.md`. This is the end-of-phase pass that skill describes, not a
per-increment one, and it is not a pipeline check: nothing in CI asserts that it happened. What survives a
pass is the tests it leaves behind, and those keep paying on every later slice.

## Decide whether this slice owes a pass

`specs/<feature>/adversary-log.md` is the record of every surface already attacked. Read it, then compare it
with the diff. **Do not spawn anything until this slice's trigger table is written into that log.** A pass is
owed when the diff does any of these:

{surface}

Write the trigger table as the first part of this slice's log row — one line per trigger, each `widened`,
`already covered`, or `not present`, with the diff path or the prior log row that is the evidence:

| Trigger | Status | Evidence |
|---|---|---|
{trigger_rows}

A slice that only adds a rule behind a surface the log already covers owes nothing. **Skipping is a reported
decision, not silence**: name the rows that cover the slice's boundaries and state that the diff did not
widen them. Skip unless any trigger is `widened`, or the slice closes a feature's split, or `--full` was
passed. Two overrides sit above the trigger — `--full`, and the slice that closes a feature's split,
which takes a full pass whether or not the trigger fired. Consecutive skips must never accumulate into a
release.

## Triage the seams

The trigger table is what `/drive` must see in the log before any `drive-adversary` spawn. Name each seam
the diff widened against that table and the attack catalogue. Spawn one adversary per widened seam, not one
per catalogue category. A seam whose brief has no explicit file manifest is not spawned: record it as
omitted, with why. Record every seam not spawned in `specs/<feature>/adversary-log.md` with the prior rows
or diff evidence that show why it was not widened. For `--full` and the slice that closes a feature's split,
select every applicable catalogue seam, not every seam in the catalogue file; those overrides remain full
passes.

For each selected seam, derive an explicit file manifest from the diff: the external boundary, production
path, tests, schemas, migrations and configuration the adversary needs. Put those paths in its brief so it
does not spend turns rediscovering the repository. Each seam goes to the `drive-adversary` type
(`agents/drive-adversary.md`), which is the standing brief and carries the read-only scope into the harness
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
state the consequence. Fixes follow through a failing test after triage, under a new `implement` entry.{extra}

Resolve the stage's role first. Each seam may use another role where its work is mechanical and its answer
checkable; otherwise it inherits the adversary stage's role. The type carries the resolved model on every
harness whose agent file names one; anywhere else, set every delegate's model explicitly through the harness
mechanism — never rely on its default — and record the actual model per seam. Do not change the
stage default to `fast`: a per-seam choice is evidence for later slices, not a new global conclusion.

## Record it

Append to `specs/<feature>/adversary-log.md` either way. Copy this shape; an unwritten row is a pass that
has to be run again:

```markdown
## <slice-id> · <commit> · <date>

| Trigger | Status | Evidence |
|---|---|---|
| … | widened / already covered / not present | `path` or prior row |

Spawned: <seam> · `drive-adversary` · <model> · delegated, fresh context · manifest: <paths>
Omitted: <seam> · <why>
Findings: none | …
```

Each selected seam records its file manifest, the type that ran it, its model, and `delegated, fresh
context`; each omitted seam records why it was not spawned. A skip is a row too, naming the rows it relied
on, with `Spawned:` empty. Findings include **no findings**, since an empty result is exactly what makes the
next slice's skip decidable.

Once every adversary has reported, triage each finding as confirmed, question, duplicate or declined, then
end the `adversary` benchmark entry with `findings=N` `seams=N` **before writing any fix**. `seams=N` is
delegates spawned; a recorded skip is `0`. Confirmed defects re-enter normal RED-GREEN-REFACTOR
implementation under a new `implement` entry. This boundary is what lets the benchmark answer what the pass
itself cost.

Each finding carries a severity — `CRITICAL` (data of one actor reaches another, or an actor gains a role),
`HIGH`, `MEDIUM`, `LOW` — and a state: `open`, `fixed` with the commit, or `deferred` with the person's name
and their reason, in their words. **An open `CRITICAL` is the next slice**, placed ahead of every product and
method slice in the split until it is fixed or a person defers it in that row; the loop's Convergence stage
offers it first and `/story-splitting` places it there. A triage row that states what a dependency does by
default — a driver's TLS mode, a framework's role prefix, a runner's reporter — cites the artefact it was
read from: the jar disassembled, the documentation at the pinned version, a test against the real thing.
Without one, the row reads *assumed*, and an assumed row closes nothing. Two real adoptions each recorded a
confident default that the artefact contradicted, and one of them was the fix.
"""

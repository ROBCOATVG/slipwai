---
name: architecture-decisions
description: Capture a hard-to-change decision as an ADR in docs/adr/ using Nygard's five sections, and supersede rather than edit one that has been accepted. Use when a decision would cost a migration rather than a refactor to reverse — event schemas, stream identity, tenancy, storage, identity and authorisation, personal-data handling, a new dependency, a published contract — or when asked to write, find, revisit, or supersede an ADR. Also use when a slice's research.md turns out to hold a decision that outlives the slice. NOT for reversible implementation choices, slice-scoped design notes (those stay in research.md), constitutional principles (amend the constitution), or event-model shape (that is global-event-model).
---

# Architecture decisions: write down what you cannot take back

An ADR records one decision, its context, and what it commits you to. It exists because the expensive
decisions are invisible later: the code shows *what* was chosen and never *why*, or which alternatives were
weighed and rejected. Six months on, nobody can tell a deliberate constraint from an accident, so the
constraint gets "cleaned up" and the reason is rediscovered as an outage.

**The format is Michael Nygard's**, unchanged since 2011 and deliberately small: Title, Status, Context,
Decision, Consequences. Five sections, one page. A template nobody can be bothered to fill in records
nothing.

---

## 1. Is this ADR-worthy?

One question, and it is not "is this important":

> **If we change our mind in six months, is the cost a refactor or a migration?**

A **refactor** — code moves, behaviour is preserved, one team, one afternoon — needs no ADR. Write it in the
code, or in the slice's `research.md`.

A **migration** — stored data must change shape, another team or customer must coordinate, a contract must be
versioned, or the answer is "we would have to rewrite history" — is an ADR. Reversal cost, not importance,
is the test.

Three secondary triggers, each of which makes something ADR-worthy on its own:

- **It is permanent by rule.** In this codebase, event schemas and stream identity are named as permanent by
  the constitution. There is no version of "we changed our mind" that is cheap.
- **Somebody will re-litigate it.** If the same argument has happened twice, the ADR is what stops the third.
- **The alternatives were real.** A decision with no rejected alternative is usually not a decision, it is
  the only option. Record the ones that were genuinely in play.

### In this codebase, specifically

These are ADR-worthy by default. The list is not exhaustive and is not a checklist to work through — it is
the set of things that have proven expensive here:

| Decision | Why reversal is a migration |
|---|---|
| An event's schema, or its name | Events are never rewritten. A rename needs a new schema version plus an upcaster that maps old events forward, forever |
| Stream identity | It is the consistency boundary and therefore the concurrency ceiling. Changing it migrates the one thing that cannot be migrated |
| The complexity rung — event-sourced, outbox, in-process events, explicit returns | Moving *up* the ladder later means reconstructing history you never stored |
| Tenancy model | It determines whether cross-tenant contamination is unrepresentable or merely forbidden |
| The event store product, or any adapter whose swap is not genuinely cheap | If the port leaks, this is a rewrite rather than an adapter change — and finding out is the expensive part |
| Personal-data classification and the erasure mechanism | It must be designed **before** the first event carrying personal data is persisted. Afterwards, append-only storage and the right to erasure no longer coexist |
| Identity and the authorisation model | Retrofitting it means auditing every read path that already exists |
| A new runtime dependency, or a published contract | Both acquire consumers who did not agree to the change |

### What is *not* an ADR

Saying so matters: a folder full of ADRs about reversible choices is a folder nobody reads, and then the
one that mattered is missed.

| Not an ADR | Where it belongs |
|---|---|
| A reversible implementation choice | The code. A comment naming the reason, if it is surprising |
| A slice-scoped design decision | That slice's `research.md`, archived with the slice — see §6 |
| A principle the whole project is held to | The constitution. Amend it via the installed Spec Kit constitution command; principles are governance, ADRs are choices made *under* governance |
| The shape of the event model — slices, frames, patterns | `docs/event-model/model.yaml`, via `global-event-model`. The ADR records *why* stream identity is what it is; the model records what it *is* |
| A learning, gotcha, or convention | The `expectations` skill routes these to their durable owner |
| A build-versus-adopt evaluation still in progress | `evaluate-existing-solutions`. It produces a proposal; when accepted, it lands here |

---

## 2. The file

```
docs/adr/NNNN-kebab-case-title.md
```

Four digits, zero-padded, allocated in order and **never reused**. `0007-tenant-scoped-stream-identity.md`.

The number is an immutable handle: it appears in commit messages, code comments, and other ADRs. Renumbering
breaks every reference silently, which is why gaps are fine and reuse is not — a deleted ADR leaves a hole,
and that is the correct outcome.

The title is a **noun phrase naming the decision**, not a question and not a verdict: *"Tenant-scoped stream
identity"*, not *"How should we scope streams?"* or *"Use tenant-scoped streams"*. It has to still read
correctly when the status is `Superseded`.

---

## 3. The template — Nygard, verbatim

```markdown
# NNNN. Title

Date: YYYY-MM-DD

## Status

Accepted

## Context

## Decision

## Consequences
```

**Status** is one of:

| Status | Means |
|---|---|
| `Proposed` | Written, not yet agreed. An agent-drafted ADR starts here — always |
| `Accepted` | Agreed and in force. The decision is now a constraint on the codebase |
| `Superseded by [ADR-NNNN](NNNN-....md)` | A later decision replaced it. The text stays exactly as it was |
| `Deprecated` | No longer in force and nothing replaced it — the need went away |

**Context** — the forces in play, in neutral language: the requirement, the constraint, the thing that made
this a decision rather than a default. Written so a reader who was not there understands the pressure. No
advocacy; if the context only supports one option, it is incomplete. A statement about what a dependency does
— a default, a limit, what a version requires — cites the artefact it was read from (its documentation at the
pinned version, its source, a run against it) or is marked *assumed*; a decision has been justified by a
library behaviour the library does not have.

**Decision** — what was decided, in the active voice: *"We will …"*. One decision. If the section needs
"and", it is likely two ADRs.

**Consequences** — what becomes true, **good and bad and neutral together**. This is the section that earns
the document and the one most often gutted into a list of benefits. Include what becomes harder, what is now
permanent, what has to be built that otherwise would not, and what the team must remember. A consequences
section with no cost in it has not been finished.

**Consequences must name the artifacts this decision invalidates or amends.** An accepted ADR does not only
constrain what happens next — it can change what an *already accepted* document means. Both are correct when
written, neither is wrong, and nothing compares them: the contradiction surfaces at the first line of code
obliged to satisfy both, which is the most expensive place to find it and the point where sunk cost argues
for coding around it.

So before an ADR leaves `Proposed`, walk the artifacts it touches — `data-model.md`, `plan.md`, the
contracts, the acceptance criteria, the event model — and name the ones whose meaning it changes, with what
now has to happen to each. A decision to encrypt a payload changes the shape of every Decider state folded
from it; an ADR that says so takes a minute, and an ADR that does not costs a rediscovery.

Two optional additions, used only when they carry weight:

- **Alternatives considered** — each with the reason it lost. Strictly this belongs inside Context, and
  splitting it out is common because it is the part future readers reach for first.
- **Compliance** — how conformance is checked, if a gate or test enforces it. In this repository that is
  usually a `make` target, and naming it stops the ADR from being the only thing holding the line.

---

## 4. Writing one

1. **Confirm it is ADR-worthy** (§1). If it is not, say so and route it — do not write a courtesy ADR.
2. **Allocate the next number.** `ls docs/adr/` and take the highest plus one. Check nothing unmerged has
   claimed it: a colliding number is a merge conflict worth having, and two ADRs sharing one is not.
3. **Write Context before Decision.** Doing it the other way round produces a Context reverse-engineered to
   justify a conclusion, which is where honest alternatives go missing.
4. **Status `Proposed`.** An agent does not accept its own architecture decision. The named owner accepts it,
   and the accepting change is what flips the status.
5. **Never invent a permanent name to fill a gap.** If the decision needs an event name, an event field, or
   stream identity that no modelling conversation has produced, that conversation is the next task. Park it
   in Context as an open question naming who decides.
6. **Link it from where it bites.** The plan's Complexity Tracking row, the code comment at the constraint,
   the `research.md` decision it generalises. An ADR nobody links to is an ADR nobody finds.

---

## 5. Changing one

**An accepted ADR is not edited.** Its text is the record of what was decided and why, at the time, with the
information available. Rewriting it destroys the only evidence of how the thinking changed — and the reason
you wanted the ADR was that reasoning gets lost.

To change a decision:

1. Write a **new** ADR. Its Context explains what changed — new constraint, new evidence, the old
   consequences turning out worse than expected.
2. Set the old one's Status to `Superseded by [ADR-NNNN](NNNN-....md)`, and nothing else.
3. Have the new one name the old one in its own Context, so the link resolves in both directions. A
   one-directional link is how a reader lands on a superseded decision and believes it.

Typo fixes and broken links are fine to correct in place. The Decision and Consequences are not.

---

## 6. `research.md` versus an ADR

They overlap and the boundary is worth stating, because getting it wrong is how the most permanent decision
in a system ends up in the least permanent place.

| | `research.md` decisions (`D-1`, `D-2`, …) | ADR |
|---|---|---|
| **Scope** | One slice | The system |
| **Lifetime** | Archived with the slice when it ships | Until superseded |
| **Reversal cost** | Usually a refactor | A migration |

**The failure mode, which has actually happened.** A project built from this starter recorded stream identity
— the one decision the constitution calls unmigratable — as decision `D-1` in slice S1's `research.md`. That
file is now archived under `specs/<feature>/slices/S1/`. The most permanent decision in the system is filed
inside a shipped slice's paperwork, and every later slice inherits it without a durable place to read why.

So: **when a `research.md` decision turns out to outlive its slice, promote it.** Write the ADR, and leave
the `research.md` entry in place with a line pointing at it — the slice's record stays honest about what it
decided, and the durable record lives where the next slice will look.

Promotion is cheap and demotion is not, so when it is genuinely unclear, write the ADR.

---

## 7. Seeding a project

A repository with no ADRs needs one before it needs a tool:
`docs/adr/0001-record-architecture-decisions.md`, Nygard's own first ADR — the decision to use ADRs at all.
It is the only ADR whose Context is about the process rather than the system, and it gives every later one a
number to follow.

---

## Checklist

- [ ] Reversal is a migration, not a refactor — or a secondary trigger applies
- [ ] `docs/adr/NNNN-kebab-title.md`, next unused number, title is a noun phrase
- [ ] All five Nygard sections present, in order
- [ ] Status is `Proposed` if an agent drafted it
- [ ] Context is neutral and would let a reader reach a different conclusion
- [ ] Decision is one decision, in the active voice
- [ ] Consequences name at least one cost
- [ ] Consequences name every already-accepted artifact this decision invalidates or amends
- [ ] Rejected alternatives carry the reason they lost
- [ ] No event name, field, or stream identity was invented to fill a gap
- [ ] Superseding: new ADR written, old status updated, links resolve both ways
- [ ] Linked from where the constraint actually bites

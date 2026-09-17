# 0001. Record architecture decisions

Date: 2026-08-12

## Status

Accepted

## Context

The expensive decisions in this codebase are the ones that cannot be taken back cheaply. Event schemas are
permanent — events are never rewritten, so every field is a commitment for the life of the system. Stream
identity is the consistency boundary and therefore the concurrency ceiling, and changing it later migrates the
one thing that cannot be migrated. The complexity rung, the tenancy model, the personal-data erasure
mechanism, the identity model: each is either right early or expensive forever.

None of them is visible in the code afterwards. Source shows *what* was chosen; it never shows what else was
considered, which constraint forced the choice, or what the choice committed us to. So the reasoning has to
live somewhere, and the places it currently lands are all wrong for it:

- **A slice's `research.md`** is archived when the slice ships. A project built from this starter recorded
  stream identity as decision `D-1` in slice S1's research, which now sits under
  `specs/<feature>/slices/S1/` — the most permanent decision in the system, filed inside a shipped slice's
  paperwork.
- **A plan's Complexity Tracking table** is scoped to one slice and justifies additions, not commitments.
- **The constitution** holds principles the project is *governed by*, not the choices made under them.
  Amending it for a storage decision would make it a changelog.
- **Commit messages and pull requests** are searchable in theory and unfindable in practice.

Meanwhile five installed skills already assume this repository has somewhere to put such a decision.
`expectations` routes an accepted architecture decision to "the repository's accepted ADR location";
`evaluate-existing-solutions` moves an accepted durable decision "into the project's existing ADR
convention"; `planning` and `technical-writing` both defer to "the repository's established ADR mechanism";
and `improve-codebase-architecture` offers to record a decision through it while explicitly forbidding
inventing a path for it. All five were pointing at a convention that did not exist, so every one of them
either did nothing or would have had to guess.

## Decision

We will record architecture decisions in `docs/adr/`, one file per decision, named
`NNNN-kebab-case-title.md` with a four-digit number allocated in order and never reused.

We will use **Michael Nygard's template**: Title, Status, Context, Decision, Consequences. Five sections, one
page, unchanged since 2011. Two optional additions are permitted where they carry weight — *Alternatives
considered* and *Compliance*.

A decision is recorded when **reversing it would cost a migration rather than a refactor** — stored data must
change shape, another team or customer must coordinate, a contract must be versioned, or history would have to
be rewritten. Importance is not the test; reversal cost is.

An accepted ADR is never edited. A decision is changed by writing a new ADR and marking the old one
`Superseded by`, with links resolving in both directions.

An ADR drafted by an agent starts at `Proposed`. Accepting it is a human act, and the accepting change is
what flips the status.

The `architecture-decisions` skill is the procedure. This constitution's Development Workflow carries the
obligation.

## Consequences

**The reasoning behind permanent decisions becomes findable**, at a stable path, by someone who was not
present. That is the whole point, and everything below is the price of it.

**The five skills above now resolve.** They stop being no-ops or guesses, and an accepted decision has one
destination rather than four plausible ones.

**A new judgement call arrives with every decision**: is this a refactor or a migration? It will sometimes be
answered wrongly. Answering it wrongly *towards* an ADR costs a page nobody needed; wrongly *away* from one
costs the reasoning entirely — so the bias is deliberate and asymmetric, and the skill says so.

**It is one more artifact to keep honest.** An ADR folder full of reversible choices is a folder nobody reads,
and then the one that mattered is missed. This is a real risk and the mitigation is editorial, not
mechanical: the skill lists what is *not* an ADR as prominently as what is.

**Nothing enforces this yet.** Numbering, the five sections, the status vocabulary, and bidirectional
supersession links are all conventions a reviewer must notice — and this repository's stated position is that
a constraint enforced by reviewer vigilance is a constraint that erodes. A `make check-adr` gate is the
obvious follow-up and is deliberately not part of this change, which is documentation only.

**Superseded ADRs accumulate and stay.** A reader may land on one and believe it. Bidirectional links are the
mitigation, and they are a convention until the gate above exists.

**The starter ships this ADR and no other.** Every later ADR in a project generated from this template is that
project's own domain reasoning, which is exactly what the template must not supply.

---
name: architecture-decisions
description: Record a hard-to-reverse system choice as an ADR in docs/adr using Nygard's five-section format. Use when reversal requires data migration, consumer coordination, a published-contract change, or replacement across a system boundary; when asked to write, find, revisit, or supersede an ADR; or when slice research reveals a decision that outlives the slice. Do not use for reversible implementation choices, slice-scoped notes, or constitutional principles.
---

# Architecture decisions

An ADR preserves one consequential choice, the forces behind it, and its costs. Code explains what exists;
an ADR explains why this option won and which constraints must survive future refactoring.

## Decide whether an ADR is warranted

Ask: **if the team changes its mind in six months, is the work a refactor or a migration?**

- A refactor stays within one implementation boundary and preserves observable behaviour. Keep that reasoning
  close to the code or in the current slice's research.
- A migration changes stored data, coordinates consumers or another team, versions a public contract, or
  replaces a capability across a system boundary. Record it as an ADR.

Typical candidates include storage and tenancy models, identity and authorisation boundaries, personal-data
handling, runtime or framework commitments, important third-party dependencies, availability/consistency
trade-offs, and published contracts. The list is illustrative; reversal cost is the test.

Do not create an ADR for a preference, a reversible library arrangement, an unresolved investigation, or a
principle that governs the whole project. Put slice-local findings in that slice's `research.md`; amend the
constitution only for governance.

## Use the repository convention

Store one decision at:

```text
docs/adr/NNNN-kebab-case-title.md
```

Allocate the next unused four-digit number and never renumber existing records. Use these sections:

```markdown
# NNNN. Title

Date: YYYY-MM-DD

## Status

Proposed

## Context

## Decision

## Consequences
```

- **Context** states the requirement, constraints, and genuine alternatives neutrally.
- **Decision** uses active voice and makes one choice: “We will …”.
- **Consequences** records benefits, costs, follow-up obligations, and existing artifacts affected.
- Optional **Alternatives considered** and **Compliance** sections are useful when they add evidence.

An agent-authored ADR always starts `Proposed`. A human owner changes it to `Accepted`. Other valid states
are `Deprecated` and `Superseded by [ADR-NNNN](...)`.

## Change a decision without erasing history

Do not rewrite an accepted Decision or Consequences section. Write a new ADR whose Context explains what
changed, mark the earlier one as superseded, and link both directions. Typographical and broken-link fixes
are safe in place.

When a slice-scoped research decision proves durable, promote it to an ADR and leave a link in the original
research. That preserves both the delivery record and the system-wide constraint.

## Checklist

- Reversal requires migration or coordination, not just refactoring.
- The next unused number and a stable noun-phrase title are used.
- Context is neutral and Decision contains one active choice.
- Consequences include costs and affected artifacts, not benefits alone.
- Agent-authored status is `Proposed`.
- Supersession creates a new ADR with links in both directions.
- The ADR is linked from the plan, contract, or code where the constraint applies.

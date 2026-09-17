# 0001. Record architecture decisions

Date: 2026-08-12

## Status

Accepted

## Context

Some decisions are expensive to reverse even when their implementation looks ordinary. Storage and tenancy
models, identity and authorisation boundaries, personal-data handling, runtime platforms, and published
contracts can require data migration or coordination with consumers. Code records what was selected but not
the constraints, alternatives, or costs that led to it.

Slice research, plans, pull requests, and commit messages are scoped to delivery work and become difficult to
discover later. The constitution records governing principles rather than every choice made under them. We
need one durable, searchable location for decisions whose consequences outlive a slice.

## Decision

We will record architecture decisions in `docs/adr/`, one file per decision, named
`NNNN-kebab-case-title.md`. Numbers are allocated in order and never reused.

We will use Michael Nygard's five sections: Title, Status, Context, Decision, and Consequences. Optional
Alternatives and Compliance sections are allowed when useful.

Reversal cost is the threshold: record a decision when changing it would require a migration, a coordinated
contract change, or replacement work across a system boundary rather than an internal refactor.

Agent-authored ADRs start as `Proposed`; acceptance is a human decision. An accepted ADR is not rewritten
when the choice changes. A new ADR supersedes it and links in both directions.

## Consequences

Future contributors can find why a durable choice was made and what it commits the product to. Decisions
that outlive slice research have a stable owner, and superseded reasoning remains visible.

The team must keep the collection selective. Filling it with reversible implementation choices would make
the consequential records harder to find. Numbering, structure, status, and links are conventions until a
repository gate enforces them.

---
name: adversarial-testing
description: Attack a finished slice through reachable interfaces, using hostile inputs, authorization failures, retries, concurrency, time, and dependency failures, then turn confirmed broken promises into ordinary regression tests at the owning layer. Use at the end-of-phase readiness gate or when asked to red-team, fuzz, stress, or try to break a feature. Use mutation-testing separately to assess whether existing tests detect changes to existing code.
---

# Adversarial testing

Mutation testing asks whether tests notice changes to code that exists. Adversarial testing asks what the
team did not think to implement. Run it after a coherent slice is demo-ready and before mutation testing;
the exploration itself is not a deterministic CI gate, but every confirmed defect leaves a deterministic
regression test.

## Build the attack brief

Use the specification and observable contract, not the author's implementation story:

- acceptance criteria and examples;
- external interfaces, payloads, responses, and authentication rules;
- business invariants and state transitions;
- dependencies, explicit non-goals, and operational promises.

Use a fresh session, independent agent, or colleague where possible. Keep the adversary read-only: it may
inspect code, tests, schemas, and configuration and may exercise the product, but it does not patch findings.
`commands/adversary.md` writes a trigger table into `adversary-log.md` before any spawn; finish the
selected seams, not the whole catalogue.

## Attack reachable seams

Load `resources/attack-catalogue.md` for concrete probes. Select only dimensions the slice actually has:
boundary parsing, authentication and authorization, tenancy, idempotency, concurrency, time, partial
failure, retries, data integrity, privacy, and operational visibility.

A finding must reproduce a violated promise through a reachable public or application boundary and state
the consequence. Calling a private helper with impossible state is not a product defect. “Input is not
validated” is incomplete until the report says what incorrect behaviour or exposure results.

## Triage before changing code

Classify each result:

- **Defect:** the system contradicts a decided promise. First add a failing test at the layer owning that
  behaviour, watch it fail for the reported reason, then fix it.
- **Specification gap:** behaviour is undefined. Record the product question; do not silently choose policy
  during the attack.
- **Declined risk:** the risk is understood and intentionally deferred. Record the reason and owner.

Regression tests belong with the behaviour they protect, not in a separate “hostile” architecture. A domain
rule is tested through its public domain or use-case API, an entry-point bypass at the edge, and an adapter
contract against the real boundary. Include `adversarial:` in the test name so `make adversarial` can select
it while `make test` continues to run it normally.

Record which attack dimensions were attempted or skipped, reproductions, resulting tests, open questions,
and declined risks. Then run mutation testing over the accumulated change and finish with `make verify`.

## Failure modes of the practice

- The author merely re-reviews the assumptions used to build the slice.
- The adversary fixes code, losing the failing evidence.
- Findings describe style or internals rather than reachable behaviour.
- Undefined behaviour is treated as permission to invent a requirement.
- The report lists findings but not what was attempted.
- The pass stops at the first defect rather than completing the selected seams.

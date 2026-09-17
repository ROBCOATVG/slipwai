---
name: adversarial-testing
description: Direct an independent agent to try to break a finished slice — hostile inputs, replays, interleavings, and authorisation paths nobody modelled — then turn every confirmed break into a permanent test at the level that owns it. Use at the end-of-phase PR-readiness gate, before mutation testing, and whenever asked to red-team, attack, fuzz, stress, or "try to break" a feature. For whether existing tests would notice a change to code you already wrote, see mutation-testing; for writing the tests themselves, see testing.
---

# Adversarial Testing

**Respect deployable boundaries.** Event-store, replay, stream, Decider, and projection probes apply to the
backend that owns those mechanisms. For a separate browser frontend, attack browser parsing, rendered
authorization states, stale server data, navigation, accessibility, and its published API boundary; do not
invent event-sourcing responsibilities for UI state.

Mutation testing asks whether your tests would notice a change to the code you wrote. Adversarial testing
asks a different question:

> **What did nobody think of?**

Both are end-of-phase gates and neither substitutes for the other. A slice can reach a mutation score of
100% while accepting a replayed command twice, because mutation testing only mutates code that exists. The
absent `if` is invisible to it. Finding the absent `if` needs something that reasons about the *contract*
rather than the implementation, and tries to violate it.

| | Mutation testing | Adversarial testing |
|---|---|---|
| Question | Would a test fail if this line changed? | Does the system hold against what nobody modelled? |
| Bounded by | The code that exists | Only the adversary's imagination |
| Finds | Weak assertions, one-sided branches | Missing behaviour, missing scenarios, wrong boundaries |
| Output | A score plus survivors | Confirmed breaks, spec gaps, declined risks |
| Verdict | Mechanical | Requires judgement about what the system promised |

**Deep-dive resources**, loaded on demand:

| Resource | Load when... |
|---|---|
| `resources/attack-catalogue.md` | Planning the attack matrix, or stuck for the next thing to try |

---

## Where this sits

```
FOR EACH TDD INCREMENT:
    └─► RED → GREEN → REFACTOR, no adversarial pass, no mutation harness

END-OF-PHASE PR-READINESS GATE:
    ├─► 1. ADVERSARIAL PASS      ── an independent adversary attacks the slice
    ├─► 2. TRIAGE + TDD          ── each confirmed break becomes a failing test, then a fix
    ├─► 3. MUTATION              ── over the accumulated scope, now including the new tests
    └─► 4. PR verification
```

Adversarial before mutation, deliberately. The pass adds tests and sometimes changes production code, and
mutation testing measures whatever exists when it runs. Reverse the order and you have measured a suite
you then modified.

Not inside the inner loop. During RED-GREEN-REFACTOR, hostile thinking belongs in the *choice of example*
— the same way `mutation-testing`'s mutator rules do — not in a separate attack session per increment.

**The pass is a step in producing the change, not a check in the pipeline.** Nothing in CI asserts that it
happened, and nothing should: an exploratory run is not deterministic and must not gate trunk. What enters
the pipeline is the tests it leaves behind, which are as deterministic as any other. That is the whole
point of converting every finding into a test — it is what lets a finding survive the session that found
it.

---

## Step 1 — Set the adversary up

**`/adversary` does this step.** The command in `commands/adversary.md` writes the trigger table into
`specs/<feature>/adversary-log.md` before any spawn — one line per surface, each `widened`, `already
covered`, or `not present` — then triages the seams the diff widened and spawns one adversary per selected
seam: the `drive-adversary` type in `agents/`, whose projection into your harness withholds the editing
tools rather than asking the delegate not to use them. Each brief carries the seam's contract plus an
explicit file manifest, so the delegate does not rediscover the repository. Read on to run the pass by
hand, or to know what the command is doing on your behalf — everything from Step 3 onward is yours either
way, because the command reports and stops.

**Independence is the mechanism.** An author attacking their own slice in the same session re-checks the
things they were already thinking about; that is why they missed the rest. Use a fresh session, or a
subagent, or a colleague — anything that has not spent the last hour deciding what this code should do.

Brief the adversary with the **contract**, not the implementation narrative:

- the slice's acceptance criteria and GWT scenarios;
- the external interface it exposes (route, payload schema, response shapes);
- the events it writes and reads, and the **stream identity** those events use;
- the invariants from the constitution that apply — commonly II (idempotency and replay), III (stream as
  the consistency boundary), IX (authorisation, tenancy, personal data);
- what the slice explicitly does *not* promise.

Then the instruction, in these terms: *try to make this system do something it promised not to do, or fail
to do something it promised.* Not "review this code" — a review produces opinions about structure, and
this pass is looking for behaviour.

**Keep the adversary read-only.** It reads source, tests, migrations and schemas freely; it does not edit
them. An adversary that patches what it finds produces a fix with no failing test in front of it, which
Principle V prohibits and which loses the only evidence that the break was real. Reproduction belongs to
the adversary; the fix belongs to the TDD cycle in Step 3.

**Time-box it.** An hour of agent attack on one slice is generous. Breadth first across the selected
seams, then depth on whatever felt soft. Stop when those seams have been probed, not when the catalogue
is exhausted.

---

## Step 2 — Attack

Work the seams, not the lines. `resources/attack-catalogue.md` is organised by the seams this
architecture actually has — replay, concurrency, stream identity, projection scoping, schema evolution,
boundary parsing, authorisation, time, partial failure, rebuild, personal data — with concrete probes for
each and the principle each one protects.

Two rules keep the output usable:

**Reproduce at a boundary the tests can reach.** A break demonstrated by calling an internal function with
a state the system cannot reach is not a break; it is a note about a private helper. Drive it through the
HTTP surface, or through a Decider fed by an event history the system could genuinely produce.

**Say what it costs.** A finding is a claim about consequence: money moves twice, a seat is held by two
people, one tenant reads another's data, the projection silently diverges. "This input is not validated"
is not a finding until you say what it does.

---

## Step 3 — Triage each finding

Three outcomes, and the difference matters more than the count.

**A defect** — the system contradicts something it promised.

1. Write the failing test **first**, at the level that owns the behaviour (Step 4).
2. Watch it fail, and fail for the stated reason.
3. Fix it.
4. Test and fix ship in the same commit.

That order is Principle V's bug-fix rule and it is not negotiable here, agent-found or not.

**A specification gap** — the system does something undefined, and nobody has decided what it should do.
This is the valuable category and the one most often mishandled. Do not decide it inside the adversarial
pass, and above all **do not invent an event name, an event field, or a stream identity to close it** —
those are permanent, and Principle XIV requires stopping to ask. Take it to `specification` or `find-gaps`
as a question, record it as a parked question, and carry on attacking.

**A declined risk** — real, understood, and out of scope for now. Write down why. An undocumented decline
is indistinguishable from an oversight three months later.

**Whatever the outcome, a claim about a dependency is verified or marked.** Triage turns on what a driver,
framework or runner does by default — which TLS mode a connector falls back to, whether a security library
prefixes a role, which reporter a test runner picks off a terminal — and the confident answer is the wrong one
often enough to have a rule: a triage row that states such a default cites where it was read — the jar
disassembled, the documentation at the pinned version, a test run against the real thing — or the row reads
*assumed*, and an assumed row closes no finding. One adoption recorded a connector as refusing a TLS mode that
is its silent default; another recorded a role prefix a library does not add. Both read as settled until
somebody opened the artefact.

---

## Step 4 — Turn a break into a permanent test

**The test lives at the level that owns the behaviour**, not in a separate hostile suite. This repository's
test projects are levels of scope, not categories of origin, and splitting by origin would leave you
running "the adversarial tests" as though the others were the friendly ones:

| The break is in… | The test goes in… |
|---|---|
| A Decider's rules — rejection, replay, ordering of prior events | `tests/domain/<context>.spec.ts` |
| A rule of the slice, reachable from its use case — an authorisation decision, an idempotent outcome | `tests/acceptance/<slice>.spec.ts` |
| **The outside surface itself** — status codes, auth headers, payload parsing, a route that bypasses the rule the use case enforces | `tests/edge/<surface>.spec.ts` |
| A projection's fold — collision, out-of-order event, rebuild divergence | `tests/projection/<view>.spec.ts` |
| An adapter's contract with the real thing | `tests/contract/<adapter>.spec.ts` |

**The attack always comes from outside; the regression test goes where the behaviour lives.** Those are
different questions and conflating them is how a red-team finding ends up with a test that would not have
caught it. You reproduce through the route, because that is where an attacker stands and reachability is
half the finding. Then you ask what actually broke:

- the rule was wrong → it belongs to the Decider or the use case, and a test there fixes it everywhere;
- **the rule was right and the route got past it** → the test belongs at the edge, because a use-case test
  proves the rule holds and says nothing about whether the surface can be made to skip it.

Constitution V puts a slice's *acceptance gate* at the use case so its scenarios survive an adapter swap.
That is about where a criterion is proved. It is not a claim that the outside surface is unimportant, and
it does not apply to this pass.

**Name it so it can be found again.** The describe block carries the marker `adversarial:` followed by the
attack, in the vocabulary of the attack rather than of the fix:

```ts
describe('adversarial: the same idempotency key replayed after a version conflict', () => {
  it('returns the original result and appends nothing', async () => {
    // ...
  });
});
```

`make adversarial` re-runs exactly these — every test whose full name matches `adversarial:`, across every
project — which is what you want while working through a batch of findings. They also run inside
`make test` like everything else, because after the fix they are ordinary regression tests. When a slice's
hostile scenarios reach the acceptance level, `make adversarial` needs Postgres up, the same as
`make test`.

The marker is case-sensitive and includes the colon. `tests/tooling/adversarial-config.spec.ts` fails the
build on a hostile test the marker cannot match, because a test that `make adversarial` silently skips is
worse than no convention at all.

**Assert the consequence, not the patch.** The test should fail against the original code for the reason
the adversary reported, and keep failing if the fix is reimplemented differently. A test that asserts the
new guard clause's error string protects an implementation detail.

---

## Step 5 — Record the attempt

**"We attacked it and found nothing" is unfalsifiable unless you say what you tried.** A pass that
reports only its findings cannot be told apart from a pass that barely happened, and the second one is
what happens under deadline pressure.

Record with the change — in the slice's plan artifact or the PR body:

- which seams from the catalogue were probed, and which were skipped with the reason;
- each confirmed break, with its reproduction and the test that now covers it;
- each specification gap raised, and where it went;
- each declined risk, and why;
- who or what ran the pass, and how long it had.

Then run `make mutation` over the accumulated scope, survivors included, and proceed to PR verification.

---

## What makes a pass fake

- **The author attacking their own slice in the session that wrote it.** The most common failure and the
  hardest to see from inside.
- **The adversary fixing what it finds.** No failing test, no evidence, and a fix aimed at the symptom.
- **Findings the compiler already rejects.** "It breaks if you pass a string" is not a finding where the
  type system makes it unrepresentable — Principle V says so explicitly. Attack behaviour, not shapes.
- **A log of findings with no log of attempts.** See Step 5.
- **Treating undefined behaviour as a defect.** If nobody decided, the output is a question, not a fix.
- **Reproductions through internals.** If the system cannot reach that state, neither can an attacker.
- **Stopping at the first break.** The first one is the cheapest. Finish the selected seams, not the
  whole catalogue.
- **Running it once, at the end, forever.** Each new slice that touches a shared stream, projection, or
  authorisation path re-opens seams the last pass cleared.

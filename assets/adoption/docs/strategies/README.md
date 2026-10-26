# Strategy playbooks

`docs/change-strategy.md` says how to choose; these say what follows once the choice is
made, because **the decided strategy informs everything done during the adoption**: where a new feature is
built, what the spec and the mock-ups show, what the gate refuses, and in what order the programme's steps come.

The strategy ADR records three separate decisions:

1. **Strategy** — how the change happens. One of four, each with its playbook below.
2. **Where the new home lives** — for the two strategies that build one: the strangler fig grows it `inside`
   (new modules in the same deployable, the seam in code) or `beside` (a new deployable, the seam at the
   network); a rewrite builds it `beside` or in a `new-repo`.
3. **Target shape** — what the system becomes, whichever way it gets there: modules (in one deployable, or as
   services) and the layering inside each (hexagonal, or as it is). [Target shape](target-shape.md) says how it
   is recorded, enforced and reached under each strategy.

**First under every strategy: [the build floor](build-floor.md)** — each deployable builds from a clean clone,
through one declared build, with every dependency and tool version written down. The strategy decides only how
far: in place and a strangler fig with its new home `inside` bring the old toolset fully up to date and raise the
target as high as the code allows, because new work is built with it; a rewrite and a strangler fig `beside` pin
the old build exactly as it is, because it is being replaced, and the new system arrives pinned.

Two of the four replace code, and they differ in two independent ways: **how traffic moves** to the new code
(one capability at a time through a seam, both systems live; or all at once, in one rehearsed cut-over) and
**how much moves** (everything, the old app deleted; or only what needs to change).

| | One capability at a time | All at once |
|---|---|---|
| **Everything moves** | Strangler fig, `End: all` — the incremental rewrite, and the recommended way to replace a system on a new stack | Rewrite |
| **Only what needs to change** | Strangler fig, `End: partial` | — |

| Strategy | Where a new feature goes | What has to exist before the first feature |
|---|---|---|
| [Leave it](leave-it.md) | The old system, under a bar (small, additive, no new way in, a signed risk paragraph); bigger requests are redirected | A risk owner, a review date, accepted risks each with a compensating control, the security floor scheduled |
| [In place](in-place.md) | The old system, *fenced* where an upgrade due soon would rewrite it, and into a module once the target's modules are declared; security upgrades first | The run proven (`smoke`), characterisation, a data baseline, and the security rungs |
| [Strangler fig](strangler-fig.md) | The new home — a new module `inside`, or a new deployable `beside` — reaching old pages through the seam (`Visibility: page \| seam`) | A freeze; the seam in place, passing everything to the old code; the new home created, in the gate, and routed; under `End: all`, the behaviour to keep (`docs/parity.md`) and a checkpoint |
| [Rewrite](rewrite.md) | The new system, never the old one; it waits for the cut-over, or reaches people through a recorded seam (`Visibility: cut-over \| seam`) | A freeze; the whole system's behaviour to keep (`docs/parity.md`) pinned against both; the new system generated in the target shape; the ADR's case for one cut-over over a strangler fig with `End: all` |

Every playbook has the same eight sections: what it is, and when it is right or wrong; what the ADR records;
the phases, each step with who does it, the evidence it is done and what it unblocks, ending at a finish line;
how a feature request is handled; how the method carries it; anti-patterns; a worked example; sources.
Section 5, how the method carries it, says what the board, the draft, the specification, the gate and the
programme do under that strategy, and closes with what is not built yet. `modular-monolith` is no longer a
strategy: an ADR that names it reads as a strangler fig whose new home is `inside`, target modules in one
deployable. Section 7 of each walks through an invented worked example: a small internal web app on an
end-of-life runtime, with no tests.

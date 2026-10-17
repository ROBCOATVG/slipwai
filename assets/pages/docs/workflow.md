# Delivery workflow

<!-- section: event-diagram -->
```mermaid
flowchart LR
  C["/speckit-constitution · principles<br/>make check-constitution gates the coverage"]
  S["/speckit-specify · whole product"]
  Q["/speckit-clarify · answers back into spec.md"]
  CK["/speckit-checklist · checklists/"]
  GS["find-gaps survey · read-only"]
  G["/gaps conversation · confirmed answers into spec.md"]
  EMOD(["event-modeling · events, commands, read models, actors"])
  SS["/story-splitting · slices"]

  subgraph loop["once per slice — /sail owns the loop, repeating until the split is exhausted"]
    direction TB
    EM["/example-map · rules → examples → GWT"]
    EG["/gaps · tighten examples.md, on paper"]
    P["/speckit-plan · one slice"]
    T["/speckit-tasks · one slice"]
    AN["/speckit-analyze · spec, plan and tasks agree"]
    I["/speckit-implement · RED → GREEN → REFACTOR"]
    EX["examples proven · a test per example"]
    R["review · the slice's own diff, and nothing beside it"]
    TR["/adversary · the trigger record, attacking nothing"]
    MG["merge to trunk"]
    EM --> EG --> P --> T --> AN --> I --> EX --> R --> TR --> MG
  end

  subgraph gates["once per capability — when its last slice has merged"]
    direction TB
    CV{"/speckit-converge · the capability's whole diff against the spec"}
    FS["follow-up slice · what converge or a gate found above the bar"]
    DG["/gaps · promise → test → production path"]
    DR["design review · screenshots of every screen it changed"]
    A["/adversary · one pass, only where a slice widened a trigger"]
    M["/mutation · measure the suite"]
    H["the hand's walk · every example, in the running app"]
    D{"demo · a person, the whole capability"}
    CV -->|"appends tasks"| FS --> CV
    CV -->|"converged"| DG --> DR --> A --> M --> H --> D
  end

  MG -->|"the capability's last slice"| CV
  D -.->|"feedback changes behaviour"| EM
  D -.->|"feedback changes implementation"| FS

  C --> S --> Q
  Q --> CK --> G
  Q --> GS --> G
  G --> EMOD --> SS --> EM

  G -.->|"gap found"| S
  EM -.->|"map reveals more than one slice"| SS
  P -.->|"title still says 'and'"| SS
  MG -.->|"next ready slice"| EM
  EM -.->|"an event has no name"| EMOD
  D -.->|"feedback changes slice"| SS
  D -.->|"feedback changes event contract"| EMOD
  D -.->|"feedback changes product scope"| S
```
<!-- end section -->
<!-- section: plain-diagram -->
```mermaid
flowchart LR
  C["/speckit-constitution · principles<br/>make check-constitution gates the coverage"]
  S["/speckit-specify · whole product"]
  Q["/speckit-clarify · answers back into spec.md"]
  CK["/speckit-checklist · checklists/"]
  GS["find-gaps survey · read-only"]
  G["/gaps conversation · confirmed answers into spec.md"]
  SS["/story-splitting · slices"]

  subgraph loop["once per slice — /sail owns the loop, repeating until the split is exhausted"]
    direction TB
    SG["/gaps · tighten the slice's criteria, on paper"]
    P["/speckit-plan · one slice"]
    T["/speckit-tasks · one slice"]
    AN["/speckit-analyze · spec, plan and tasks agree"]
    I["/speckit-implement · RED → GREEN → REFACTOR"]
    EX["examples proven · a test per example"]
    R["review · the slice's own diff, and nothing beside it"]
    TR["/adversary · the trigger record, attacking nothing"]
    MG["merge to trunk"]
    SG --> P --> T --> AN --> I --> EX --> R --> TR --> MG
  end

  subgraph gates["once per capability — when its last slice has merged"]
    direction TB
    CV{"/speckit-converge · the capability's whole diff against the spec"}
    FS["follow-up slice · what converge or a gate found above the bar"]
    DG["/gaps · promise → test → production path"]
    DR["design review · screenshots of every screen it changed"]
    A["/adversary · one pass, only where a slice widened a trigger"]
    M["/mutation · measure the suite"]
    H["the hand's walk · every example, in the running app"]
    D{"demo · a person, the whole capability"}
    CV -->|"appends tasks"| FS --> CV
    CV -->|"converged"| DG --> DR --> A --> M --> H --> D
  end

  MG -->|"the capability's last slice"| CV
  D -.->|"feedback changes implementation"| FS

  C --> S --> Q
  Q --> CK --> G
  Q --> GS --> G
  G --> SS --> SG

  G -.->|"gap found"| S
  P -.->|"title still says 'and'"| SS
  MG -.->|"next ready slice"| SG
  D -.->|"feedback changes slice"| SS
  D -.->|"feedback changes behaviour"| S
```
<!-- end section -->

For one small vertical slice:

1. {{discovery}}.
2. On the specification, run `/speckit-clarify`. Against that clarified snapshot, run
   `/speckit-checklist` and the read-only find-gaps survey in parallel. When both return, run the find-gaps
   conversation on the host, using both outputs and writing confirmed answers back while a missing state
   is still a paper edit. On a slice's example map or its own criteria, `/gaps` is the whole pass.
3. Create or resume `plan.md` and `tasks.md` with the Spec Kit commands installed by `./init`.
4. Run `/speckit-analyze` over `spec.md`, `plan.md` and `tasks.md`. It writes nothing. A finding goes back
   to the plan or the tasks; a clean reading is what lets implementation start.
5. Implement each task RED-GREEN-REFACTOR, keeping `make verify` green.
6. Prove every example in the slice's `examples.md` with a passing test.
7. Review the slice's diff against its merge base once — only what it added or changed.
8. Run `/adversary` for the slice's trigger record — which attack-surface triggers it widened, attacking
   nothing — then `make verify`, and merge.
9. Once a capability's last slice has merged, run its gates once: converge over its diff, `/gaps`, the design
   review from screenshots, one adversary pass where any slice widened a trigger, `/mutation`, and the hand's
   walk of every example. Then the person's demo. Under the `open` release mode converge, the gaps trace, the
   design review and the walk run per slice as well, after step 5, and a slice that widened authorisation,
   identity or money is attacked before its push; the capability's converge, adversary pass and mutation
   still run.

The principles stage has a gate of its own. `.specify/memory/constitution.md` is what every stage after it
treats as the authority, so `make check-constitution` fails the build when that file stops carrying minimum
CD, the practices the skills in `skills/` teach, or the obligations this project's capabilities claim — and
`.specify/extensions.yml` hooks `/speckit-constitution` on both sides so the drafting session sees the
required coverage before writing and the check runs immediately after. `/constitution-coverage` prints the
normative text at any time. Until that stage has been started the gate stands aside: `./init` installs the
template, and the untouched template passes, so the walking skeleton reaches `main` — and production, where
there is a target — before the first principle is written. It applies from the first edit, and from the first
feature under `specs/` whether or not the constitution was touched.

**Analyze** is the read between tasks and implementation. It compares `spec.md`, `plan.md` and `tasks.md`
and writes nothing, so a plan that has drifted is caught before any code. It is not either `/gaps` pass:
the one before planning tightens a single artifact, and the capability's one after converge traces a promise
to a test and a path.

Three stages in the loop are deliberately not the shape they look like. **Converge** runs once per
capability, not per slice: it asks whether the code does what the specification requires, and that has its
answer only once the slices sharing a requirement are all built. It is append-only — its only write is new
tasks — so it is safe to repeat until it reports converged or reaches its bound. The **second `/gaps`** runs
after it, once per capability, because ahead of converge every unbuilt task reads as a gap, and slice by
slice a promise two slices keep between them reads as one neither kept. **`/adversary`** attacks nothing per
slice: each slice records its trigger table in `specs/<feature>/adversary-log.md`, and the capability is
attacked once, only where one of those tables has a trigger `widened` — which is what lets a capability
decline on evidence instead of judgement. **`/mutation`** runs once per capability — when its last
slice has merged, before the person is shown it, bounded by its budget and leaving a qualified receipt rather
than a score when capped — and when both run adversary goes first, since it
adds tests and mutation measures whatever exists when it runs.

`/sail` owns resumption and sequencing, and is safe to call at any point on this diagram: it enters at the
first stage still owing an artifact, stepping back out of the loop when an upstream stage has not been done.
Demo feedback returns to the stage that owns the change before the path is demonstrated again. A real product decision is a stop; finishing an intermediate document is
not.

`/cruise` runs this same diagram with nobody at the wheel. A product decision is answered by `sail-decide-skipper`
and written in `specs/<feature>/decisions.md`; the hand's walk is run by `sail-demo-hand` and written in the
capability's `demo-log.md`; the run ends only when the specification is satisfied, or when a person stops it. What each
stage produces does not change. `commands/cruise.md` is exact.

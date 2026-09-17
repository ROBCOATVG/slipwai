# Writing your first slice

What a slice looks like on disk, where its artifacts live, and the four things that cost real debugging to
learn.

- [The files a slice touches](#the-files-a-slice-touches)
- [Where a slice's artifacts live](#where-a-slices-artifacts-live)
- [Four things worth internalising](#four-things-worth-internalising)

## The files a slice touches

```
specs/<feature>/slices/<id>/examples.md   # rules → examples → GWT. FIRST, by /example-map then /gaps
docs/event-model/mockups/<screen>-*.html  # one per state of the white box — the mocks, or what you designed
src/domain/<context>/events.ts            # zod schemas + registry; createEventParser over it
src/domain/<context>/decider.ts           # initialState, evolve, decide — pure, no I/O
src/application/usecases/<x>.ts           # load, fold, decide, append with expected version, re-decide on conflict
src/adapters/driving/http/...             # parse, delegate, map outcomes to statuses
<the frontend>/<Screen>.tsx               # THE WHITE BOX — the surface the actor uses. Same slice, same PR
src/adapters/driven/<provider>/...        # only if the slice integrates: provider types stop here
tests/acceptance/<x>.spec.ts              # boundary GWT through the use case — the gate. Titles cite AC- ids
tests/edge/<surface>.spec.ts              # the route itself: parse, delegate, map outcomes to statuses
<the frontend>/<Screen>.spec.tsx          # each state of the screen, at the project's UI level
tests/domain/<context>.spec.ts            # rules unreachable from the boundary — CS- ids
tests/integration/<provider>.spec.ts      # that adapter vs a stub: error mapping, retry, timeout
```

**The two frontend lines are the ones that get skipped**, and skipping them is why a slice can model a
screen, pass every gate, and ship with no user interface. A white box is not a label on the route beneath
it — it is the surface the actor uses, it belongs to the slice that models it rather than to a later UI
slice, and it is built even when what it submits to is not wired up yet. `check-model` refuses an
`implemented` slice whose white box appears nowhere in the source (`screen-is-built`) or records none of the
states it renders (`screen-states-recorded`). The path is written `<the frontend>` because this template
ships no frontend and does not pick one for you; the plan states where it lives, and `code` names the files.

Every one of those files corresponds to something in the model, and
[`event-modeling-to-code.md`](event-modeling-to-code.md) is the mapping — which box becomes which file, what
`stream` and `folds` turn into, and which test level proves what.
[`tests/README.md`](../tests/README.md) is the other half of that question: which level owns a rule, and why
a fat `domain` suite is a symptom.

## Where a slice's artifacts live

One feature directory holds many slices over time, and three kinds of artifact age differently. **This bites
at the second slice, not the first**: the installed Spec Kit plan and tasks commands resolve to
`specs/<feature>/plan.md`, so that path has to describe the slice in flight — but a *file* there, overwritten
by the next slice, destroys the only record of why the last slice looks the way it does, including its
Complexity / Deviation list and whatever its stubs turned out to be. So the path is a link into the slice's
own directory, made by `/drive` before the plan command runs, and two slices planned at once never meet
there at all.

| Artifact | Lifetime | Where |
|---|---|---|
| `spec.md`, `story-split.md`, `checklists/` | feature-scoped | the feature directory, amended in place |
| `contracts/` | cumulative | the feature directory. The HTTP surface, event schemas and ports belong to the *system*, not one slice; each slice amends them and marks what it changed |
| `adversary-log.md` | cumulative | the feature directory. One row per slice: trigger table (`widened` / `already covered` / `not present`), spawned seams (type, model, manifest), omitted seams with why, findings *including no findings*. A slice declines an adversarial pass by citing rows here, so an unwritten row is a pass that has to be run again |
| `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md` | slice-scoped | `slices/<id>/` from the day it is planned. The canonical paths the Spec Kit commands resolve to are links into it, ignored by git and never committed |
| `slices/<id>/examples.md` | slice-scoped | `slices/<id>/` from the day it is mapped. No command resolves to it — `gwt` names it by path — so it never needs the canonical slot, and slices can be mapped ahead without colliding |
| `slices/README.md` | cumulative | the register: one row per slice, written when the slice is accepted. Where there is no event model it is what says a slice is done; with one, `status: implemented` says it |

So the canonical paths always point at the slice being planned or built, and `slices/<id>/` holds a slice's
whole record from the day it is mapped.

**Finishing a slice marks it done rather than moving it**: `status: implemented` in the model on the event
profile, a row in `slices/README.md`'s register otherwise — the board's ✅ *Works now* and `/drive`'s ready
set both read that mark, and a slice with a `plan.md` under `slices/<id>/` and no mark is in flight. The
register carrying this table is worth the ten lines on either profile: the next slice should not have to
re-derive the convention. A regular file still at a canonical path — a harness that replaced the link — is
moved under `slices/<id>/` before the mark is written; `make check-slice-scope` refuses one left behind.

The demo is a feedback stage, not a presentation ceremony. Feedback returns to the delivery stage that owns
it and the revised path is demonstrated again. After the demo is accepted with no unresolved feedback,
finishing means mutation evidence, `make verify`, and the mark — `implemented` in the model, or the register
row — plus an adversarial pass first, when this slice changed attack surface or closed the split.
`commands/adversary.md` decides that against `adversary-log.md` and writes the row either way, so the
decision is never a judgement made twice. The agent then reads the **ready** set from `story-split.md`
(every slice not done whose `depends_on` are all done) and continues automatically: every unclaimed ready
slice whose contract is settled runs concurrently, one delegate per slice on a `slice/<id>` branch in its
own worktree, merged back in split order — `commands/drive.md`, *Running ready slices concurrently*; a
harness that cannot delegate takes the earliest in split order and names the rest. Choosing among an
already-computed ready set is not a new product decision.

Nothing is deleted. A shipped slice's research is the only explanation of why the code looks the way it does,
and *"it's in the git history"* is not a place anybody looks.

A slice-scoped decision stays in that slice's `research.md` — but when one turns out to outlive its slice,
promote it to an ADR. Stream identity recorded as `D-1` in a shipped slice's research is the failure
[`adr/0001`](adr/0001-record-architecture-decisions.md) exists to prevent.

## Four things worth internalising

Each of these cost real debugging to learn.

**A version conflict is a return value, not an exception.** Contention is expected under load. The use case
rehydrates and re-decides; nothing throws.

**Scope every projection to its own streams.** A fold over the whole log breaks the first time an unrelated
stream exists whose event type name collides.

**Never reach for the connection pool while holding a connection.** Under contention every in-flight write
holds one and waits for another, and the pool deadlocks.

**`REVOKE` does not make a table append-only** when the application role owns it — a Postgres owner keeps its
privileges. `002_events_append_only.js` uses a statement-level trigger, which holds whatever the role.

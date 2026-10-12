# Repository guidance

Keep domain logic independent of adapters and make changes as small end-to-end slices.

## Two gates, not one

| When | What to run | Why |
|---|---|---|
| Every increment inside a slice | `make unit`, `make lint`, `make typecheck` | Seconds. Run them often enough that a break is one edit old |
| Once, before the merge to `main` | `make verify`, on the rebased branch | The whole of it, including the integration suites and the gates |

`make unit` is the fast half, and it stays fast because of where a test lives rather than because anybody
remembers. **A test that needs a real database, a real process or the network is exercising an adapter, so
it is an integration test**: it goes in the integration suite with the others, and `make unit` does not run
it. The domain and the use cases are tested behind their ports with fakes, which is what makes them quick,
and `make check-imports` is what keeps the three apart. A unit suite that creeps towards minutes is a
suite nobody runs per increment, and then the only gate anyone runs is the one before the merge — which is
version 1's single `make verify` back again, by a slower road.

Never edit a Spec Kit-managed file in place; override it by name from the preset layer under
`.specify/presets/`, because an in-place edit quietly turns every later `specify integration upgrade` into a
manual reconciliation — `make check-speckit` catches the drift either way.

`.specify/memory/constitution.md` is human-owned and human-amended. Never edit it to make a change pass and
never drop a principle to clear a gate: `make check-constitution` fails when it stops carrying minimum CD,
the practices the skills in `skills/` teach, or the obligations this profile's capabilities claim.
`/constitution-coverage` prints the required text; a finding that needs a decision nobody has made is a
question for the user, not an obligation to invent.

## Finding your way around this codebase

*Who calls this*, *where else is this symbol used*, and *what breaks if I change it* are answered by
following the call path, not by reading one file. Two skills in `skills/` ask for precisely that —
`debugging` says to search every caller before changing a shared function, and `refactoring` says to inspect
every caller and reachability path before removing a branch — and neither is satisfied by a text search,
which finds the spellings you thought to try and is silent about the rest.

If this file carries an extension block for a code index — one is elected at `./init`, and the block it
projects names where the index lives and the routes that reach it — that index is what answers those
questions, and asking it is the first move rather than the fallback. Each session follows the block's own
order of routes for itself. A fresh delegate does not inherit the parent's MCP connection, but where it has
the block's shell route it can query the same project index.

A block is not a promise that the index is reachable or current. The database travels with the checkout
and the tooling that serves it does not, and it is only maintained while a client is attached to it — so
follow the block's own detection step first, and where no tool answers, say that and use a text search:
an index you cannot query is an index you do not have. `make check-extensions` is what notices a database
its tooling has stopped writing to, which otherwise answers *nothing calls that* indistinguishably from
*nothing calls that yet*.

With no such block this project has no index and a text search is the tool. Either way, say which one you
used when you report what you found, so a review can tell an exhaustive answer from a lucky one.


## Delegated agents

Each stage `/sail` sends to a fresh context is a named type in `agents/` (and a whole slice is `sail-slice-watch`) carrying that stage's standing brief,
its model and its write scope, projected into the installed harness so it holds what it can. Delegate to the
type: a brief adds only its task-specific contract and file manifest, and restates neither the scope nor `docs/delegated-agent-safety.md` — a brief that restates a rule is one that can fall behind it.
## Deployable ownership

{{rules}}
<!-- section: continuation-standard -->

## Per-slice continuation contract

Use `/sail` to resume from the first missing artifact or unchecked task, whether that artifact is the
constitution, the product specification, the split, or the slice's own tasks. Work through specification,
`/gaps` over the slice's acceptance criteria, plan, tasks, RED-GREEN-REFACTOR implementation, the installed
Spec Kit converge command until it reports converged or reaches its bound, `/gaps` over the slice diff, and an actor-visible
demo. Pause at the demo for feedback; after acceptance run `/adversary` when the slice changed attack
surface or closed the split — `commands/adversary.md` makes and records that decision — then `/mutation` and
`make verify`. Stop earlier only for a product decision or unavailable external input.
<!-- end section -->
<!-- section: continuation-cruise -->

## Per-slice continuation contract

The loop starts when any per-slice command is invoked: `/sail`, `/example-map`, or the installed Spec Kit
plan, tasks, and implement commands. Naming one stage requests that stage and what follows it. A
stage's own done condition is stage completion, not permission to end the delivery loop, and an optional
extension hook is not a gate.

Continue until the actor-visible path is ready for a demo, a product decision or unavailable external input
blocks progress, or the ordered split is exhausted. Before the demo, run the installed Spec Kit converge
command until it reports converged or reaches its bound, and `/gaps` over the slice diff. At the demo, pause for feedback. On
acceptance, harden and finish the slice — `/adversary` when the slice changed attack surface or closed the
split, then `/mutation` and `make verify` — then continue to the ready slices (not done, every `depends_on` done): every unclaimed one whose contract is settled runs concurrently, one delegate per slice on a `slice/<id>` branch, merged in split order (`commands/sail.md`, *Running ready slices concurrently*); where the harness cannot delegate, the earliest in split order, naming the rest.

Under `/cruise` the same contract holds with nobody at the wheel: the two stops that were a person's — a
product decision and the demo — are answered by `sail-decide-skipper` and `sail-demo-hand`, every answer is written where
a person's would have been and again in `specs/<feature>/decisions.md`, and an iteration ends with one line
(`cruise: continue | done | parked: <why> | stopped: human`) that the outer loop reads before it invokes the
next. `commands/cruise.md` is exact; it runs `commands/sail.md` and adds nothing to what a stage produces.

`commands/sail.md` is the resumable entry point at any point in the workflow. It derives the current stage
from artifacts and never re-runs a completed stage merely to make sure. Invoked before the upstream stages
exist — no ratified constitution, no specification, no modelled events, no split — it steps back to the
earliest stage still owing an artifact instead of improvising one. If it conflicts with this file, this
file wins.
<!-- end section -->

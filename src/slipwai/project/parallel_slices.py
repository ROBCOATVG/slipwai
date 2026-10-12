"""The tail of `commands/sail.md`: which slices may start now, and how one session runs several at once.

Ready-set selection used to end with "one slice per session; name the rest so another session can claim a
sibling" — the parallelism the method promises (slices that share only an event schema are independent, and
Principle V makes it true in the tests) exploited only by running `/sail` twice. Once the contract is
settled a session can run every ready slice at once, one delegate per slice, and the reference
implementations — Nebulit's build kits, Dilger's Ralph loop — show the three things that have to be true
for that to work: a claim, so two drivers never take the same slice; a written shared-surface rule, held
at the gate; and one slice per delegate, strictly sequential inside it. This module is those rules as
the driver reads them. What "done" means changed with it: a slice's plan and tasks live under
`slices/<id>/` from the day they are written, so their being there no longer says the slice shipped — the
model's `status` does on the event profile, and the register at `slices/README.md` does otherwise.
"""
from __future__ import annotations

from ..layout import AT_ROOT, Layout


def done_marker(event: bool) -> str:
    """What says a slice is finished, per profile — read by the ready set, the board and Phase 4 alike."""
    if event:
        return "`status: implemented` in `docs/event-model/model.yaml`"
    return "a row in the register at `specs/<feature>/slices/README.md`"


def contract_precondition(event: bool) -> str:
    """When a ready slice may run alongside a sibling: it has clearance.

    This replaced version 1's "its own contract is settled", which a slice could only answer about itself —
    so nothing said what a slice was *waiting for*, and a fresh fairway serialised behind a host example map
    per slice. Issue #32.
    """
    return """**It has clearance.** A ready slice runs alongside its siblings when every mark it steers by has
been set, and a mark is set when some slice wrote a `mark-set` line for it at its own first stage, in its
own worktree. So a sibling unblocks this slice by having **planned**, not by having merged — if a merge
were the signal, every fairway would wait on every other one, which is what version 1 did.

Ask, never assume:

```sh
python3 scripts/agents/clearance.py           # every slice that may start now
python3 scripts/agents/clearance.py <id>      # whether that one may, and what it waits on
```

It reads `specs/<feature>/chart.yaml` for what each slice sets and steers by, and the deck logs for the
`mark-set` lines. **Never a status field**: in the first attempt `model.yaml` said `planned` for eight
slices that were built and merged, because the field was written at plan time and never reconciled. A log
line is written by the thing that did the work at the moment it did it.

A slice with no clearance is not a stop — it is a slice whose turn has not come. Name what it waits on and
take a cleared one. A mark the chart declares that *no slice sets* is a different thing and is a stop for
the host: `make check-chart` refuses that chart, and the sentence clearance prints says so."""


def ready_set_selection(event: bool) -> str:
    """The numbered rules that turn the slice graph into this session's next move."""
    graph = (
        "each slice's `depends_on` in\n   `docs/event-model/model.yaml`, or `## Slice graph` in the split"
        if event
        else "`## Slice graph` in the split"
    )
    return f"""**Ready-set selection** (which slices may start now, and whether this session takes one or all of them):

1. Read the slice graph — {graph} — and which slices are **done**:
   {done_marker(event)}. A slice with `plan.md` under `slices/<id>/` and no such mark is in
   flight, not done.
2. An open `CRITICAL` in `specs/<feature>/adversary-log.md` is the next slice, ahead of every ready
   product or method slice.
3. Otherwise **ready** = not done, every `depends_on` done.
4. If ready is empty, stop — the split is exhausted or every remaining slice is blocked.
5. If ready has one slice, claim it and take it.
6. If ready has several, **name the full ready set**, split into *claimed* and *unclaimed* by the
   forge's `slice/<id>` branches, and run every unclaimed one whose contract is settled concurrently, as
   *Running ready slices concurrently* says. Where the harness cannot delegate, claim the earliest in the
   ordered split for this session and leave the rest named, so another session can claim a sibling. Do not
   stop merely to choose among them unless the user asks.
7. **A fairway narrows all of the above.** Given one — `fairway=<name>` in this command's argument — ready is
   that fairway's slices and no other; the rest of the ready set is named as *another fairway's* and left.
   Given none, take the ready slices of every fairway nobody holds, and leave a fairway whose `held_by` names
   somebody else to them, naming its slices as *held*. *Fairways* below says where a slice's fairway is read
   from."""


def concurrent_slices(event: bool, layout: Layout = AT_ROOT) -> str:
    """The `### Running ready slices concurrently` section: precondition, claim, fan-out, rule, merge order."""
    contract = (
        "Slices that share an event schema are independent: the schema is the contract between them, and\n"
        "Principle V — seed from synthetic events — is what makes that true in the tests."
        if event
        else "Slices that share only a written contract — a route, a schema, a port — are independent: neither\n"
        "has to be built first, and each is tested against the contract rather than against the other."
    )
    return f"""### Running ready slices concurrently

{contract}
So one session need not take one slice at a time. Fan out over the ready set when, and only when, the
four things below hold; the reference implementations of this method parallelise exactly this way, and
these are the primitives they add.

{contract_precondition(event)}

**Each slice is claimed.** A claim is a `slice/<id>` branch on the forge — nothing in the model changes,
so `check-model` learns nothing new. Claim by pushing the branch and expecting it not to exist:

```sh
git push --force-with-lease=refs/heads/slice/<id>: origin HEAD:refs/heads/slice/<id>
```

Rejected means another session got there first: skip to the next unclaimed ready slice, never retry,
never error. Read the claims back with `git ls-remote --heads origin 'slice/*'`; the board shows 🔀
*Ready* split into *claimed by* and *unclaimed*. A claim whose last commit is days old is reported as
stale, never silently taken — its owner may be mid-slice. Without a remote, the local branch is the claim,
and say so. A remote that is configured and cannot be reached is the other case, and it looks like success:
`ls-remote` fails, every slice reads as unclaimed, and that is exactly the answer that lets two sessions take
one slice. A failed read is reported as *claims could not be read*, never as *unclaimed*, and no slice is
claimed on the strength of it.

**Each slice has its own worktree and one delegate.** For every unclaimed ready slice whose contract is
settled, in the same turn: claim it, give it a worktree (`git worktree add ../<project>-<id> slice/<id>`;
on Claude Code the Agent tool's `isolation: worktree` makes one), and delegate the slice's ladder — its
example map through its converged verdict — to one fresh `sail-slice-watch` delegate (`agents/sail-slice-watch.md`,
the standing brief) with a manifest naming the worktree, the slice's block of the model, its `examples.md`,
and the shared-surface rule below. That type takes no stage's model, because *Who runs each stage* still
chooses one stage by stage inside the delegate, where `[P]` tasks still fan out to `sail-implement-shipwright`: the
two levels nest. Inside one slice the stages stay strictly sequential. A delegate that meets a
product question stops its slice with the question recorded in its `plan.md` and hands it here — a blocked
slice is marked blocked, never guessed past.

**The shared-surface rule**, which the delegates cannot infer and `{layout.make} check-slice-scope` holds on
every `slice/<id>` branch: a slice's commits touch its own `specs/<feature>/slices/<id>/`, the feature's
cumulative artifacts (`spec.md`, `story-split.md`, `contracts/`, `checklists/`, `adversary-log.md`, and
`decisions.md`, where `/cruise` records a decision taken during the slice), its own block of `model.yaml`
with the committed canvas `model.drawio` regenerated from it (`{layout.make} model-drawio` — `check-drawio`
holds the canvas to the model, so a slice that advanced its block cannot pass `verify` without it), the
mockups, the code and tests of the service that owns it — one bounded context where the service holds
several — the context's events module *additively*, **new** migration files named by a timestamp
(`date -u +%Y%m%d%H%M`, so two slices never mint the same name), a **new** ADR under `docs/adr/` at
`Proposed` (never an edit to one that stands), and the composition root. Nothing else —
`Makefile`, `project.json`, package manifests and locks, `scripts/`, `skills/`, `agents/`, the other docs —
is a slice's to write: a delegate that needs one of them hands the need back here, and it lands on `main`
before the fan-out or between merges. The canonical slot at the feature root is a link, never committed.

**Demo on the slice branch, then verify, then push.** As delegates report converged, demo each slice from
its unpushed worktree in split order — never from `main`, never by pushing increment commits first. A
claim may already have pushed a lock ref from `main`; leave the increment commits local until the actor
accepts. After acceptance: bring the code index up to the tree if the project has adopted one, `{layout.make} verify`
green, then push the slice's commits and merge into `main` in split order — never in finishing order.
That is the first implementation push, and it is what starts CI. The composition root and the cumulative
artifacts are where two merges meet, and split order is what makes those resolutions predictable;
regenerate the Mermaid diagrams (`{layout.make} model`) after a merge, never in a branch, and the canvas
(`{layout.make} model-drawio`) after each merge as well, taking both sides' blocks. No slice's Phase 4 runs until its demo is
accepted, and a sibling's demo never waits on another's Phase 4. Phase 4 itself — adversary, mutation,
`{layout.make} verify`, marking the slice done — runs here, on `main`, one slice at a time. Delete the
`slice/<id>` branch once its Phase 4 clears: the claim is spent.

**Where the harness cannot delegate**, run one slice at a time here — claim the earliest in split order,
name the rest — and say so in the line that says which model ran (`harness cannot delegate`).

{fairways(layout)}"""


def fairways(layout: Layout = AT_ROOT) -> str:
    """The `### Fairways` section: what one is, where it is read from, who holds it, and how its merges stop
    waiting on another's.

    Version 1 called this a workstream and read it from a column somebody typed into the split. The chart
    already says it — one entry per fairway, with the paths it owns — and a second field to keep in step
    with the first is a field that goes stale. So this reads the chart, on both profiles.
    """
    return f"""### Fairways

A **fairway** is one bounded context's slices, in split order, held by one at a time: a person, a `/sail`
session, a captain on another machine. Two fairways share nothing but **marks** — the contracts one sets and
another steers by — so a slice in one merges and demos without waiting on a slice in another, and a second
person or machine joins the work by taking a fairway rather than by racing for the next slice in one list. A
project with one context has one fairway, and nothing in this section changes for it.

**The chart names them, and nothing else does.** `specs/<feature>/chart.yaml`'s `fairways` block has one
entry per fairway — its context, its service, and the paths it owns — and each slice's entry names the
fairway it belongs to. `/chart` writes that on the standard profile and `{layout.make} chart` renders it from
the model on the event profile. The split's `## Fairways` table is **read from the chart**, never typed
beside it: a second place to say which fairway a slice is in is a second place for it to be wrong, and the
one that is wrong is always the one somebody typed. A slice whose work straddles two contexts is two slices,
or a boundary question for the chart, and never one slice in two fairways.

**A session takes one fairway, or every free one.** `/sail fairway=<name>` confines the ready set to that
fairway. Given none, a session takes the ready slices of every fairway nobody holds. `held_by` in the split's
table is routing, not a lock: whoever is named there gets that fairway's slices left alone, and the board
shows them as held; the claim is still the `slice/<id>` branch, so two sessions on one fairway are two claims
and the mutex holds. **The column is rendered from `refs/slipwai/claims/<fairway>` and nothing writes it by
hand** — a name typed into the row does not survive the next `make decisions` and `make check-rendered`
refuses it. A person takes a fairway the way a captain does: `python3 scripts/agents/claims.py --take
<fairway>`, which is a push a second taker cannot win, and `--release` gives it back.

**Merges are ordered within a fairway and not across.** Inside one, merge in split order as *Running ready
slices concurrently* says. Across fairways, merge as each is accepted, whichever finished first. The
composition root and the cumulative artifacts are where two merges meet and the second takes both sides; the
events module grows additively for exactly that reason, because the merge of two additions is a union. A
real conflict in a mark is a contract change: stop both fairways for the host, never resolve it in a branch.
A fairway's release flag is its own, and `check-slice-scope` refuses a branch that touches a path another
fairway owns, so the boundary is held rather than remembered. The board's lines are grouped by fairway where
there is more than one, each with its own `N of M` and its `held_by`."""

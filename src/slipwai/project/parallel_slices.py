"""The tail of `commands/drive.md`: which slices may start now, and how one session runs several at once.

Ready-set selection used to end with "one slice per session; name the rest so another session can claim a
sibling" — the parallelism the method promises (slices that share only an event schema are independent, and
Principle V makes it true in the tests) exploited only by running `/drive` twice. Once the contract is
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
    """When a ready slice may run alongside a sibling: the contract it shares with them is settled."""
    if event:
        return """**The contract is settled.** A ready slice runs alongside its siblings only when its `status` in
`model.yaml` is `planned`: its events carry `attributes`, its append is guarded by a named `stream` or
`guard`, and `gwt` points at an `examples.md` that exists — `make check-model` holds each of those. That
is the contract a concurrent sibling builds against. A ready slice still `modelled` is a stop at the
example map — its events may yet change shape, and a sibling building on them would be building on sand —
so it is worked here first, never delegated alongside the others."""
    return """**The contract is settled.** A ready slice runs alongside its siblings only when what they share is
written down: the entries it adds to `specs/<feature>/contracts/` exist, and its acceptance criteria in
`spec.md` have had their gaps review. That is the contract a concurrent sibling builds against. A ready
slice whose surface is still being decided is worked here first, never delegated alongside the others."""


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
   stop merely to choose among them unless the user asks."""


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
and say so.

**Each slice has its own worktree and one delegate.** For every unclaimed ready slice whose contract is
settled, in the same turn: claim it, give it a worktree (`git worktree add ../<project>-<id> slice/<id>`;
on Claude Code the Agent tool's `isolation: worktree` makes one), and delegate the slice's ladder — its
example map through its converged verdict — to one fresh `drive-slice` delegate (`agents/drive-slice.md`,
the standing brief) with a manifest naming the worktree, the slice's block of the model, its `examples.md`,
and the shared-surface rule below. That type takes no stage's model, because *Who runs each stage* still
chooses one stage by stage inside the delegate, where `[P]` tasks still fan out to `drive-implement`: the
two levels nest. Inside one slice the stages stay strictly sequential. A delegate that meets a
product question stops its slice with the question recorded in its `plan.md` and hands it here — a blocked
slice is marked blocked, never guessed past.

**The shared-surface rule**, which the delegates cannot infer and `{layout.make} check-slice-scope` holds on
every `slice/<id>` branch: a slice's commits touch its own `specs/<feature>/slices/<id>/`, the feature's
cumulative artifacts (`spec.md`, `story-split.md`, `contracts/`, `checklists/`, `adversary-log.md`), its own
block of `model.yaml`, the mockups, the code and tests of the service that owns it — one bounded context
where the service holds several — the context's events module *additively*, **new** migration files named
by a timestamp (`date -u +%Y%m%d%H%M`, so two slices never mint the same name), and the composition root.
Nothing else — `Makefile`, `project.json`, package manifests and locks, `scripts/`, `skills/`, `agents/`, the
docs — is a slice's to write: a delegate that needs one of them hands the need back here, and it lands on `main` before
the fan-out or between merges. The canonical slot at the feature root is a link, never committed.

**Demo on the slice branch, then verify, then push.** As delegates report converged, demo each slice from
its unpushed worktree in split order — never from `main`, never by pushing increment commits first. A
claim may already have pushed a lock ref from `main`; leave the increment commits local until the actor
accepts. After acceptance: `codegraph sync` if the project has adopted a code index, `{layout.make} verify`
green, then push the slice's commits and merge into `main` in split order — never in finishing order.
That is the first implementation push, and it is what starts CI. The composition root and the cumulative
artifacts are where two merges meet, and split order is what makes those resolutions predictable;
regenerate the model diagram after a merge, never in a branch. No slice's Phase 4 runs until its demo is
accepted, and a sibling's demo never waits on another's Phase 4. Phase 4 itself — adversary, mutation,
`{layout.make} verify`, marking the slice done — runs here, on `main`, one slice at a time. Delete the
`slice/<id>` branch once its Phase 4 clears: the claim is spent.

**Where the harness cannot delegate**, run one slice at a time here — claim the earliest in split order,
name the rest — and say so in the line that says which model ran (`harness cannot delegate`)."""

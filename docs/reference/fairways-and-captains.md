# The fairway, the captain, the harbourmaster

A **fairway** is one bounded context's slices, in split order, with one release flag and one holder. It is
the unit of scope, of ownership and of release. Several fairways run side by side into the same harbour, and
they share nothing but [marks](the-chart-and-the-mark.md).

A **captain** is the outer loop for one fairway. A **harbourmaster** is the part the captains share.

```
python3 scripts/agents/claims.py          # every fairway the chart has, and who holds it
```

---

## One captain per fairway, and the ref that makes it true

Two machines running a captain for the same fairway is two processes appending to one
`.slipwai/logs/<feature>/<fairway>.jsonl` through two worktrees — a conflict in the one file the whole
design promises will never have one, and, where one side forces the ref, lines nobody can tell are missing.

So a claim is a git ref: **`refs/slipwai/claims/<fairway>`**. A captain takes it before it writes `claimed`,
and a machine that cannot take it is told who holds it and since when.

The mechanism is a push that is not a fast-forward, which every forge refuses — an atomic compare-and-swap
with nothing of slipwai's own running: no server, no lease daemon, no election. With no forge at all it is
`git update-ref` against the value the ref must already have, which is the same compare-and-swap made
smaller.

**The ref is a chain and nothing is ever deleted.** Its tip is a commit whose author is the machine, whose
date is *since when*, and whose message is `held` or `released`. Taking a free fairway pushes a child of the
tip you read; if another machine took it in between, your commit's parent is no longer the tip and the push
is refused. Releasing pushes a `released` child rather than deleting the ref, so
`git log refs/slipwai/claims/ordering` still answers *who had this fairway last Tuesday* — a question
somebody asks after a bad merge. A tip saying anything else is read as **held**, because an unreadable claim
must never read as free.

`held_by` in the split's table is rendered from this and written by nothing. There were two answers to *who
holds this fairway* — a name in a markdown table and a running process with a pid — and a third would have
been worse than either. A person taking a fairway by hand takes the same ref:

```
python3 scripts/agents/claims.py --take ordering
python3 scripts/agents/claims.py --release ordering
```

---

## What a captain does

It fetches trunk and reads both logs. It works out the fairway's state from the logs plus trunk, never from
a `status` field. It gives [clearance](clearance.md). It claims `slice/<id>`. It dispatches the stage with
its budgets. It enforces an inbox read at every boundary. It writes a heartbeat. It ends a stage that has
wedged. It appends every result to its own [deck log](the-logs.md), and to nothing else.

**It runs in both modes, and the modes differ in two seats only.** Under `/sail` a person is present and the
fleet still fans out; every product question, park and demo stop comes back to that person through the
inbox. Under `/cruise` the same captains run with nobody at the keyboard: the skipper answers the product
questions and the hand walks the demos. Nothing else differs.

**A captain holds no credential.** Its berth is a sandbox or a container, and a berth with a token in it is
a sandbox with a way out. Anything outside the berth — a push, a merge, a deploy, a flag change, a publish —
is a `request` line the harbourmaster answers.

**None of its controls depends on a harness hook.** The captain reads the last line of every iteration
itself, compares the controlled files before and after, and owns the waits. Where a harness has a hook, the
hook is a second belt.

---

## What a harbourmaster does

One per machine, and the only writer of that machine's [harbour log](the-logs.md).

- **It carries between fairways.** A fairway that had to read every other fairway's log to find the one line
  it needed would read a hundred files to find three. So a mark set, a park, a berth allocated and a flag
  changed are copied into the harbour log.
- **It allocates berths.** A captain asks with `berth-request`; the answer is `berth-allocated`. The numbers
  are arithmetic, so nobody chooses one and nobody chooses the same one twice — but somebody has to decide
  the order, and one writer deciding it is the whole of the mechanism.
- **It holds the credentials.** It does what a `request` asks or refuses with the reason, checked against a
  closed list of what a run never does: destroy data or history, release what nobody asked for, spend money,
  expose a secret, weaken security, discard a person's commits, change a gate to make it pass. Both outcomes
  are written.
- **It holds the flags**, draws the fleet board and the bridge, and answers the telegraph.

Under `/sail` it runs inside the person's session, so the person's own credentials are used and are never
copied into a berth. Under `/cruise` it is a process of its own.

---

## The merge, serialised through `refs/slipwai/merge`

A granted merge is **performed, not merely permitted**: the harbourmaster rebases the slice branch onto
trunk in a scratch worktree of its own, runs the project's own `make verify` there, and advances trunk. Then
`granted` carries the commit, and the captain writes `merged` into its own log against it.

Two harbourmasters rebasing onto one trunk at once is two gates each measured against a trunk the other is
about to move. So the merge takes `refs/slipwai/merge` — the same compare-and-swap a claim uses, taken
before the rebase and given back afterwards.

Four things about how, each of which was a choice:

- **One at a time, in the order they were asked.** Each gate then runs on a trunk that already holds every
  merge before it. Gating two in parallel wins nothing: `make verify` is a whole-repo gate, and a result
  measured against a trunk that has since moved has to be measured again.
- **A scratch worktree, never the berth.** The berth belongs to a captain that may still be writing in it,
  and the person's own checkout belongs to the person.
- **The gate is the project's own `make verify`** — exactly what [the two gates](the-two-gates.md) already
  name, so a project that adds a check gets it at the merge for nothing. `make ci` was rejected because it
  wants Docker or the network, and a laptop without them could then never merge.
- **A conflict is aborted and refused, naming the paths.** `git rebase --abort`, so nothing is left
  half-done, and the captain resolves in its own berth — where the context is — and asks again.

The loser of the race waits on the ref rather than refusing at once, because the machine ahead will be some
minutes. What the wait bound catches is not a busy harbour but a dead one: a machine that took the ref and
was killed before it could give it back. That is a line a person has to read, so it is said rather than
waited on for ever.

**It is not a merge queue.**

---

## Ids, and the files two fairways would otherwise meet on

Every id carries its fairway — `D-ORD-07`, `A-BIL-03` — so two fairways cannot mint the same one and
nothing is ever renumbered. Every append-only artefact is per fairway: `fairways/<name>/decisions.md`, the
adversary log, the benchmark records, the register, and the deck log. The feature-level files are rendered
from them on `main` by the harbourmaster and are never edited by hand:

```
python3 scripts/agents/ids.py decision ORD     # the next decision id in that fairway: D-ORD-01, D-ORD-02, …
make decisions                                 # fold every fairway's files into the feature-level ones
make check-rendered                            # fail when a folded file is not what it renders from
```

Two digits, so a fairway's ids sort as text for as long as it has fewer than a hundred.

---

Next: [the deck log and the harbour log](the-logs.md) · [the telegraph](the-telegraph.md) ·
[the two gates](the-two-gates.md) · [a second person joins](../guide/a-second-person.md)

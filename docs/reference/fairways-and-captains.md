# The fairway, the captain, the harbourmaster

A **fairway** is the slices of one bounded context, in split order, with one release flag and one holder.
The fairway is the unit of scope, of ownership and of release. Several fairways run side by side into the
same harbour. Fairways share nothing except [marks](the-chart-and-the-mark.md).

A **captain** is the outer loop for one fairway. A **harbourmaster** is the part that the captains share.

```
python3 scripts/agents/claims.py          # every fairway the chart has, and who holds it
```

---

## One captain per fairway, and the ref that makes it true

Two machines must not run a captain for the same fairway. If they did, two processes would append to one
`.slipwai/logs/<feature>/<fairway>.jsonl` through two worktrees. The design promises that this file never
has a conflict, and this would give it one. If one side then forced the ref, lines would be missing and
nobody could tell.

So a claim is a git ref: **`refs/slipwai/claims/<fairway>`**. A captain takes the ref before it writes
`claimed`. If a machine cannot take the ref, the machine is told who holds it and since when.

The mechanism is a push that is not a fast-forward. Every forge refuses such a push. This makes the push an
atomic compare-and-swap, and slipwai runs nothing of its own for it: no server, no lease daemon and no
election. When there is no forge, the mechanism is `git update-ref` against the value that the ref must
already have. That is the same compare-and-swap, on one machine.

**The ref is a chain, and nothing in it is ever deleted.** The tip of the ref is a commit:

- the author is the machine;
- the date is *since when*;
- the message is `held` or `released`.

To take a free fairway, push a child of the tip that you read. If another machine took the fairway in the
meantime, the parent of your commit is no longer the tip, and the forge refuses the push.

To release a fairway, push a `released` child. Do not delete the ref. Because the chain stays,
`git log refs/slipwai/claims/ordering` still answers *who had this fairway last Tuesday*. People ask that
question after a bad merge.

A tip with any other message reads as **held**. An unreadable claim must never read as free.

`held_by` in the split's table is rendered from this ref. Nothing writes `held_by` directly. Before this,
there were two answers to *who holds this fairway*: a name in a markdown table, and a running process with
a pid. A third answer would be worse than either. A person who takes a fairway by hand takes the same ref:

```
python3 scripts/agents/claims.py --take ordering
python3 scripts/agents/claims.py --release ordering
```

---

## What a captain does

A captain does these things, in this order:

1. It fetches trunk and reads both logs.
2. It works out the state of the fairway from the logs and trunk. It never reads a `status` field.
3. It gives [clearance](clearance.md).
4. It claims `slice/<id>`.
5. It dispatches the stage, with the stage's budgets.
6. It makes the stage read the inbox at every boundary.
7. It writes a heartbeat.
8. It ends a stage that is wedged.
9. It appends every result to its own [deck log](the-logs.md). It writes to no other log.

**A wedged stage is a stage that shows no progress for the stage bound.** The stage bound is the longest
stage budget in `harbour.json`. Progress is a new line in the deck log, or a new commit on `slice/<id>`.
When a stage parks itself, the stage keeps its own park. The captain does not write a second park over it.

**A captain runs in both modes, and the two modes differ in two seats only.**

- Under `/sail`, a person is present, and the fleet still fans out. Every product question, park and demo
  stop comes back to that person through the inbox.
- Under `/cruise`, the same captains run with nobody at the keyboard. The skipper answers the product
  questions, and the hand walks the demos.

Nothing else differs.

**A captain holds no credential.** Its berth is a sandbox or a container. A berth with a token in it is a
sandbox with a way out. For anything outside the berth, the captain writes a `request` line, and the
harbourmaster answers it. Examples are a push, a merge, a deploy, a flag change and a publish.

**None of the captain's controls depends on a harness hook.** The captain reads the last line of every
iteration itself. It compares the controlled files before and after. It owns the waits. When a harness has
a hook, the hook is a second, extra control.

---

## What a harbourmaster does

There is one harbourmaster for each machine. It is the only writer of that machine's
[harbour log](the-logs.md).

- **It carries lines between fairways.** If a fairway had to read every other fairway's log to find the one
  line it needed, it would read a hundred files to find three. So the harbourmaster copies these into the
  harbour log: a mark set, a park, a berth allocated, and a flag changed.
- **It allocates berths.** A captain asks with a `berth-request` line. The answer is a `berth-allocated`
  line. The berth numbers are calculated, so nobody chooses a number and nobody chooses the same number
  twice. But something has to decide the order. One writer that decides the order is all of the mechanism.
- **It holds the credentials.** It does what a `request` asks, or it refuses and gives the reason. It checks
  each request against a closed list of things that a run never does:
  - destroy data or history;
  - release something that nobody asked for;
  - spend money;
  - expose a secret;
  - weaken security;
  - discard a person's commits;
  - change a gate to make it pass.

  It writes both outcomes, a grant and a refusal, to the log.
- **It holds the flags**, draws the fleet board and the bridge, and answers the telegraph.

Under `/sail`, the harbourmaster runs inside the person's session. So it uses the person's own credentials,
and it never copies them into a berth. Under `/cruise`, the harbourmaster is a separate process.

---

## The merge, serialised through `refs/slipwai/merge`

The harbourmaster **performs a granted merge. It does not only permit it.** It does these steps:

1. It rebases the slice branch onto trunk, in a scratch worktree of its own.
2. It runs the project's own `make verify` in that worktree.
3. It advances trunk.
4. It writes `granted` with the commit. The captain then writes `merged` against that commit in its own log.

Two harbourmasters must not rebase onto one trunk at the same time. If they did, each gate would measure
against a trunk that the other is about to move. So the merge takes `refs/slipwai/merge`. This is the same
compare-and-swap that a claim uses. The harbourmaster takes the ref before the rebase and gives it back
afterwards.

Four parts of this design were each a choice:

- **Merges go one at a time, in the order that they were asked for.** Each gate then runs on a trunk that
  already holds every earlier merge. Gating two merges in parallel gains nothing. `make verify` is a gate
  for the whole repository. A result measured against a trunk that has since moved must be measured again.
- **The merge uses a scratch worktree, never the berth.** The berth belongs to a captain that may still be
  writing in it. The person's own checkout belongs to the person.
- **The gate is the project's own `make verify`.** This is exactly the gate that
  [the two gates](the-two-gates.md) names. So when a project adds a check, the merge runs that check with no
  extra work. `make ci` was rejected, because it needs Docker or the network. A laptop without them could
  then never merge.
- **A conflict is aborted and refused, and the refusal names the paths.** The harbourmaster runs
  `git rebase --abort`, so nothing is left half-done. The captain resolves the conflict in its own berth,
  where the context is, and asks again.

When two machines race for the ref, the machine that loses waits on the ref. It does not refuse at once,
because the machine ahead takes some minutes. The wait bound does not catch a busy harbour. It catches a
dead one: a machine that took the ref and was killed before it gave it back. A person has to read that
case, so the harbourmaster reports it instead of waiting for ever.

**It is not a merge queue.**

---

## Ids, and the files two fairways would otherwise meet on

Every id carries its fairway, for example `D-ORD-07` and `A-BIL-03`. So two fairways cannot mint the same
id, and nothing is ever renumbered.

Every append-only artefact is kept for each fairway separately: `fairways/<name>/decisions.md`, the
adversary log, the benchmark records, the register, and the deck log. The harbourmaster renders the
feature-level files from them on `main`. Nobody edits the feature-level files by hand:

```
python3 scripts/agents/ids.py decision ORD     # the next decision id in that fairway: D-ORD-01, D-ORD-02, …
make decisions                                 # fold every fairway's files into the feature-level ones
make check-rendered                            # fail when a folded file is not what it renders from
```

Ids use two digits. So a fairway's ids sort correctly as text while the fairway has fewer than a hundred.

---

Next: [the deck log and the harbour log](the-logs.md) · [the telegraph](the-telegraph.md) ·
[the two gates](the-two-gates.md) · [a second person joins](../guide/a-second-person.md)

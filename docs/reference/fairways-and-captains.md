# The fairway, the captain, the harbourmaster

A **fairway** is the slices of one bounded context, in split order, with one release flag and one holder.
The fairway is the unit of scope, of ownership and of release. Several fairways run side by side into the
same harbour. Fairways share nothing except [marks](the-chart-and-the-mark.md).

A **captain** runs one fairway: a program that is always there, and, where the harness allows it, an agent on
top of it that makes a few choices the program checks. A **harbourmaster** is the part that the captains
share.

```
python3 scripts/agents/claims.py          # every fairway the chart has, and who holds it
```

---

## One captain per fairway, and the ref that makes it true

Two machines must not run a captain for the same fairway. If they did, two processes would append to one
`.slipwai/run/logs/<feature>/<fairway>.jsonl` through two worktrees. The design promises that this file never
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

The captain program does these things, in this order:

1. It fetches trunk and reads both logs.
2. It works out the state of the fairway from the logs and trunk. It never reads a `status` field.
3. It gives [clearance](clearance.md).
4. It claims `slice/<id>`.
5. It dispatches the stage, with the stage's budgets.
6. It delivers what is said to the slice through the slice's driver, and wakes its captain agent, where it
   has one, when there is a choice to make.
7. It writes a heartbeat.
8. It ends a stage that is wedged.
9. It appends every result to its own [deck log](the-logs.md). It writes to no other log.

**A captain runs its fairway's ready slices abreast.** Rule 6 of `/sail`'s *Ready-set selection* says that
several ready slices run at once, and a captain now honours it inside its fairway as a person's `/sail`
does. A slice is ready when every `depends_on` in the slice graph has merged, every mark it steers by is
set, and no question or park holds it — [clearance](clearance.md) answers that, and nothing else does. Two
ready slices may run together unless the split's `parallel_ok_with` leaves one of them out. Each slice
then gets:

- **its own berth**: a worktree at `../<project>-<id>` on `slice/<id>`, the same name `/sail` gives one, with
  `.slipwai/run/logs` linked to the project's so that every line lands in the one deck log;
- its own session — held open over the Agent Client Protocol where `sessions` and the harness allow it,
  the harness's print mode elsewhere — stage bound, retries, `.working` marker
  (`.slipwai/run/running/captain-<fairway>--<slice>.working`) and gate, read from the lines that carry its
  `slice`;
- its own merge request. Merges still go one at a time through the harbourmaster. A rebase conflict with a
  sibling's merge sends that slice back to its berth to resolve, and it asks again.

As each slice merges or parks, the captain starts the next ready one into the space it left, without
waiting for the rest. A park that names a `slice` holds that slice alone, and its siblings carry on. A stop
ends every slice in flight and writes a `stopped` line for each. The next captain lit resumes every slice
that was claimed and not merged. With `abreast: 1`, a captain works one slice at a time in the project's
own checkout, exactly as it did before.

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

## The captain agent

The program decides by fixed rules. The **captain agent** is one coding-agent session per fairway that makes
some of those decisions instead, with the program still underneath it. No setting makes the agent the only
decider: the program is always there.

**What wakes it.** The program writes an event to `.slipwai/run/events/<fairway>/<id>.json` when there is a
choice to make, with the facts the choice needs, the orders it will accept, and the order its fixed rule
would give. Beside the events, `state.json` is the fairway as its log says it now. Each wake-up hands the agent
these, never what it remembers, so a cold start answers as a warm one would.

| Event | The choice |
|---|---|
| `choose-next` | Which cleared slices start, when more could start than there are free slots |
| `gate-failed` | Retry the slice with a note, or park it with a reason |
| `stuck` | Message, interrupt, pause, stop or park a slice that is taking long, going in circles or gone quiet, or tell the person |
| `message` | Where something said to the stream goes, or what to answer |
| `permission` | Whether a slice's session may touch something outside its berth: a read inside the project, nothing else |
| `question` | Only where `captain.answers` is on: an answer to a question a slice's session asked mid-turn |
| `trunk-red` | What to say or do while trunk is red. Nothing new starts until it is green |

**How it acts.** Only by running the project's own `scripts/agents/orders.py`, which writes a signed order to
`.slipwai/run/orders/<fairway>/`. The program reads the order, checks it against the rules as they stand when
it is carried out — clearance, the free slots, the attempts left, a person's hold, the merge — does it or
refuses it, and writes `done` or `refused` with why beside it. It writes every deck line itself.

**When the agent fails.** Where it says nothing within `captain.bound` seconds of its session being ready,
gives an order the event does not allow, or cannot be run, the program closes the event by its fixed rule,
records that the rule closed it and why, and tries the agent again at the next event. Its own loop never
waits on the agent. If the agent's machinery fails outright, the fairway runs on the program alone until the
captain is next started, `captain.json` beside the events says `"agent": false` with why, and the deck log
gets one `noted` line.

**Only over the Agent Client Protocol.** The agent's session is held over the protocol with a policy that lets
it read and run `orders.py` and refuses every other tool call. A captain run headless, with a shell of its
own, could reach anything in the project, and nothing checked afterwards could tell its changes from the
fleet's own work, so there is no such captain. Where the harness has no launch over the protocol that the
registry marks proven, the fairway runs on the program alone and says so once.

**It does not answer product questions.** A question a slice's session asks mid-turn is declined and goes down
the deck log's `question` path, to the skipper or a person as the project's *Who answers* settings say. With
`captain.answers: true` the agent may answer; every answer, and every refusal with words in it, is then a
`decision` by `captain:<fairway>`, counted toward the decision ceiling.

**Settings.** `harbour.json`'s `captain`: `agent` (true in a new project; absent or false is the program
alone, and migrating never sets it), `bound` (60 seconds), `answers` (false), `per_hour` (30, the most
times the agent is woken in an hour), `context_ceiling` (150000, the tokens of context past which the captain's
session is closed at the next event and a fresh one started) and `wake_ceiling` (100, the wake-ups one session
answers where the agent never reports its context). A captain program never loads the session a run before it
saved: each wake-up hands the agent the stream's state, so its history is worth nothing. `SLIPWAI_CAPTAIN` in the environment says first: `off`, `1` for the
project's own harness, or a command that starts an agent speaking the protocol.

**Where the checks stop.** Every check here is against the captain agent and the slices' sessions acting
through their tools. None is against another process of the same user writing the run folder directly. Such
a process can append a `told` line as a person, clear a park, write a line in a conversation's thread, or read
the keys that sign messages and orders. Only running sessions as another user would stop it, and nothing is
built against it.

**Evals.** The keel repository scores the agent's choices against recorded situations: `make evals` puts
each case to the captain through the harness several times and reports, for each decision, how often its
order was one a person would accept; `make evals-rescore` judges a saved run again without calling an agent.
The score is advice and gates nothing. A project carries none of this. [The captain's
evals](../captain-evals.md) describes the cases and the scoring.

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

### How the boilers are shared

`boilers` is the number of slice sessions that run at once in the harbour, in every fairway together. It
used to count captains, and a captain ran one slice. A captain can now run several, so a second budget for
slices would be two levers on one machine. Instead the harbourmaster shares `boilers` out on each pass and
writes a `slots` line for each fairway whose number has changed. It already lights the captains, and it is
the one writer of its harbour log, so it is the one decider. The rule, in order:

1. **Breadth first.** Every fairway with work gets one session before any fairway gets a second.
2. **Then depth, by priority.** Spare sessions go to the fairways that can use them. The order is the
   person's own (`fairways` in `harbour.json`), then the critical path — a ready slice whose merge unblocks
   the most slices, or sets a mark that another fairway steers by — then the most ready slices left.
3. **`abreast` caps depth.** It is three where `harbour.json` does not say, and never more than `boilers`.
4. **Back-pressure.** A fairway with a slice waiting on a merge answer starts nothing new. Merges run one at
   a time with a full gate each, so starting more only makes more rebase conflicts.
5. **Nothing is preempted.** A running session keeps its slot until its slice merges, parks or stops. The
   slot it frees is offered again by the same rules, the way `yielded` hands a berth from one captain to
   another.

A captain's first slice is its own, because it was lit. It starts any slice beyond that only on a `slots`
line written since its fairway's last slice ended. A captain that finds no `slots` line runs one slice.
With `abreast: 1`, or with `boilers` equal to the number of fairways that have work, every fairway runs one
slice, which is what the fleet always did.

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

**It performs the merge and chooses none.** A slice lands because its captain asked and the gate passed, in
the order of the asking.

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

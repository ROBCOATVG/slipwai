# The deck log and the harbour log

Status is folded from log lines, and it is stored nowhere. **A slice that wrote no line made no progress.**

There are two logs. The split between them is about who writes them, not about what they contain. Each file
has one writer, and that is all of the mechanism. No two processes ever append to the same file, so neither
log can have a conflict.

| | Deck log | Harbour log |
|---|---|---|
| Path | `.slipwai/logs/<feature>/<fairway>.jsonl` | `.slipwai/logs/harbour/<machine>.jsonl` |
| One per | Fairway | Machine |
| Written by | That fairway's captain, and nothing else | That machine's harbourmaster, and nothing else |
| Read by | Everybody | Everybody |
| Synced through | `refs/slipwai/logs/<fairway>` | `refs/slipwai/logs/harbour/<machine>` |

Neither log is committed. `.gitignore` lists `.slipwai/logs/`, because heartbeat and token lines arrive
every few seconds and do not belong in trunk's history. The harbourmaster pushes and fetches the logs
through their own refs. So a captain on another machine reads the same lines without a commit on `main`.

A push that is not an append is refused. If a local log does not continue what the ref holds, its push would
drop every line that the ref has, and nobody could tell.

A project that was written before there were three writers has one `.slipwai/logs/harbour.jsonl`. The fold
still reads that file with the rest, and nothing moves it. A migration that moves somebody's log can lose a
line, and these lines are the only record.

---

## Every line carries `v`

`v` is the format version of the line. When a reader meets a version that it does not know, it refuses the
line and names `slipwai upgrade`. It does not guess which fields moved.

A line that the reader cannot read stops the fold. The reader does not skip it. A log that is missing the
events it could not parse looks exactly like the log of a run that did not have those events. A board that
is folded from a log with gaps is wrong, and it looks certain.

Fields are checked when a line is written, as well as when it is read. If a line is written with a field
missing, a reader weeks later cannot use it, and by then nobody knows what the missing value was.

---

## The deck log's kinds

Every line has `v`, `t` and `kind`. Each kind also has the fields named here.

| Kind | Carries | What it records |
|---|---|---|
| `claimed` | `fairway`, `slice` | This captain has taken the slice |
| `mark-set` | `fairway`, `slice`, `mark` | A contract is published. Written at the setting slice's first stage, in its own worktree — this is what gives a sibling [clearance](clearance.md), which is why it is not `merged` |
| `demo` | `fairway`, `slice`, `verdict` | The hand walked the examples. `verdict` is one of `accepted`, `behaviour` or `implementation`, and nothing else |
| `accepted` | `fairway`, `capability` | A person accepted a demo. Against a capability, not a slice |
| `demo-due` | `fairway`, `capability` | A capability's last slice has merged, so a person's demo is owed |
| `merged` | `fairway`, `slice`, `commit` | The slice is on trunk |
| `decision` | `fairway`, `id`, `what` | A decision, with the fairway-carrying id that makes renumbering impossible |
| `question` | `fairway`, `slice`, `id`, `what` | A product question this slice cannot be guessed past, waiting on a person. Open until a `decision` line carries the same `id`; while it is open [clearance](clearance.md) reports the slice as *awaiting decision* and names the siblings the wait reaches |
| `told` | `fairway`, `message` | A person said something to this captain |
| `read` | `fairway`, `told` | The captain read it. Carries the `t` of the `told` it answers, which is what makes it a receipt rather than an assertion |
| `heartbeat` | `fairway` | Still working |
| `request` | `fairway`, `id`, `what`, `detail` | Something outside the berth is wanted: `push`, `merge`, `deploy`, `flag` or `publish` |
| `berth-request` | `fairway` | A berth is wanted |
| `stowed` | `fairway`, `slice`, `from`, `what` | Work moved into the careen when a stage ran out of budget |
| `taken-over` | `fairway`, `slice`, `from` | Another machine went past its lease and this captain took the claim, the log and the in-flight branch over mid-slice. The one thing in a fairway's history a later reader cannot work out from any other line |
| `parked` | `fairway`, `why` | This fairway has stopped and says why |

---

## The harbour log's kinds

A captain never appends to the harbour log. The harbourmaster copies across what other fairways need, and
records the answers that it owes.

| Kind | Carries | What it records |
|---|---|---|
| `mark-set` | `fairway`, `slice`, `mark` | A mark carried across from a deck log |
| `flag-hoisted` | `flag`, `where` | A [release flag](release-modes.md) turned on, and in which environment |
| `flag-struck` | `flag` | A release flag removed |
| `berth-allocated` | `fairway`, `berth` | The answer to a `berth-request` |
| `fires-banked` | `step`, `why` | The [telegraph](the-telegraph.md) stepped down because the bunker ran out |
| `park` | `fairway`, `why` | A park carried across, so other fairways and the inbox see it |
| `telegraph` | `position` | The lever was rung |
| `granted` | `fairway`, `request`, `what` | A `request` was done. A merge's answer, granted or refused, also says where its time went, in whole seconds: `waited_s` queued for the harbourmaster, `lock_s` waiting on `refs/slipwai/merge`, `gate_s` running the gate, each as far as the merge got. `attempt` says which attempt at that slice it was |
| `refused` | `fairway`, `request`, `why` | A `request` was not. Both outcomes are written: a refusal that left no line is one the captain waits on for ever and nobody can explain afterwards |
| `cleared` | `fairway`, `parked`, `what` | The receipt a `parked` owes — see below |
| `trunk-red` | `commit`, `job`, `why` | Trunk's own CI went red. Written once per change of state, because a log saying `trunk-red` every fifteen seconds is one nobody reads |
| `trunk-green` | `commit` | And once per change back |
| `fix-trunk` | `fairway`, `slice`, `commit`, `job` | Sent to the captain whose `merged` line names the commit that went red |

Trunk can go red because of a check that `make verify` never ran. For this reason, the last four kinds are
in the harbour log and not in one fairway's log. If nothing explains a red trunk, the harbourmaster writes a
`park` for a person.

---

## What a `parked` owes

Each `parked` line needs a `cleared` receipt in the harbour log. The receipt names two things: the
**fairway, and the timestamp of the original park**. A later heartbeat does not count, and another
fairway's park does not count. The fairway's wait clock runs until that receipt arrives.

The receipt names the park for this reason: if an answer did not name which park it answered, one answer
could close two waits. The second fairway would then continue on an answer that nobody gave it.

**Two things cause the receipt to be written.** The harbourmaster writes it in both cases, because the
harbourmaster is the only writer of the harbour log:

- **A `told` line after the park.** The board's answer box, `/cruise-tell` and `make cruise-tell` each write
  a `told` line in the fairway's deck log. On each pass, the harbourmaster reads every deck log in full. For
  each open park that has a later `told` for the same fairway, it writes `cleared` with that park's
  timestamp. `what` is the last such message. A second pass writes nothing, because the receipt has already
  closed the park.
- **`harbourmaster.py --clear <fairway>`**, which a person types.

**While a park is open, the harbourmaster does not light a captain for that fairway.** It lights a captain
for the fairway again on the pass after the receipt.

---

## Which machine this is

Each machine has one identity. Slipwai works it out; nobody chooses it. The identity is the first label of
the hostname, in lower case. Every character that is not safe in all three of these places becomes `_`:

- a git ref component;
- a path component;
- an unquoted SQL identifier.

The identity is at most sixteen characters long. It names three things: the claim ref that a captain takes,
the harbour log that this machine writes, and the database that a berth allocates.

`SLIPWAI_MACHINE` is the one place where a person types a name, and they type it once. Two containers made
from one image share a hostname. Without `SLIPWAI_MACHINE`, the first sign of this would be a shared
database, not a message.

---

Next: [fairways, captains and the harbourmaster](fairways-and-captains.md) ·
[clearance](clearance.md) · [let it cruise](../guide/let-it-cruise.md)

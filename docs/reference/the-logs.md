# The deck log and the harbour log

Status is folded from lines and stored nowhere. **A slice that wrote no line made no progress.**

There are two logs, and the split between them is about writers, not about contents. One writer per file is
the whole mechanism: no two processes ever append to one file, so neither log can conflict.

| | Deck log | Harbour log |
|---|---|---|
| Path | `.slipwai/logs/<feature>/<fairway>.jsonl` | `.slipwai/logs/harbour/<machine>.jsonl` |
| One per | Fairway | Machine |
| Written by | That fairway's captain, and nothing else | That machine's harbourmaster, and nothing else |
| Read by | Everybody | Everybody |
| Synced through | `refs/slipwai/logs/<fairway>` | `refs/slipwai/logs/harbour/<machine>` |

Neither is committed. `.gitignore` lists `.slipwai/logs/`, because heartbeat and token lines arrive every
few seconds and have no place in trunk's history. The harbourmaster pushes and fetches them through their
own refs, so a captain on another machine reads the same lines with no commit on `main`. A push that is not
an append is refused: a local log that is not a continuation of what the ref holds is one whose push would
drop every line the ref has, and nobody could tell.

A project written before there were three writers has one `.slipwai/logs/harbour.jsonl`. It is still read
and folded in with the rest, and nothing moves it — a migration that relocates somebody's log is one that
can lose a line, and these lines are the only record there is.

---

## Every line carries `v`

A reader that meets a version it does not know refuses the line and names `slipwai upgrade` rather than
guessing which fields moved. A line that cannot be read stops the fold rather than being skipped: a log
missing the events it could not parse reads exactly like a log of a run that did not have them, and a board
folded from a log with holes in it is confidently wrong.

Fields are checked on the way in as well as on the way out. A line written short is a line some reader
weeks later cannot use, and by then nobody knows what the missing value was.

---

## The deck log's kinds

Beyond `v`, `t` and `kind`, each carries the fields named here.

| Kind | Carries | What it records |
|---|---|---|
| `claimed` | `fairway`, `slice` | This captain has taken the slice |
| `mark-set` | `fairway`, `slice`, `mark` | A contract is published. Written at the setting slice's first stage, in its own worktree — this is what gives a sibling [clearance](clearance.md), which is why it is not `merged` |
| `demo` | `fairway`, `slice`, `verdict` | The hand walked the examples. `verdict` is one of `accepted`, `behaviour` or `implementation`, and nothing else |
| `accepted` | `fairway`, `capability` | A person accepted a demo. Against a capability, not a slice |
| `demo-due` | `fairway`, `capability` | A capability's last slice has merged, so a person's demo is owed |
| `merged` | `fairway`, `slice`, `commit` | The slice is on trunk |
| `decision` | `fairway`, `id`, `what` | A decision, with the fairway-carrying id that makes renumbering impossible |
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

A captain never appends here. The harbourmaster carries across what other fairways need, and records the
answers it owes.

| Kind | Carries | What it records |
|---|---|---|
| `mark-set` | `fairway`, `slice`, `mark` | A mark carried across from a deck log |
| `flag-hoisted` | `flag`, `where` | A [release flag](release-modes.md) turned on, and in which environment |
| `flag-struck` | `flag` | A release flag removed |
| `berth-allocated` | `fairway`, `berth` | The answer to a `berth-request` |
| `fires-banked` | `step`, `why` | The [telegraph](the-telegraph.md) stepped down because the bunker ran out |
| `park` | `fairway`, `why` | A park carried across, so other fairways and the inbox see it |
| `telegraph` | `position` | The lever was rung |
| `granted` | `fairway`, `request`, `what` | A `request` was done |
| `refused` | `fairway`, `request`, `why` | A `request` was not. Both outcomes are written: a refusal that left no line is one the captain waits on for ever and nobody can explain afterwards |
| `cleared` | `fairway`, `parked`, `what` | The receipt a `parked` owes — see below |
| `trunk-red` | `commit`, `job`, `why` | Trunk's own CI went red. Written once per change of state, because a log saying `trunk-red` every fifteen seconds is one nobody reads |
| `trunk-green` | `commit` | And once per change back |
| `fix-trunk` | `fairway`, `slice`, `commit`, `job` | Sent to the captain whose `merged` line names the commit that went red |

Trunk can go red from a check `make verify` never ran, which is why these four exist at harbour level rather
than in one fairway's log. A red nothing accounts for is a `park` for a person.

---

## What a `parked` owes

A `parked` line owes a `cleared` receipt in the harbour log, and the receipt's identity is the **fairway
plus the original park's timestamp** — never a later heartbeat, and never another fairway's park. The
fairway's wait clock runs until that receipt arrives.

That is why the pair exists: a park answered by a line that did not name which park it answered would let
one answer close two waits, and the second fairway would run on an answer nobody gave it.

---

## Which machine this is

One identity, derived and not chosen: the hostname's first label, lowercased, with everything outside the
three alphabets it has to survive — a git ref component, a path component, an unquoted SQL identifier —
folded to `_`, and capped at sixteen characters. It names the claim ref a captain takes, the harbour log
this machine writes, and the database a berth allocates. `SLIPWAI_MACHINE` is the one place a name is
typed, and it is typed once: two containers off one image share a hostname, and a shared database is where
that is found out rather than said.

---

Next: [fairways, captains and the harbourmaster](fairways-and-captains.md) ·
[clearance](clearance.md) · [let it cruise](../guide/let-it-cruise.md)

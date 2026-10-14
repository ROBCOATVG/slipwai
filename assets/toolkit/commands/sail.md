---
description: Drive one slice through planning, implementation, and an actor-visible demo
argument-hint: [slice-id-or-feature] [fairway=<name>]
---

# Drive

Deliver one small vertical slice under `AGENTS.md`. Once the ladder below has produced it, resolve
{{resolution}}.

## What the argument narrows

**Bare is the normal form.** With no argument this takes the ready slices of every fairway nobody holds,
works them, and goes on to the next without being invoked again — *Ready-set selection* below is the whole
rule, and it stops only when the split is exhausted or everything left is blocked. Each of the three
arguments narrows that and nothing else:

| Written | What ready means for this session |
| --- | --- |
| `/sail` | every fairway nobody holds, every ready slice of each |
| `/sail fairway=<name>` | that fairway's ready slices; the rest are named as another fairway's and left |
| `/sail <feature>` | that feature's ready slices, across whichever fairways they are in |
| `/sail <slice-id>` | that slice, and nothing else |

A `fairway=` may be written with any of the others. Nothing here chooses a slice for you where several are
ready: rule 6 says run them concurrently, and that holds in every form but the last.

## Enter at the first incomplete stage

Read artifacts from disk rather than conversation memory and walk this ladder from the top. The entry stage
is the first one whose artifact is missing, empty, or still a placeholder — **including the stages upstream
of the slice loop**. State the entry stage and the evidence that selected it before changing anything, then
run that stage and every stage after it. Never rerun a completed stage merely to check. Where this project has
adopted a code index, a caller or blast-radius question is one call to it, by a route its block in `AGENTS.md`
names, and not a text search; grep is for words in documents.

**The checkout goes stale the way conversation memory does, so check the branch before the artifacts.**
Every signal the ladder reads — a slice's `status`, whether `examples.md` or `tasks.md` exists, the slice
graph — is a property of this commit, and a branch behind trunk reads exactly like a project where the work
was never done: a `/sail` fifty-seven commits behind wrote a second example map for a slice that had
shipped. So fetch and compare first — `git fetch`, then `git log --oneline HEAD..@{u}`, or against
`origin/main` where the branch has no upstream. Behind by anything, stop and say so rather than deriving:
the artifacts about to be read are not the project's current ones. The evidence line names the branch, its
head and its distance from trunk in the same breath as the stage. Where the fetch could not run — no remote,
or a remote this environment cannot reach — the line says *could not verify this checkout is current*, and
that never reads as *current*.

{{ladder}}

Being invoked before any of this exists is a valid start, not an error: it means the entry stage is near the
top of the ladder. Step back to that stage and say so rather than reporting that the request came too early.
Never invent a principle, specification, event, command, stream, or slice to skip a stage — a missing
artifact is work to do with the user, not a gap to fill from context. A stage needing a real product
decision is a stop.

## Who runs each stage

`.specify/models.json` says which model each stage runs on, by role: `strong` where a stage decides what to
build or whether it was built, `fast` where the input is already fully specified on paper — a plan into
tasks, `examples.md` into tests and code, a mutation run. Before running a stage, read its line:

```sh
python3 scripts/agents/models.py implement   # keyed by the command the stage runs; `{{make}} models` prints them all
```

The line chooses the model; it does not require that model to inherit this session's context. Prefer a fresh
sub-agent whenever the stage can get all of its inputs from artifacts on disk. Six stages are exactly that,
and each is a **named agent type** this project carries in `agents/`, projected into the installed harness by
`{{make}} agents` with its model and as much of its scope as that harness can enforce:

{{delegable-types}}

Every stage in that table is named for its purpose and then for the crew member who runs it, and every
stage that is not in it is named for the work alone — so the key says whether a stage has a delegate at all.
The gaps rung runs twice and only the pass after implementation is delegated: the pre-planning one may have
to ask a product question, which is the whole reason a stage stays here. Any other conversational stage stays
here too, and has no type for that reason. There is one more type, `sail-slice-watch`, for a whole slice
rather than a stage: *Running ready slices concurrently* is where it is delegated, and it reads this section
from inside its own worktree to choose a model for each stage it then runs. The last three rows,
`decide-skipper`, `demo-hand` and `unblock-bosun`, are `/cruise`'s: the product owner, the actor and the one
who gets a blocked run moving, delegated only when that command is running this ladder on its own
(`commands/cruise.md`). Under `/sail` alone they run nothing; a person is the owner and the actor.

Delegate to the type by name. The type is the standing brief, so the call adds only the task, its contract and
the file manifest — it never describes the role again or restates the scope, and it does not give the delegate
conclusions. It may give it a map: which precedent to copy, which decision in `research.md` governs, which
helper already exists — a file and a section, which the delegate then opens and reads for itself. Naming where
a fact lives is a pointer and costs a sentence; asserting what it says is a conclusion, and a brief that asked
the delegate to read a decision itself and report what it says has caught what a brief that summarised it got
wrong. Where a brief offers a delegate more than one way of working, every permission is written into each
mode that has it, even at the price of a repeated paragraph: a fresh delegate reads a silence conservatively,
and the conservative reading is the expensive one. The page each type is written on is `docs/delegated-agent-safety.md`, the standing boundary every
delegation is held to: reference it, restate none of it (`AGENTS.md`, *Delegated agents*).

**A delegate does not inherit this session's code-index connection, and needs none.** Where `AGENTS.md`
carries a code index's extension block, three of the types above — `sail-converge-navigator`, `sail-gaps-lookout` and
`sail-adversary-privateer` — are exploration-heavy, and *what does this code not yet do* is a blast-radius question the
index answers. Delegate them as the table says: a delegate reaches the index by the routes that block names,
which are the shell's and the harness's rather than this session's, so its brief's first route is one it has.
It names the route that answered, and falls back to text search only when the index says there is none. Never
pass the parent conversation merely to carry the connection.

Delegate both when the line names another model and when the same strong model can run in a fresh context.
On a harness whose agent file names a model (`scripts/agents/registry.json`, `agentFile`) the type already
carries the one the table resolved; everywhere else set it explicitly through the mechanism the registry
names, and never accept that mechanism's implicit default. If the harness cannot start a fresh sub-agent on
the selected model, run the stage here and say why. Then read its result from disk the way every stage is
read. Either way the stage says, in one line, which type ran it, which model, whether it was delegated and
whether its context was fresh (`sail-implement-shipwright · model: sonnet · delegated, fresh context` ·
`sail-adversary-privateer · model: host · delegated, fresh context` · `model: host, current context — harness cannot
delegate`). Those lines make type, model and context measurable; a stage that switched any of them silently
cannot be compared with one that did not. Nothing about what a stage produces changes with who runs it — the
artifacts, gates and stops are the same — and a sub-agent that meets a product decision hands the
question back here rather than answering it.

A stage is not always one delegate. Before delegating implementation, read `tasks.md` for its `[P]` markers and
its *Parallel opportunities* section: the tasks command writes both, and they are the plan for what may run
alongside what — written by one half of this workflow to be read here, not decoration. Every unchecked `[P]`
task whose files are disjoint from the batch already running is a concurrent sibling, delegated in the same turn
with a manifest of its own — and so is a task with no marker whose manifest shares no file with the batch. The
marker is the tasks command's reading of production-code contention, and it under-reports: one slice's list
marked one pair concurrent, said of the rest "none, by construction", and left two pairs that shared no file
to run in sequence. The manifests are the artifact; read them, and let only an overlap with a running
sibling's files, or what the section rules out, keep a task waiting. How many rules one delegate is handed
— a task, a rule or a user story — and how many RED tests each cycle opens with are `.specify/sail.json`'s
two settings (*How implementation is delegated* below), said in the stage line and put on the record. What the
section rules out stays sequential whatever the markers seem to allow — a RED-GREEN-REFACTOR increment starts
from a green, committed suite, and two of them at once is the batched-tests anti-pattern with a `[P]` on it.
The siblings are `sail-implement-shipwright` delegates, and that type is where the rule they cannot infer for
themselves already lives: **no concurrent delegate writes `tasks.md`**. It is the one file every sibling would
otherwise contend for, so each reports which task it finished and this session ticks the checkbox.

When several delegates form one batch, report once when the batch completes rather than once per delegate.
Verify their claims by spot-checking the recorded reproduction or RED evidence; do not repeat each complete
investigation in the host context. Do not re-investigate. **The spot-check is this session's, never a
reviewer's**: `sail-review-mate` reads the slice's whole diff once, after it converged (the *Review and
reshape* rung), and a return sent to it instead is a review the rung did not ask for and a fix round the
slice pays for — one run paid eight of each for nine pieces of coding. **And what is integrated is a
commit, named by its hash in the return**: `sail-implement-shipwright` commits each green increment locally and
reports the hash, and this session takes that commit into the slice's tree — `git cherry-pick` or a merge
from the delegate's worktree — never files copied out of a working tree, which is how a host once took a
sibling's files while its next rule was still RED and spent a verification run on the mixture. A return
that names no hash while its tree carries edits is refused at the boundary by the `after-delegate` guard
(`scripts/agents/session.py`) and goes back to the delegate; `no commit` with a reason is the honest empty
return and is not refused. A delegate that was stopped has filed nothing:
everything in its stop notification is a lead, never a result, and a lead is re-run before it is written
anywhere outside this session. An adversary pass is the same kind of batch:
disjoint-manifest seams of one pass are concurrent `sail-adversary-privateer` siblings in one turn, and the host
writes the log after the batch rather than re-attacking. It records the type and the explicit model that
ran each seam in `specs/<feature>/adversary-log.md`, especially when seams use different models.

The table is the project owner's to change at any point, and it is read before every stage rather than once,
so a change takes effect at the next stage — and rewrites the agent types, which carry the model on every
harness that reads one from a file: `/model-delegation-settings implement=strong claude.fast=haiku` edits it checked
(`commands/model-delegation-settings.md`, over `python3 scripts/agents/models.py --set`), or edit the file by hand and let
`make check-agents` hold the shape. When the owner asks for a different model at a stage, `/model-delegation-settings` is the
change — not a note, and not a switch made silently in the delegation. Commit the file: the choice is versioned with the project, and `slipwai
migrate` merges a newer factory's table over it rather than replacing it.

{{stage-costs}}
{{implementation}}
{{budget}}
{{hook-points}}
## Once inside the slice

Start the slice from a green `make verify`. During implementation, take one RED-GREEN-REFACTOR increment per
task — one rule of the example map with its examples, where the map numbers its rules — run only the quickest
relevant tests in the same file or area, commit that increment locally, and keep
task checkboxes truthful. A local commit is not a push: it does not run the full gate and it does not start
CI. Do not push increment commits until the hand's verdict on this slice's examples is green. Before an increment that changes a
shared function, ask this project's code index what calls it and what the change reaches — by the route its
block in `AGENTS.md` names, loaded by name where the harness defers a tool — and name those callers in the
delegate's manifest; a project that has adopted none answers with a text search and says so.

When the tasks are done, converge, then have the hand walk this slice's examples from the unpushed slice
branch and record its verdict. **Nobody is stopped here.** A person's demo is per capability and runs when
the capability's last slice has merged, which is usually several slices later; this rung proves the path
works, and the person is shown the whole thing rather than its instalments. After a green verdict — and only
then — a project that has adopted a code index brings it up to the tree, then the full
`make verify`, then the first push of those increment commits (and the merge that lands them on trunk).
That push is the integration boundary. A claim of `slice/<id>` at the start of the slice may still push a
lock ref from `main`; that is not the implementation.

{{demo-stop}}

### After the hand's verdict, and after Phase 4 clears

After a green verdict, run `/adversary`, which decides whether the slice changed attack surface or closed the
split and records the attack or the skip — `make check-decisions` holds every done slice to that row. Close the
adversary benchmark entry after its findings are triaged; implement confirmed defects through failing tests,
each in an `implement` entry. Then run `/mutation`, then `make verify`. `commands/adversary.md` owns the
trigger table; do not spawn before it is in the log. It records that decision in
`specs/<feature>/adversary-log.md` either way, so do not make it here. The order is not arbitrary: the pass
adds tests, and mutation measures whatever exists when it runs. Stop earlier only for a product decision or
unavailable input.

Once that evidence is clean, **continue on the same run**: mark the finished slice done —
{{done-marker}} — and confirm its
`plan.md`, `research.md`, `data-model.md`, `quickstart.md` and `tasks.md` are under
`specs/<feature>/slices/<id>/` with their relative links pointing at what they cite (they have been since it
was planned; a regular file still at the feature root is moved there now, and the canonical links dropped).
Then refill from the **ready** set as *Refill at every boundary* says — this is one of its boundaries and
not the only one — and re-enter the ladder at whichever stage each slice's own artifacts require, which is
usually its example map or its plan rather than the top. Do not wait to be invoked again.

**Ready-set selection** (which slices may start now, and whether this session takes one or all of them):

1. Read the slice graph — {{slice-graph}} — and which slices are **done**:
   {{done-marker}}. A slice with `plan.md` under `slices/<id>/` and no such mark is in
   flight, not done.
2. An open `CRITICAL` in `specs/<feature>/adversary-log.md` is the next slice, ahead of every ready
   product or method slice.
3. Otherwise **ready** = not done, every `depends_on` done.
4. If ready is empty, stop — the split is exhausted or every remaining slice is blocked.
5. If ready has one slice, claim it and take it.
6. If ready has several, **name the full ready set with each slice's state** —
   `python3 scripts/agents/clearance.py` prints it, and *Running ready slices concurrently* says what each
   state admits — split into *claimed* and *unclaimed* by the forge's `slice/<id>` branches, and start every
   unclaimed one in the band its state allows, in the same turn: a *preparation-ready* slice prepares, an
   *implementation-ready* slice implements. Nothing waits for its contract to be settled before preparing,
   because preparing is what settles it. Where the harness cannot delegate, claim the earliest in the
   ordered split for this session and leave the rest named, so another session can claim a sibling. Do not
   stop merely to choose among them unless the user asks.
7. **A fairway narrows all of the above.** Given one — `fairway=<name>` in this command's argument — ready is
   that fairway's slices and no other; the rest of the ready set is named as *another fairway's* and left.
   Given none, take the ready slices of every fairway nobody holds, and leave a fairway whose `held_by` names
   somebody else to them, naming its slices as *held*. *Fairways* below says where a slice's fairway is read
   from.

### Running ready slices concurrently

{{independence}}
So one session need not take one slice at a time. Fan out over the ready set when, and only when, the
four things below hold; the reference implementations of this method parallelise exactly this way, and
these are the primitives they add. The rules after them say how the fan-out is kept full, how a wait stays
local to the slice that is waiting, and what bounds it — each written down because a run followed the four
and still ran one slice at a time.

**It has clearance.** A ready slice runs alongside its siblings when every mark it steers by has
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

**Clearance is a state, not a yes.** For every slice `clearance.py` answers with one of eight words and the
sentence that says why, and the state is what decides what happens next, so read the word and not the
colour: *blocked* (which marks, and who owes each); *migration-evidence-required* (the setter shipped before
marks were logged, or a crossing's hold still stands — *Migrated prerequisites* below); *awaiting-decision*
(a `question` line stands open against it, or its fairway is parked, and which siblings the answer would
unblock); *preparation-ready*; *implementation-ready*; *running* (claimed, and in which band); *awaiting-demo*
(its capability is due a person's demo); *done* (merged). A slice with no clearance is not a stop — it is a
slice whose turn has not come. Name what it waits on and take a cleared one. A mark the chart declares that
*no slice sets* is a different thing and is a stop for the host: `make check-chart` refuses that chart, and
the sentence clearance prints says so.

**Two bands, and clearance admits a slice to one of them.** *Preparation* is the example map, the contract
files its marks name, and the gaps pass before planning — the stages that end with the slice's own
`mark-set` lines. It needs clearance and nothing else. *Implementation* is the plan onward: tasks,
increments, converge, the hand's verdict. It needs the slice's own marks set and no open question, which
is what *implementation-ready* means. This page used to say *run every ready slice whose contract is
settled*, and a slice settles its contract by preparing, so a host reading that waited on the one thing the
wait was stopping: two cleared slices with HTTP contracts still to decide sat idle for an afternoon while
their example maps, their route drafts and their gap reviews could all have been running. Preparation is
the band that *finds* the question; it is never the band that waits for the answer.

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

**Each slice has its own worktree and one delegate.** For every unclaimed slice the schedule starts, in
the same turn: claim it, give it a worktree (`git worktree add ../<project>-<id> slice/<id>`; on Claude Code
the Agent tool's `isolation: worktree` makes one), and delegate the band its state admits to one fresh
`sail-slice-watch` delegate (`agents/sail-slice-watch.md`, the standing brief) with a manifest naming the
**band** — `prepare`, `implement`, or `whole` — the worktree, the slice's block of the model, its
`examples.md`, and the shared-surface rule below. A *preparation-ready* slice is handed `prepare`, and its
delegate returns at the slice's `mark-set` lines; the same slice, now *implementation-ready*, is handed
`implement` by a fresh delegate that enters at the plan. An *implementation-ready* slice nobody has prepared
— one that sets nothing, or whose marks a baseline recorded — is handed `whole`. That type takes no stage's
model, because *Who runs each stage* still chooses one stage by stage inside the delegate, where `[P]` tasks
still fan out to `sail-implement-shipwright`: the two levels nest. Inside one slice the stages stay strictly
sequential. A delegate that meets a product question writes a `question` line to the deck log — `fairway`,
`slice`, `id`, `what` — records it in the slice's `plan.md`, and returns; the slice reads *awaiting-decision*
from that line until a `decision` carries the same `id`, and it is never guessed past.

**Refill at every boundary.** The ready set is not read once at the top and remembered. It is recomputed —
`python3 scripts/agents/clearance.py` again — at every one of these, and the free slots filled from what it
says: a delegate returning, prepared or converged; a `mark-set` landing in any log; a `decision` answering a
question; a demo verdict; a merge and its Phase 4 clearing; a claim refused because another session got
there. Each of those changes what may start, and a host that revisits its siblings only when its current
slice is finished is a host whose siblings waited for nothing. **Where eligible work waits with a slot free,
say why**, in the line that names the ready set: the schedule's own reasons are the only ones there are —
no slot, claimed elsewhere, claims unreadable, harness cannot delegate, fairway held — and *I had not
looked* is not among them.

**A wait is local to the slice that is waiting.** A question stands against one slice. Under `/sail` the
person is the owner: put the question to them — the `question` line, the slice's `plan.md`, and the line
that names the ready set, which says exactly which slices the answer unblocks — and **keep going**: the
independent siblings' delegates are still running, the slots the blocked slice is not using are filled
from the ready set, and the answer is taken at the boundary it arrives at. A demo wait is the same shape:
*awaiting-demo* is the slice's own state and never a sibling's, and a sibling's implementation never stalls
behind a demo it is not part of. Merges stay ordered within a fairway, as *Fairways* says; order is a rule
about merging and not about starting.

**Count the whole tree, and read the two numbers as the two things they are.** A whole-slice delegate
carrying `[P]` tasks is not one agent: it is one plus `fanout` (`harbour.json`), and the slices running at
once are bounded by `boilers`, so the harness is asked for up to `boilers × (1 + fanout)` agents at the
fan-out's widest. `boilers` bounds slices; `fanout` bounds the delegates inside one slice; neither is the
other, and a run that read the slice number as the delegate number dispatched two where it had room for
three and then wrote that the harness disagreed with the configuration. `python3 scripts/agents/clearance.py`
prints both on its second line, with the slots left and the tree they add up to — read it there rather than
from memory. **Inside a running slice the same duty holds at every boundary**: a `[P]` task or a
disjoint-manifest sibling left undispatched while `fanout` has room has one of these reasons, said in the
stage line — an overlapping writer, a RED-GREEN-REFACTOR cycle in progress on the same files, a `question`
it waits on, the stage's budget, or the harness's own limit — and *I had not looked* is not among them,
there either. Hold the product to what the harness
can actually run at once — its own limit, where it states one — and lower `boilers` before `fanout`, since
a slice that cannot start costs nothing and a slice that starts and starves costs the retry. Browser-driven
checks are bounded separately, by `browsers`: several worktrees are still one machine, and five Playwright
runs on it are not five times faster, they are slow one run and flaky the next. A delegate about to run one
waits for a `browsers` slot, in split order, and says so in its own lines.

**Migrated prerequisites.** A slice that shipped before this project logged marks has no `mark-set` line
and no line at all, and a sibling steering by what it sets is not *blocked* — it is told
*migration-evidence-required*, and nothing is cleared on the done marker's word. Record the evidence once:
`python3 scripts/agents/clearance.py --baseline-marks` writes a `mark-set` line to the harbour log for every
such mark, carrying `provenance: baseline` and what it was read from, so a reader can always tell it from a
mark a stage earned; a second baseline is refused, and a slice finished since writes its own line at its
own first stage.

**The shared-surface rule**, which the delegates cannot infer and `{{make}} check-slice-scope` holds on
every `slice/<id>` branch: a slice's commits touch its own `specs/<feature>/slices/<id>/`, the feature's
cumulative artifacts (`spec.md`, `story-split.md`, `contracts/`, `checklists/`, `adversary-log.md`, and
`decisions.md`, where `/cruise` records a decision taken during the slice), its own block of `model.yaml`
with the committed canvas `model.drawio` regenerated from it (`{{make}} model-drawio` — `check-drawio`
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
accepts. After acceptance: bring the code index up to the tree if the project has adopted one, `{{make}} verify`
green, then push the slice's commits and merge into `main` in split order — never in finishing order.
That is the first implementation push, and it is what starts CI. A slice converged and not yet accepted is
*awaiting-demo*; its siblings are not. The composition root and the cumulative
artifacts are where two merges meet, and split order is what makes those resolutions predictable;
regenerate the Mermaid diagrams (`{{make}} model`) after a merge, never in a branch, and the canvas
(`{{make}} model-drawio`) after each merge as well, taking both sides' blocks. No slice's Phase 4 runs until its demo is
accepted, and a sibling's demo never waits on another's Phase 4. Phase 4 itself — adversary, mutation,
`{{make}} verify`, marking the slice done — runs here, on `main`, one slice at a time. Delete the
`slice/<id>` branch once its Phase 4 clears: the claim is spent.

**Where the harness cannot delegate**, run one slice at a time here — claim the earliest in split order,
name the rest — and say so in the line that says which model ran (`harness cannot delegate`).

### Fairways

A **fairway** is one bounded context's slices, in split order, held by one at a time: a person, a `/sail`
session, a captain on another machine. Two fairways share nothing but **marks** — the contracts one sets and
another steers by — so a slice in one merges and demos without waiting on a slice in another, and a second
person or machine joins the work by taking a fairway rather than by racing for the next slice in one list. A
project with one context has one fairway, and nothing in this section changes for it.

**The chart names them, and nothing else does.** `specs/<feature>/chart.yaml`'s `fairways` block has one
entry per fairway — its context, its service, and the paths it owns — and each slice's entry names the
fairway it belongs to. `/chart` writes that on the standard profile and `{{make}} chart` renders it from
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
there is more than one, each with its own `N of M` and its `held_by`.

The stops are a required product decision, an input that is genuinely unavailable, a split with no ready
slice left in it, and the next slice's own demo. **A slice having finished is not one of them.**

Demo feedback re-enters the ladder at the stage that owns the change, which may sit well above the slice
loop. Re-derive the entry stage from artifacts instead of assuming the loop resumes where it paused.

<!-- section: push-check -->
### Before you push, name the release constraint

A push to `main` is a production deploy here: `verify` passes, `deploy.yml` applies staging, smokes it,
applies production and smokes that, with nobody in between. So the last thing before pushing is to say, in
the turn that pushes, what holds this change back from the actor — the flag key, and that it is `off` in
both environments.

**If nothing does — no flag, or a flag that is already on — stop and ask the user to confirm that this is a
release they want now.** Do not push and mention it afterwards, and do not decide on their behalf that the
change is small enough to be safe: there is no later gate at which somebody would catch it, which is the
whole reason the question is asked here. A refactor with no actor-visible behaviour is not a release and
needs no flag; say that it is one, rather than saying nothing.
<!-- end section -->

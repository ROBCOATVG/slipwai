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
investigation in the host context. Do not re-investigate. A delegate that was stopped has filed nothing:
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
Then select the next slice from the **ready** set and re-enter the ladder at whichever stage that slice's
own artifacts require, which is usually its example map or its plan rather than the top. Do not wait to be
invoked again.

{{ready-set}}

{{concurrent-slices}}

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

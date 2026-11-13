# Phase 25: stop the line, and nobody waits for an answer they needn't

Written 2026-11-13, from the game-club-manager run (`~/Documents/game-club-manager-new`), which built eight
slices on 2026-11-12 and merged one. Every stop in that run had one of three causes, and none needed a person.
Lands in 2.1 as a MINOR: every log kind it adds is new, and every path it moves is read at both places for
the MINOR (see 25.1).

## What the run showed

- **Run state leaks into every berth.** The ACP port (phase 22) writes `.slipwai/acp/<slice>/` and nobody
  added it to `RUN_STATE` (`src/slipwai/project/gitignore.py:16`). `check-slice-scope` then failed every
  berth on those files, and AC1 and AC2 parked themselves instead of asking to merge. The harbourmaster's
  own gate, in a clean worktree, would have passed them: CL1 asked anyway and was granted in seven seconds.
  The same project also has untracked `.slipwai/console/`, `.slipwai/stages/`, `surfaces.pid` and
  `model-next.pid`. It is the third time the list has fallen behind (`preflight.json`/`logs.unread-*`, then
  `activity/`, now these).
- **A red trunk found nobody to fix it.** CL1 was granted at 13:48:55 and CI went red at 13:49:22 (the
  scaffold's `event model` workflow uses `actions/upload-artifact@v3`, refused at *Set up job*).
  `broke_it()` (`harbourmaster.py:774`) looks for the captain's `merged` line, which the clubs captain wrote
  at 14:06 after its demo, so the harbourmaster wrote "nobody here broke it" and parked for a person. It
  writes once per change of state, so it never looked again. Meanwhile every other fairway kept building on
  the red trunk.
- **A cruising lane parked on a note.** `inbox.owed()` (`inbox.py:166`) forces a park when a `told` goes past
  `wait_bound`, or when unread decisions pass `decision_ceiling`, whatever the cruise settings say. CL1's
  13:08 note about the ignore file stopped the clubs fairway at 14:54. Accounts had 18 unread decisions
  against a ceiling of 10, every one taken by the skipper or the host's recommendation, as
  `decide: recommended-first` asks.

## 25.1 One folder for run state

Everything a run writes about itself, and nothing a checkout needs, goes under `.slipwai/run/`:
`logs/`, `running/`, `berths/`, `acp/`, `activity/`, `try-it/`, `walks/`, `console/`, `stages/`,
`catch-up/`, `catch-up.md`, `run-state.json`, `harbourmaster.json`, `intake-cleanup.json`,
`preflight.json`, `logs.unread-*/`, `*.pid`, `app.log`. The ignore block has one line, `.slipwai/run/`.
What stays at `.slipwai/` is committed: `dispatch/`, `extensions.json`, `hooks.json`, `guards.json`,
`quickstart.json`, `packages/`.

- One module owns the location (`RUN = ".slipwai/run"` in the keel, copied byte-identical into
  `assets/toolkit/scripts/agents/`, as `logs.py` and `berths.py` are). Every reader and writer goes
  through it. First step: an inventory of every string and `Path` join that names a run-state path.
- `make check-agents` refuses a write under `.slipwai/` outside `run/` that is not on the committed list,
  so the list cannot fall behind again.
- `slipwai migrate` moves the old paths in, rewrites the ignore block through `converge.respell`, and refuses
  while a fleet is out (a pid under `running/` is alive): moving live state under a running harbourmaster
  loses lines.
- The protocol MINOR: for 2.1, every reader looks in `run/` first and the old place second. Writers write
  only `run/`. 2.2 drops the old place. `docs/reference/the-logs.md` names the move.
- Stopgap for runs in flight now: add `acp/`, `console/`, `stages/`, `*.pid` to `RUN_STATE`.

## 25.2 Stop the line

minimumCD: a red trunk stops feature work, and fixing it is the next job.

- **`broke_it()` reads its own `granted` line**, which carries the fairway, slice and commit and is written
  at push time. `merged` stays as a fallback for older logs. A test replays this run's ordering: granted,
  trunk-red, merged 18 minutes later.
- **Stop the line.** On `trunk-red`, every captain stops at its next stage boundary, never mid-stage, and
  writes `held` naming the commit. On `trunk-green` it carries on, cleared by the harbourmaster's receipt as
  red-trunk parks are today.
- **A trunk mender** (`agents/sail-trunk-mender.md`), dispatched by the harbourmaster on `trunk-red`, in the
  harbour's own worktree. The brief carries the commit, the failed job and its log. In order: fix forward
  in code, else revert the merge that went red. Its change goes through the merge queue as the one request
  granted onto a red trunk, through the same `make verify` gate.
- **CI edits, setup failures only** (decided 2026-11-13). The mender may edit `.github/workflows/` only
  where no check ran: the run failed at *Set up job* or resolving an action. The diff may not remove, skip,
  `continue-on-error` or weaken any step, and a check enforces that on the mender's diff. A red from a check
  that ran is fixed in code or reverted, never in the workflow.
- `fix-trunk` to the breaking captain goes. A captain that broke trunk may be parked or gone (clubs was), and
  the breaking merge is often not the cause (here it was the scaffold's workflow).
- What still parks for a person: a red the mender's fix and revert both fail to clear, within `attempts`.

## 25.3 Fleet needs get an owner

A `need` with `by: fleet` (the `.env.example` lines, `docs/design.md` sections, a typed `post` in
`packages/api-client` in this run) has nobody assigned today. The trunk mender takes them too, between
reds: it lands each one on main through the merge queue from the file the slice left
(`slices/<id>/env-example-additions.txt`, `slices/<id>/design.md`), ticks the need with its `check`, and
the waiting slice's park clears. `by: person` needs stay a person's.

## 25.4 A cruising run parks only where it must

Under `decide: recommended-first` or `skipper-always`:

- A `told` is something to read, not a wait. It shows under *Waiting on you* and never forces a boundary.
- `decision_ceiling` does not park. The unread count shows on the board. The skipper taking decisions is what
  the setting asked for.
- A fairway parks only for what no agent may supply: a secret or credential, spending, ratifying the
  constitution (where `constitution: ratify`), turning a release flag on, a `by: person` need, and the
  bosun's catastrophic list.

Outside cruise, nothing changes: the wait bound and the ceiling park as they do today.

## Order

25.2's `broke_it` fix and 25.1's stopgap first, since both are small and unblock runs in flight. Then 25.4, then
25.2's stop-the-line and mender, then 25.3, then 25.1's move.

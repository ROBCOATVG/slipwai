MINOR

**The loop's memory travels, and `/sail` is what makes it.** `travel.py` has carried the deck logs, the
harbour logs and the in-flight slice branches between machines since it was written — one ref per writer,
nothing ever merged, a push that is not an append refused — and only `captain.py` ever called it. So a
person's `/sail`, a cloud session and a second machine each read the plans out of git and none of the
history, which is a project where nothing has been started: one run saw six slices as unstarted that
another machine had prepared that morning, rebuilt their work on trunk, and left eight worktrees nobody
could reach. `make arrive` lands what other machines wrote and `make depart` pushes what this one
did; the ladder runs the first beside its own `git fetch` and the second at every boundary it already has.
The harbourmaster now calls the same two functions, so the credentialled process and a plain session
cannot travel by two different rules.

**A session is told when it cannot run the method, instead of discovering it.** The delegate types are
derived from `agents/` into each harness's own directory, and git ignores those — correctly, since they
are a second copy of a committed source — so a fresh clone has none and a session there reads a ladder
built on delegates with nothing to call. `scripts/agents/project.py --check` passes on that by design, and
cannot do otherwise: it cannot tell a clone nobody will run `/sail` in from one somebody is about to.
`make preflight` can, because it runs when a slice is about to start, so it now asks two more
questions — are this harness's delegate types projected here, and does this harness have sub-agents at all
— and `scripts/agents/harness.py --can-delegate` answers the second from the registry. Thirty of its
thirty-six rows cannot delegate, so that answer is recorded and never failed; a missing projection is
failed, and names `make agents`.

**What was dispatched is written down at the moment of dispatch.** `make dispatch` records one line
per slice in `specs/<feature>/dispatch-ledger.jsonl` — the slot, the worktree and the delegate, or
*taken-here* and *left-named* with the recorded reason this session could not delegate. Committed, unlike
the deck logs, because it is evidence about a commit and the gate that reads it runs on a checkout holding
only what git carries. It will not write a line without a current `preflight --record`, so a run that
skipped the check has nothing to dispatch with rather than a judgement to record.

**The crossing's own catch-up is taken, not asked for.** A slice that shipped before the mark log existed
set nothing in it, so everything steering by its marks reads as blocked for ever —
`clearance.py` calls that `migration-evidence-required` rather than `blocked` for exactly that reason.
`make dispatch` now takes the baseline when it sees that state, re-reads clearance, and records a
`baselined` line in the ledger so the run says what it stood on. Safe to automate for the reason it was
safe to write down: it derives from the done markers already in the tree, stamps every line
`provenance: baseline`, and refuses a second baseline outright, so automating it cannot turn it into a way
past the gate. `make hooks` is the same shape — idempotent, never takes a path somebody else owns — so
`make dispatch` depends on it and every clone, worktree and cloud runner gets it without being asked.

**And one gate holds whoever is driving.** `scripts/check-dispatch.py` reads commit subjects up to their
first colon and refuses two things: a slice-shaped token no chart, event model or `slices/` directory
knows, and a planned slice no dispatch ledger accounts for. It is on `verify` and in a `pre-push` hook
that `make hooks` installs, because every other rule in the method is one a session has to choose to
read — the command page is prose, `verify` runs when something runs it, and the session-start guards reach
three of the registry's thirty-six harnesses. Git reaches all of them. Decision ids (`D49`) and task ids
(`T018`) are excluded by shape, and a project with no plan at all — an adopted repository before its first
chart — is not held.

**The hook path is set by the thing that makes the checkout.** `core.hooksPath` is per-checkout git
config, so it travels with no clone, worktree or cloud runner — which would have left the one rule that
holds whoever is driving installed nowhere, the same shape as the bug it catches. Generation sets it, and
`slipwai migrate` sets it for a project that predates the hook. A path somebody else owns — husky,
lefthook, an adopted repository's own — is reported and never taken.

**And `make crossing` asks what a migration could not carry.** The merge carries the files; it cannot
carry the state those files are about. One project migrated cleanly and twenty minutes later had a chart
covering the first of its two features, eleven slices still `modelled` that were built and merged, a log
ref the design names and nothing had ever created, and no hook path — and had passed every gate it had.
`scripts/check-crossing.py` asks the six questions out loud: a chart per feature, every slice folder named
in one, statuses against trunk, a mark recorded for what already shipped, somewhere for the logs to
travel, and this checkout's hooks. A report by default, `--strict` to fail, because a project mid-crossing
is not a broken project and a command that refused to run is one nobody runs twice.

**Clearance refuses a feature it cannot answer for.** It takes the first feature with a chart, so a
project with two features and one chart answered for the charted one *whatever it was asked about* — and
a `/sail` on the uncharted one read every slice of the other feature as queued or blocked and took that
for *nothing may start*. A named feature with no chart is now `cannot schedule`, naming what is charted;
answering for one feature of several says which it is not about.

**Catch-up:** `slipwai migrate` carries `travel.py`, `preflight.py`, `harness.py`, the new
`scripts/agents/dispatch.py`, `scripts/check-dispatch.py` and `scripts/check-crossing.py`, rewrites
`commands/sail.md`, adds `check-dispatch` to `verify`, and points this checkout at `.githooks`. **Run
`make crossing` after it** for what no command can take for you — a chart per feature, statuses against
trunk. CI holds the push rule for every push a local hook never sees. A project whose
shipped slices predate the ledger will have `check-dispatch` refuse a commit naming one: either the slice
is already merged and the commit is prose about it (no slice-shaped token before the colon), or record
what was dispatched. A feature with no `chart.yaml` is unknown to both gates — `make chart` first, or its
slices read as work no plan knows.

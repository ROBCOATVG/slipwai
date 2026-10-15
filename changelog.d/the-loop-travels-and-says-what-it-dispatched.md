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

**And one gate holds whoever is driving.** `scripts/check-dispatch.py` reads commit subjects up to their
first colon and refuses two things: a slice-shaped token no chart, event model or `slices/` directory
knows, and a planned slice no dispatch ledger accounts for. It is on `verify` and in a `pre-push` hook
that `make hooks` installs, because every other rule in the method is one a session has to choose to
read — the command page is prose, `verify` runs when something runs it, and the session-start guards reach
three of the registry's thirty-six harnesses. Git reaches all of them. Decision ids (`D49`) and task ids
(`T018`) are excluded by shape, and a project with no plan at all — an adopted repository before its first
chart — is not held.

**Catch-up:** `slipwai migrate` carries `travel.py`, `preflight.py`, `harness.py`, the new
`scripts/agents/dispatch.py` and `scripts/check-dispatch.py`, rewrites `commands/sail.md`, and adds
`check-dispatch` to `verify`. Run `make hooks` once per checkout — git config is not cloned, so a
cloud runner and every new machine need it, and CI holds the same rule for the pushes it never sees. A
project whose shipped slices predate the ledger will have `check-dispatch` refuse a commit naming one:
either the slice is already merged and the commit is prose about it (no slice-shaped token before the
colon), or record what was dispatched. A feature with no `chart.yaml` is unknown to the gate — `make
chart` first, or its slices read as work no plan knows.

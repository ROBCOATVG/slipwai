MINOR

**Slices are arranged into workstreams by bounded context, so several people and machines can deliver at
once.** The ladder already decides which service and bounded context own each slice, at the event model and
the plan, and `make check-slice-scope` already holds a slice branch to its own context; nothing downstream
read that to decide what may run and merge independently. Now a **workstream** is one context's slices in split
order, held by one runner at a time. `/story-splitting` writes a *Workstream* column into the slice graph and a
`## Workstreams` table (context, slices in order, `held_by`) wherever the slices fall in more than one context.
`commands/drive.md` gains a *Workstreams* section: merges stay in split order within a workstream and are
unordered across; a workstream's demo and release constraint never wait on another's; the ready set is grouped
by workstream and a workstream somebody else holds is left to them; `/drive workstream=<name>` takes one.
`scripts/agents/cruise.py run` and `start` take `--workstream <name>` (`make cruise WORKSTREAM=<name>`), carry
it as `workstream=<name>` on every iteration, and record it in the log, so two runners on two machines are two
workstreams and the `slice/<id>` claim stays the mutex between them. The progress board in `/drive`'s demo stop
and `/where-are-we` groups ⬜, 🔀 and ➡️ by workstream with a count and a holder each, and the completion
audit runs per workstream before it runs across them. A project with one bounded context has one workstream
and sees no change.

**Catch-up.** `slipwai migrate` brings the commands, the skill, the runner and the Makefile target whole. A
split already written in a project with more than one context gains a `## Workstreams` table only when you
add one; until then every slice is in one workstream, exactly as before.

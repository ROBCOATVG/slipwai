MINOR

**A capability built on a stand-in is a release blocker, not a finished one.** A capability whose path to its
actor runs through a stand-in — a no-transport or drop-directory mailer, an empty source, a fake — now says so
in its `gates.md` with a `Stand-in: <port> · <adapter> · <the missing piece>` line, and a screen the hand's walk
could not reach from seeded state with `Unreached: <screen> · <why>`. A slice of it whose `try-it.json` is empty
counts the same. Any of these keeps the capability out of done whatever `Cleared:` says:
`capabilities.py --blocked` lists it, no demo is owed and neither the hand nor a person can accept it, and the
board says *Merged, not done: … built on a stand-in* where it would have said *Built*. It ends when the stand-in
is replaced and its line removed, or when a person adds `· Accepted-by: <who> <date>` to the line to say the
stand-in is the intended behaviour; an `Accepted-by:` naming an agent is not read. The plan rung and `/chart` now
ask for a missing cloud resource — a sending domain, an IAM grant, a queue — once and early, as one bundled
question to a person, and have the slice build the real, contract-tested adapter behind the port so only the
grant is missing. A story's `given` may name the fields its product seals and the key it seals them under,
`"seal": {"key": "<whose key>", "fields": ["<field>"]}`, and `check-try` holds that to the event's data and the
model; the language package's seed door does the sealing. A project that cleared an email capability on a stand-in
found the BD was never told in any environment, and its founder screens were proven only by tests.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/capabilities.py` and `scripts/agents/try_it.py`
and the new `/sail` and `/chart` pages. Then add a `Stand-in:` line to the `gates.md` of each capability that
already cleared on one, and an `Unreached:` line for each screen its walk never reached, so the board shows
them as release blockers.

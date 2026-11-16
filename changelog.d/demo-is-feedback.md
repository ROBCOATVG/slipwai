MINOR

**Nobody is asked to accept a demo by default: the hand's verdict is the acceptance, and the film is an
opportunity to say what it showed.** `.specify/cruise.json` has a new setting, `demos`: `hand`, the
default, or `person`. Under `hand` the hand's `accepted` at a capability's walk accepts the capability —
`python3 scripts/agents/deck_line.py accepted --capability <name> --by sail-demo-hand` writes the line —
its slices read as done, nothing is listed as waiting on a person for it and nothing parks. The film on the
Voyage tab offers **Say what it showed**, which opens the Feedback box with the capability on it, and no
Accept or Not yet. Under `person` the board is as it was: `deck_line.py demo-due` makes a capability due,
the film says *Ready for you*, and the Feedback card offers Accept and Not yet; an `accepted` line the hand
wrote is the last reading before a person's and closes nothing. A verdict of `behaviour` or
`implementation` re-enters the ladder or becomes a task under either, as before.

Before this, nothing wrote `demo-due` or `accepted` at all — `deck_line.py` wrote only `mark-set` and
`demo` — so a capability the hand had accepted was never accepted anywhere: `capabilities.py` listed it as
owed a demo for good, and the Voyage tab's last stage said no capability had been demoed. Both lines now
have a door, and both are refused unless the capability is whole and its gates record says `Cleared:`.
`deck_line.py` writes only the hand's acceptance (and `demo-due` only under `person`); a person's is written
by the board when they press Accept, so no session can accept as a person. Under `hand`,
`capabilities.py --due` says nothing is owed a person and lists what still owes the hand's line. The setting
is on the board's **Settings**, **Who answers** tab, as *A capability's demo*, beside the other stops, and
`/cruise-settings demos=person` sets it in the agent. The demo stop is the one place that says how an
acceptance is written; the hand protocol, the cruise page, the stops table, the hand's brief, the captain's
line table and the board guide point to it.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/` and command pages. A project with no
`demos` in its `.specify/cruise.json` reads as `hand`; set `demos=person` with `/cruise-settings` to keep a
person accepting each capability. Nothing to run per capability: under `hand`, a whole, cleared capability
whose `demo-log.md` ends on the hand's `accepted`, or whose every slice has a register row naming
`accepted-by: sail-demo-hand`, reads as accepted where no `accepted` line exists.

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
have a command. The setting is on the board's **Settings**, **Who answers** tab, as *A capability's demo*,
beside the other stops, and `/cruise-settings demos=person` sets it in the agent. The demo stop, the hand
protocol, the cruise stops table, the hand's brief, the captain's line table and the board guide say the
same.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/` and command pages. A project with no
`demos` in its `.specify/cruise.json` reads as `hand`; set `demos=person` with `/cruise-settings` to keep a
person accepting each capability.

MINOR

**The specification, the storyboard and the event model can advance on their own.** Each of those steps ends at
a stop: the board shows what was made, and a person presses the next step's button or approves the
storyboard. A new stop on the board's Settings card, *The specification, storyboard and model*, switches
that between **stop for me at each**, which is what a project does today and stays the default, and
**advance on their own**. Advancing, the board draws the storyboard once the specification is drafted,
approves the storyboard once it is drawn, models it on an event-modelling project, and continues the build,
each as the step before it ends well. A step that failed, a disapproved storyboard, and anything the board
is already running each stop it as before.

An approval given this way says so: the first line of `mock-states.md` names the setting, so a verdict the
board gave can be told apart from one a person did. It is `upstream` in `.specify/cruise.json`, and
`python3 scripts/agents/cruise.py --set upstream=advance` sets it from a terminal.

The board advances when it is polled, which every open board window does every few seconds; with no window
open it waits until one is.

**Catch-up:** none. A project whose `.specify/cruise.json` has no `upstream` reads it as `park`, and its own
`make check-agents` still passes; setting it writes it in.

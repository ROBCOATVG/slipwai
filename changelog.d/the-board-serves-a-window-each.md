MINOR

**The board serves a window each, so two projects at once is a thing a person can do.** It kept `root` on
its handler class, so a second window opened on the same board looked wherever the first one had pointed it,
and a generate in one tab moved every other tab with it. A window now carries a seat — minted on its first
load and held in its own address, because a cookie is one per browser and not one per window — and where it
is looking is the seat's. What is *under way* in a project stays keyed by the project: two windows on one
tree share its `./init` and its cast-off, which is what has always stopped a fleet being cast off twice.
`slipwai --root <directory>` reaches the window now too; typed at a board that was already serving, it was
dropped.

**A run is watched in a window of its own.** The Voyage has left the tab bar. The board is where a person
points somewhere, starts a project, adopts a repository and installs a language; a run is the one product
they are watching, which is a thing to leave open on another screen rather than a tab to lose by pressing
Packages. The project's card opens it, named, so it arrives pointed at the right tree, and the window is
titled for the project so two runs are told apart in a dock.

**The strip says what to expect of the stage it is on, and whether that stage stops for you.** A stage that
waits for a person by design looked exactly like one that had hung, and nothing on the page said which it
was. Every stage now carries that sentence — roughly how long, and who it waits on — with the stage being
worked given its own space above the rest.

**The mock-up review is a stage of the strip.** It was running in the ladder and the strip never named it,
so a person waiting on a storyboard was waiting on something the page did not mention. It stands between
the specification and the event model, where `project/ladder.py` has it and for its reason — the screens
are what the modelling conversation is held over — and it is read from the states a person marked in
`specs/<feature>/mockups/mock-states.md`: amber while one is parked, with the count of what is approved. A
stage this profile has not got no longer prints a file the project will never have.

**Who answers at each stop of a run is on the page, and can be changed while it runs.** `/sail` and
`/cruise` were never one switch: `/cruise` runs the same ladder and differs only at the stops, and
`.specify/cruise.json` already answered each separately — `park` on one *is* `/sail` for that stop. The
Voyage shows all four with what each answer means, says in a line which of them this run will stop for you
at, and writes a change through the project's own `scripts/agents/cruise.py`, which is what
`/cruise-settings` runs and what `make check-agents` holds. A captain reads it at its next boundary.

**And the fleet can be stopped from the page it is watched on.** `make cruise-stop`, beside Cast off: it
asks rather than kills, so a captain finishes the stage it is on and leaves its worktree, its branch and its
deck log in a state the next cast-off picks up.

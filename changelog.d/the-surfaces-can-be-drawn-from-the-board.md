MINOR

**The Voyage keeps itself current, and the stage between a specification and a model has a button.** Two
faults in one window, both found watching a real run stop with nothing to press.

**The page went stale.** Its poll repainted the strip and gave up the moment nothing the board had started
was running — and the stages that move a project on are run in the agent, by a person, which the board is
never told about. Worse, the cards are rendered once: the specification landed under an open window and the
Open spec button, the storyboard, the model and the work were all still drawn from the files that were
there when the window opened. The poll now carries a signature of what the page was built out of, slows to
every eight seconds when nothing is moving rather than stopping, and reloads the window when the signature
says the page is built from different files than the ones it was drawn with.

**Draw the surfaces**, beside Continue the build, runs the half of the mock-up review nobody has to be
present for: `make surfaces` (`scripts/agents/surfaces.py`) starts one headless session with
`commands/mockups.md` as its rules, which researches the surfaces the specification implies, draws a
wireframe for each and storyboards them — and stops there. Nothing is marked approved by a session nobody
was in: the verdicts are what the stage is for, and `/mockups <feature>` in the agent walks a person
through them with the drawings already in front of them. The button is gone once there are drawings,
because what they wait on then is a person. The strip says so too — surfaces drawn and no verdicts written
now reads **Waiting on you** rather than *to do*, which is what it said while a person was the only thing
holding the project up.

**Catch-up:** `slipwai migrate` carries `scripts/agents/surfaces.py`, the `surfaces` Makefile target and
`commands/mockups.md`'s dispatched half into an existing project. The board's own change needs no
migration — but a board kept running by the login service is still serving the code it started with, and
`slipwai bridge install` restarts it.

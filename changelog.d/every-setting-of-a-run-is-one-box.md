MINOR

**Everything a run is set to is one box with a tab each, and two of the settings now have a control at
all.** Speed and Fine tune were two cards; who answers at each stop was a third; and the two files the
ladder actually reads had nowhere to be seen — `.specify/sail.json`, how much one implementation delegate
is handed and how many failing tests a cycle opens with, and `.specify/models.json`, which role each stage
runs under. Both were a command typed into an agent by somebody with the board open in front of them.
Asking "what is this run set to" was asking four questions in four places.

The Settings card carries all five: **Speed**, **Fine tune**, **Who answers** (`/cruise-settings`),
**Delegation** (`/sail-settings`) and **Models** (`/model-delegation-settings`). Each panel names the file
it writes. The telegraph's two tabs are the board's own and are always there; the other three appear only
where the project has that file, because a tab offering to set a file that is not there would be a control
that refuses every press.

**Written by the project's own scripts, never by the board** — the rule the stops already followed, now
also for `scripts/agents/sail.py --set` and `scripts/agents/models.py --set`. Each validates against the
same table the board renders from and `make check-agents` holds both files' shape, so there is no second
writer to drift from the project's own checker. Which roles a stage is offered is read from the project
too: `models.py` accepts any role name, so offering one this project has not mapped would be offering a
fall-through dressed up as a choice.

**The tabs are radio buttons and a stylesheet.** The published copy of a board is one file with nothing to
press and therefore no JavaScript, and a box whose tabs only worked on the served copy would be the two
copies disagreeing.

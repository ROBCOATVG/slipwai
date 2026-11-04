# The brief, as a mock

The mock that [the prototyping plan](../../prototyping-plan.md) is drawn to: one session in a prototyping
tool, the folder it exports, and what the board does with it. The clickable copy is at
https://claude.ai/artifact/GGdVnjrQzATQi1nUSDj9WM; these are its sources, kept here so the design is in
the tree beside the plan the way `../ledger-bridge.html` is beside the board's.

They are artboards for a design canvas, not pages that open on their own: each `.dc.html` is one frame,
`canvas.json` is the index that places them, and the `{{holes}}` and `<sc-if>`/`<sc-for>` tags are filled by
the canvas's runtime from the `renderVals()` in each file's script block. Read them for the markup, the
tokens and the states; open the link to press anything.

| Frame | What it shows |
|---|---|
| `Main.dc.html` | Describe it: the conversation, the brief counting itself up, and the prototype Sam plays, embedded |
| `States.dc.html` | Walk the states: one surface, seven states, who decided each |
| `Handover.dc.html` | Check and hand over: the plain-words check Sam sees, the folder and the state markup the developer sees |
| `Slipwai.dc.html` | The Voyage page after the brief arrives: four ticks from the folder, the storyboard waiting, approve or park |
| `Prototype.dc.html` | The club boat bookings prototype itself, as a phone: book, cancel, sign in as the bosun |

Boards 1 to 4 sit on the board's own tokens (`src/slipwai/page_shell.py`): IBM Plex, teal and brass, the
ink and rule greys, 8px controls and 12px cards. The prototype keeps the club's own blue, because that look
is the brief's and not slipwai's.

PATCH

**Two windows on one conversation see the same turn.** A page polled only while it believed the agent was
busy, so a turn started from another window never showed, the box stayed open, and a message sent into it
was refused with an error bubble each time. The first page and the console now poll quietly while idle,
and a message that lands during another window's turn is answered as a wait rather than a refusal: the
box greys, says *Answering…*, and the turn appears as it goes. The agent's words render their little
markdown — bold, code, bullets — as nodes, never as HTML, instead of as raw asterisks.

**Catch-up:** nothing; the board is served from the installed command.

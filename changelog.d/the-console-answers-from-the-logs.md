MINOR

**The Voyage window has a console for asking the harbourmaster.** A button at the bottom-right of every tab opens a chat panel: ask why a fairway is waiting on you, what the fleet is doing, or what happened in the last hour, and a read-only session of your coding agent answers from the project's logs and the board's own fold of them. It can read and search files and nothing else — it cannot change a log, grant a request or clear a park, and it names the control on the board that does. The conversation is kept by the session, so a reload shows it again; `New conversation` starts another.

It needs Claude Code (`claude`) on the `PATH` of the shell that started the board, and says so where it is not. Each question is one agent call.

**Catch-up:** nothing in the project: the console is the board's, which is the keel's. Restart a running `slipwai bridge` after `slipwai upgrade` to get it.

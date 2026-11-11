PATCH

**On Windows a conversation no longer stops at the first `❌` the agent reads.** The board read an agent's
stream in the platform's own encoding, which on Windows is cp1252, and five bytes of UTF-8 mean nothing in
it. The first file the agent read that held one — a `❌`, a `”` — ended the board's reader mid-turn: the
page showed the session stopped while the agent worked on unseen, and the next thing said was answered
*The session ended with status 1 and said nothing*. The stream is now read as UTF-8 everywhere — the
sketch, the console, and a session over the protocol. Nothing changes on macOS or Linux.

**Catch-up:** nothing; the board is served from the installed command.

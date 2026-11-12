PATCH

**The app on Windows no longer opens a blank terminal for what it starts.** The app is a windowed program,
and Windows gives a console program started by one a console of its own, and shows it: every agent session
and every `git` opened a terminal window that stayed blank, because its output goes down a pipe to the
board. It looked stuck, and closing it ended the session. The app's children are now started with no
window. A window somebody asked for — the sign-in, *Open a terminal here* — still opens, and `slipwai` run
from a terminal is unchanged, as is everything on macOS and Linux.

**Catch-up:** none.

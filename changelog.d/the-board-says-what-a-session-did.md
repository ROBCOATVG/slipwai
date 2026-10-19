PATCH

**The board says what a headless session is doing, not only which tool it reached for.** A session redrawing
eleven screens read as a column of `→ Write`, `→ Write`, `→ Bash`. Each line now says what it acted on: the
file, relative to the project, with a run of writes listed under one name; a shell command's own
description; the task a delegate was given, with that delegate's own calls indented beneath it; the page a
browser opened; the workflow by name. A delegate or a shell left running in the background says when it
finishes, the todo list shows as a count and the item in hand, and the harness's own plumbing — finding a
tool, scheduling a wake-up — is left out.

**Catch-up:** nothing to do; the board does this for every step it runs. A board kept running by the login
service is restarted by `slipwai bridge install`.

PATCH

**The board's console finds `claude` when the board was started at login.** Started by launchd, the board has
launchd's bare `PATH` and no `SHELL`, so the console looked for `claude` there, did not find it, and said there was
no `claude` on this machine. It now asks the account's login shell for its environment, once a conversation,
looks `claude` up on that `PATH` and runs it with that environment.

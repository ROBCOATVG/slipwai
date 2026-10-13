MINOR

**`slipwai bridge --at-login` keeps the board running, so the installed window is worth installing.** A
browser will not let an installed page start a server, which is why the window shows "nothing is serving
the board on this machine" whenever nobody has typed the command. The other end of that problem is the one
that can be solved: this writes your own account's login service — a launchd agent on macOS, a systemd user
unit on Linux, a file in the Startup folder on Windows — and starts it, so the board is simply up. No root,
no daemon, no installer, and `--no-at-login` removes it.

It obeys the one-board rule like everything else here: finding a board already serving, the service ends
rather than binding a rival, and says so at install time rather than leaving you to find out. `slipwai
bridge --serve` is what it runs — serve, open nothing, and do not insist the directory is a project yet,
because a login service starts before there is one and the page attaches anywhere.

**Catch-up:** nothing, and nothing is installed unless you ask for it.

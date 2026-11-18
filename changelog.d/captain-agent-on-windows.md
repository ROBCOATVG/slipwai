PATCH

**The captain agent, the board's cards and the captain's own reads work on Windows.** The captain-agent stream
had only run on macOS and Linux. On Windows it failed in several places:

- **The captain's agent never started** (`[WinError 2]`). Its command was split as POSIX splits it, which
  drops a Windows path's backslashes. It is now split as a slice's agent command already was.
- **The board's slice and captain cards crashed.** They formatted dates with `%-d`, which Windows refuses.
- **The captain was refused its own events.** The check for what lies under its run folder appended a
  `/`, and a Windows path has none.
- **A process probe killed what it asked about.** `drive.alive` used `os.kill(pid, 0)`, which Windows
  treats as a Ctrl-C. It now asks the process handle, as `fleet.alive` already did.
- **Ending an agent left what it started running.** A tree is now ended with `taskkill /T`.
- **A print-mode harness installed by npm would not start.** It is a `.cmd` shim, which a bare name does not
  find. It is now looked up on PATH first, on Windows only.
- **The pruner's `git check-ignore` read `target\r`.** Its input and output are now NUL-separated.

macOS and Linux run exactly as before.

**Catch-up:** `slipwai migrate` carries the changed `scripts/agents/` files, `scripts/check-dispatch.py` and
`scripts/backing-services.py`.

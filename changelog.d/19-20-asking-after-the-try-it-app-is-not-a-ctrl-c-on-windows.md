PATCH

**Asking whether the try-it app is still running no longer sends a Ctrl-C to the console on Windows.**
The Try it card and the toolkit's `try_it.py` asked with `os.kill(pid, 0)`, which on Windows is
`CTRL_C_EVENT` to every process sharing the console: the board asking after the app interrupted the session
that asked, and the gate's own suite with it. Both ask through the process handle now, as the fleet already
asks after a captain.

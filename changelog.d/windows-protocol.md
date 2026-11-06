PATCH

**The protocol's tests run on Windows, and a drive's variable keeps a Windows path whole.** `SLIPWAI_ACP`
was split the POSIX way, which read a path's backslashes as escapes and dropped them. The stub agent the
suite drives speaks in forward slashes on every platform, a fake `npx` is one Windows can find, and a mode
bit is only asked about where one exists.

**Catch-up:** nothing a project runs changes on a POSIX machine.

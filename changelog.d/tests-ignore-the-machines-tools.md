PATCH

**The keel's suite no longer depends on what the app has installed on the machine running it.** Two tests
failed on any Mac where the app had chosen an agent or installed a tool under `~/.slipwai/tools`: one
expected the login shell's `PATH` alone, and the other expected no agent at all. Both now stand in for the
machine's settings and installed tools, so they pass the same way locally as in CI.

**Catch-up:** nothing; tests in the keel's own suite.

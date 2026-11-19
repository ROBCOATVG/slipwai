PATCH

**A test of the board no longer fails at random on a slow runner.** A start page asks `git`, `node`,
`python` and `make` for their versions before it answers, and the board the suites drive asked the
runner's own: one Windows run took twelve seconds over that while the test's window waited five. A board
under test now has a machine that lacks nothing unless a case says otherwise. Its server is also stopped
before its socket is closed, where it was closed first — the `WinError 10038` a Windows log carried once
a case, from a thread still selecting on a socket that had gone.

**Catch-up:** nothing; it is this repository's own tests.

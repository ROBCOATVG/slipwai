PATCH

**The app's own board finds the tools it installed too.** The fix that put the board's tools on its own path
was made where the command and the login service start a board, and not where the app opened by a
double-click does — which is the board a person on Windows has. *Generate* there still made the project and
answered `[WinError 2] The system cannot find the file specified`. It is now done at the one place every
board is started from.

**Catch-up:** none.

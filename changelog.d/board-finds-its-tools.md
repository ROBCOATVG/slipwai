PATCH

**The board finds the tools it installed when it runs one itself.** On a machine whose only Git was the one
the board installed, *Generate* made the project and then answered `[WinError 2] The system cannot find the
file specified`, and `./init` never started. The tools the board installs are put on the path of the
children it starts, but the board also runs `git` itself, by name — is there a remote, what is committed —
and a bare name is looked for on the board's own path, where its tools were not. They are now on the end of
it from the moment the board starts, and from the moment one is installed, so nothing of the machine's own
is passed over.

**Catch-up:** none.

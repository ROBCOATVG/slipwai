PATCH

**`./init` started from the board is given the login shell's environment.** A board started at login has
`PATH=/usr/bin:/bin`, and the `./init` it started with that found neither brew, uv, Spec Kit nor the
cloud's own tools on a machine that had every one of them, then fell through to the system pip and a
Python too old for Spec Kit. The generate child already got the login shell's `PATH` and exports; now the
handover child does too.

**Catch-up:** nothing — rerun `./init` from the board, or in a terminal, where it stopped.

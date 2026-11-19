PATCH

**No test of the board asks the machine running it for its tools any more, whichever suite starts the
board.** One board fixture had been given a described machine; three other suites started boards of their
own and still asked the runner's `git`, `node`, `python` and `make`. The described machine now stands in
for every board a suite starts, from the one module all of those suites already import, and a test starts
a board with no fixture at all and fails if the real machine is what answered. The four suites also start
and stop their boards through one helper: stopped, its thread seen out, then closed.

**Catch-up:** nothing; it is this repository's own tests.

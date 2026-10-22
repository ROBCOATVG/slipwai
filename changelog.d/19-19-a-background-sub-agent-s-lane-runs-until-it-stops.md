PATCH

**A sub-agent the harness runs in the background has a lane as long as its work, not a sliver.**
The harness answered each delegating call the second it was made, so the window read `done` in the same
second as `start` and drew LB8's four implementing sub-agents as one-letter slivers while they wrote a
hundred and thirty lines between them, and the person reading it saw very little implementing going on.
A `done` that soon after its `start`, before the harness has named the sub-agent, is now the launch, and
the harness's own stop event — `SubagentStop`, a new hook — writes the `done` that ends the lane under the
sub-agent's own name. A log with no stop line, written before the hook existed, ends a launched sub-agent
at its last line once it has gone quiet, and keeps one still writing as running.

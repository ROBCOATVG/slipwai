MINOR

**The board shows each process, why it left, and what would start it.** A captain now writes
`.slipwai/running/captain-<fairway>.exit` on its way out, with the last line it said. `slipwai fleet` and the
board's JSON carry `processes`: the harbourmaster and one row per stream, each `running`, `exited` or
`not lit`, with the captain's own word on its exit and one sentence on what starts it again — a park cleared,
a pause ending at a time, a slice becoming startable. A restart that lights two captains for a second each
is now visible as exactly that.

**Catch-up:** `slipwai upgrade` carries the new `scripts/agents/captain.py` and `fleet.py`.

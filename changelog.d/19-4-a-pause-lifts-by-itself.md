MINOR

**A pause lifts by itself when its time comes.** The harbourmaster writes the `cleared` receipt for any
park whose `until` has passed, on the pass after the time, and lights the captain on the same pass. A person's
`/cruise-tell` still clears one early. `fleet relight` and `fleet list` say `paused until 21:40, so not lit`
for a stream waiting on the harness, instead of `parked`, which read as waiting on you.

**Catch-up:** `slipwai upgrade` carries the new `scripts/agents/harbourmaster.py` and `fleet.py`.

PATCH

**A stream's captain session no longer grows for the whole run, or carries over into the next one.** The
captain agent held one session per stream across every event and loaded it again at the next fleet start, so
each wake-up paid for every one before it: manda's intake captain reached 655k tokens a call after 634 calls,
while its brief says to believe the stream's state over anything it remembers. A captain program now always
starts its session fresh, and at an event boundary closes it for a fresh one once its context passes
`captain.context_ceiling` in `harbour.json` (150000 tokens), as the agent reports it over the protocol
(`usage_update`). Where the agent never reports its context, `captain.wake_ceiling` (100 wake-ups) stands in
for it. The captain's session also carries `SLIPWAI_STAGE=captain` in its environment, as it already did,
which a prompt hook can read to stay out of it.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/captain_agent.py` and `scripts/agents/drive.py`;
the next `fleet.py start` begins every captain fresh. Set `captain.context_ceiling` or `captain.wake_ceiling`
in `harbour.json` only to change the defaults.

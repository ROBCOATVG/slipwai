MINOR

**The board's token tile counts what the agents spent, and says what it is counting.** *Tokens today* summed
a `tokens` field on deck-log lines that nothing ever wrote. It read 0 all day while lean-coffee-club's three
slices worked, and the harbourmaster's day budget never moved for the same reason. Both now read each
stage's usage from its slice's `benchmark.json`, on trunk and in every berth, and count a stage once. A stage
counts on the day it ended.

The tile is now **Work tokens today**: uncached input plus output, which is the unit the day's budget is set
in. Work tokens are the pace the fleet is held to, not what the day cost. Sessions also re-read tens of
millions of cached tokens a day, and models are priced differently. So under the figure, the tile shows each
model's day: output, uncached input, read from cache and written to cache. Where `harbour.json` has
`prices` for every model that ran, it adds an estimate in money:

```json
"prices": {"<model>": {"input": 3, "output": 15, "cache_read": 0.3, "cache_creation": 3.75}}
```

Each price is per million tokens. None is shipped, because prices change and differ by account.

**Catch-up:** `slipwai migrate` carries `scripts/agents/spend.py` and the harbourmaster that reads it. To see
an estimate, add `prices` to `harbour.json`.

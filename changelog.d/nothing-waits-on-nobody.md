PATCH

**The fleet no longer says it is waiting on you when nobody has anything to do.** lean-coffee-club's board
said *12 things waiting on you* over nine notes, two merges waiting for trunk's CI and one question.

- A merge the harbourmaster refuses only because trunk is red is now a pause: the park carries
  `waiting: green-trunk` and the cause `trunk`, every reader lists it under *paused, nothing for you to do*,
  and the harbourmaster asks for the merge again when trunk turns, as it always did.
- A usage limit met while a slice is back in its berth resolving a refused merge is a pause with its time on
  it, as it already was at a slice's first run. It was read as a run that failed: the stream parked on
  "`/sail` exited 1" for a person and its captain left, while the streams beside it started again at the reset.
- A merge request is answered only by an answer written after it, where its id has been asked before. A
  slice's requests are numbered from nought at every run, so a slice refused one evening was told the same
  refusal the next morning, in the second it asked, while the harbourmaster gated and merged it: the stream
  parked for a person on a slice that was on trunk, and its worktree and containers were left.
- `slipwai fleet`, the fleet's headline and the agent inbox count only what holds something up. A note a slice
  left that needs nothing on trunk, and decisions under the ceiling, are listed under *left for you to read,
  holding nothing up*, which is what the board's page has always said of them.

**Catch-up:** `slipwai migrate` carries `scripts/agents/captain.py` and `logs.py`; start the fleet again.

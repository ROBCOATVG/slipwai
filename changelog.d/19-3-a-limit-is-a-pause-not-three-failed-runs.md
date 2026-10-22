MINOR

**A session limit pauses a slice instead of spending its attempts.** When the harness refuses to run a
session — a session limit, a rate limit, an overloaded answer — the captain no longer runs the slice twice
more in a second and parks it as "`/sail` exited 1". It writes one park with `cause: limit` and the time the
limit lifts, spends no attempt, and says `paused at LB3 until 21:40`. A captain lit while its stream is
paused says `is paused until 21:40` and runs nothing. Every other park the captain writes now carries its
cause too: `gate`, `demo`, `silence`, `exit`, `question`, `ceiling` or `trunk`.

**Catch-up:** `slipwai upgrade` carries the new `scripts/agents/captain.py`. The harbourmaster learns to
clear a pause when its time comes in the next slice; until then `/cruise-tell` clears one as it clears any park.

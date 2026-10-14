---
description: Continue the build from a drafted specification — chart it, split it, enable /cruise and cast off
argument-hint: [--boilers <n>]
---

# Launch

`/draft` stops at a specification so that a person can read it. This is the step after reading: from that
specification to a running fleet, and nobody is asked again until a captain parks. It is what the board's
**Continue the build** button runs, and the one place a person's word that the specification is good enough
to build from is given.

**Typed by a person**, run `python3 scripts/agents/launch.py` — `{{make}} launch`, with `CRUISE_FLAGS="--boilers
<n>"` where you want to bound the fleet — and repeat what it printed. The script refuses where there is no
`specs/<feature>/spec.md`. Where the chart and the split are already written it only enables `/cruise` and
casts off; otherwise it dispatches one headless session with this page as its rules, and casts off when that
session has ended well.

**In a session that script dispatched** (`SLIPWAI_STAGE=launch` in the environment), this file is the rules.
Run `commands/sail.md` from *Enter at the first incomplete stage* through the split's first ready set — the
upstream stages, as the stage contract in `commands/cruise.md` names them — and no further: no slice is
claimed here, because that is the captains' work. Wherever the ladder would stop for a person, answer as
`commands/cruise.md` answers it — the stop table, and the skipper protocol with every decision written to the
feature's decision log under its own number. Where a stage says a person is present (the chart), bring the
proposal it asks for, with the evidence it asks for, and take it as confirmed, recorded as a decision. Write
each artefact as the stage produces it. Commit on the current branch when the split is written, say what was
charted and split, and end. A park is a line and an end, not an exit code: the script reads the tree and says
so.

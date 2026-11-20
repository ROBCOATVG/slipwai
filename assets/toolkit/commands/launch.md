---
description: Continue the build from a drafted specification — chart it, split it, enable /cruise and cast off
argument-hint: [<feature>] [--boilers <n>]
---

# Launch

`/draft` stops at a specification so that a person can read it. This is the step after reading: from that
specification to a running fleet, and nobody is asked again until a captain parks. It is what the board's
**Continue the build** button runs, and the one place a person's word that the specification is good enough
to build from is given.

**Typed by a person**, run `python3 scripts/agents/launch.py` — `{{make}} launch`, with `CRUISE_FLAGS="--boilers
<n>"` where you want to bound the fleet — and repeat what it printed. The script refuses where there is no
`specs/<feature>/spec.md`. Where the chart and the split already hold the feature in hand — the one
`.specify/feature.json` names — it only enables `/cruise` and casts off; otherwise it dispatches one headless session with this page as its rules, and casts off when that
session has ended well.

**It is about one feature, and an earlier feature's chart is not that feature's.** The argument names it —
the directory under `specs/` — and where there is none it is the one `.specify/feature.json` names. A project
that has built a feature already has a model, a chart and a split, and none of them holds a further feature
until its own slices are in them: on the event profile the model is global and there is one chart, so each
slice of a further feature carries `feature: <its directory under specs/>` in `docs/event-model/model.yaml`,
`{{make}} chart` carries that into the chart, and the split orders those slices and leaves every slice that is
there as it is. A launch that finds the chart holding nothing of the feature in hand has the chart and the
split to do, however many slices the chart names.

**In a session that script dispatched** (`SLIPWAI_STAGE=launch` in the environment), this file is the rules.
Run `commands/sail.md` from *Enter at the first incomplete stage* through the split's first ready set — the
upstream stages, as the stage contract in `commands/cruise.md` names them — and no further: no slice is
claimed here, because that is the captains' work. Wherever the ladder would stop for a person, answer as
`commands/cruise.md` answers it — the stop table, and the skipper protocol with every decision written to the
feature's decision log under its own number. Where a stage says a person is present (the chart), bring the
proposal it asks for, with the evidence it asks for, and proceed on it — never as an answer somebody gave.
The chart's context answer is the one that shapes the whole fleet, so it follows `commands/chart.md`,
*Record the context answer, every time*, to the letter: the seam table in a decision entry even for one
context, `Decided by: host (stage recommendation)` with `Status: awaiting human confirmation`, and the
question posted to the first fairway's deck log for the board. On the event profile the model is that
answer: if this session models, it runs `skills/event-modeling/references/nine-steps.md` Step 9 the same
way. `make check-chart` refuses a split without it. Write
each artefact as the stage produces it. Commit on the current branch when the split is written, say what was
charted and split, and end. Do not push: casting off does, because every slice's worktree is cut from the
remote trunk and a plan that is only in this checkout is a plan no slice can see (`scripts/agents/published.py`). A park is a line and an end, not an exit code: the script reads the tree and says
so.

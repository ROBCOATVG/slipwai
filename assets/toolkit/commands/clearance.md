---
description: Say which slices may start now and what each one that may not is waiting on — read off the chart and the logs, changing nothing
argument-hint: [slice]
---

# Clearance

Clearance is the question `/sail` asks before it takes a slice: has every mark this slice steers by been set?
This asks it from the session, so a person can see the answer without starting anything.

Run `python3 scripts/agents/clearance.py`. Where `$ARGUMENTS` names a slice, run
`python3 scripts/agents/clearance.py $ARGUMENTS` instead, which says whether that one may start and what it
waits on.

Put every line it printed in your reply, unchanged, in a fenced block, before anything else: the harness folds
a command's output, so what it said reaches a person only through your reply. Then say, in a line each:

1. **How many may start now**, from its first line, and in which band — *prepare* or *implement*.
2. **What each blocked slice waits on**: the mark, and the slice that sets it. Quote the line. A paraphrase of
   why a slice is blocked is a second thing to be wrong.

**Read, don't start.** Nothing here claims a slice, makes a berth or sets a mark. Where a slice may start,
`/sail` is what takes it. Where the script says there is no chart yet, say so: the chart comes before
clearance can say anything.

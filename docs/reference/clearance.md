# Clearance

**A slice has clearance when every mark it steers by has been set.** That is the rule that lets a slice
start, and it replaces version 1's "its own contract is settled" — a question a slice could only answer
about itself, which serialised a fresh fairway because nothing said what a slice was waiting *for*.

```
python3 scripts/agents/clearance.py            # every slice that may start now
python3 scripts/agents/clearance.py BIL-01     # whether that one may, and what it waits on
```

With no chart yet, it says so and exits 0: a project with no feature in flight has nothing waiting on
anything.

---

## A mark is set by being written down, not by being merged

A mark is set when some slice wrote a `mark-set` line for it, at its own first stage, in its own worktree.
So **a sibling unblocks this slice by having planned, not by having merged.** That is the whole of the
parallelism version 2 promises. If a merge were the signal, every fairway would wait on every other one.

The line is in the setting slice's own [deck log](the-logs.md), and the harbourmaster carries it into the
harbour log so other fairways see it without reading every deck log there is.

---

## State comes from the log, never from a status field

`clearance.py` folds `mark-set` lines out of every fairway's deck log and out of every machine's harbour
log — every machine's, because a mark another machine's harbourmaster carried is what clears a slice here,
and reading one of them would make clearance depend on which machine happened to carry it.

It never reads a `status` field. In the first attempt `model.yaml` said `planned` for eight slices that
were built and merged, because the field was written at plan time and never reconciled. A log line is
written by the thing that did the work at the moment it did it.

Two reading rules follow from that, and they pull in opposite directions on purpose:

- **A line of a kind this reader does not know is ignored.** The logs hold a dozen kinds and will grow, and
  a reader that refused the unfamiliar would break every time one was added.
- **A line in a newer format stops the read**, naming `slipwai upgrade`. Guessing which fields moved is how
  a reader reports a run that did not happen. A line that is not JSON stops it too.

---

## What a refusal says

Every missing mark, not the first — a fairway told one blocker at a time is a fairway blocked once per
blocker — and each with the slice that owes it:

```
clearance: BIL-01 steers by booking.confirmed (set by BOK-02), and none of those is set yet
```

A mark no slice sets is named as such, because the chart is then wrong rather than the fairway blocked. A
slice the chart does not name is refused rather than cleared: answering yes for an uncharted slice would
clear anything anybody asked about.

---

## `observed` slices

A slice the chart marks `observed` says *this is what the code already does*. Nobody builds it, so it is
never offered as ready — a ready set that included one would send a captain to build what is already
built — and the marks it sets count as settled from the moment the chart is drawn, because the behaviour
they describe shipped before the model existed.

---

## Where it lives, and why it is not in the keel

`clearance.py` ships in the toolkit, inside a generated project, alongside `check-chart.py` and
`check-slice-scope.py`. The things that ask it — a `/sail` session and the captain — run inside that
project, which has no slipwai to import. The first version of this was a keel module and was unreachable
from everything that needed it.

A board asks it with `--json`, which reads and reports and never installs a dependency or reaches the
network.

---

Next: [the chart and the mark](the-chart-and-the-mark.md), which is what clearance reads ·
[the deck log and the harbour log](the-logs.md) ·
[a second person joins](../guide/a-second-person.md)

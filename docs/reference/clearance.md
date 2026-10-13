# Clearance

**A slice has clearance when every mark it steers by has been set.** That is the rule that lets a slice
start, and it replaces version 1's "its own contract is settled" — a question a slice could only answer
about itself, which serialised a fresh fairway because nothing said what a slice was waiting *for*.

```
python3 scripts/agents/clearance.py                    # every slice, its state and why, and the schedule
python3 scripts/agents/clearance.py BIL-01             # one slice: its state and what it waits on
python3 scripts/agents/clearance.py --json             # the same, for a board; reaches no network
python3 scripts/agents/clearance.py --baseline-marks   # once, after a crossing: record shipped marks
```

With no chart yet, it says so and exits 0: a project with no feature in flight has nothing waiting on
anything.

---

## Clearance is a state, not a yes

One word hid a distinction. *Ready* said nothing about whether a slice could be prepared, could be
implemented, or was waiting on a person — and the page said *run every ready slice whose contract is
settled*, which a slice can only do by preparing. A host reading that waited on the one thing the wait was
stopping. So every slice is answered with one of eight states and the sentence that says why:

| State | Means | The sentence says |
|---|---|---|
| `blocked` | a mark it steers by is not set | every missing mark and the slice that owes it; whether that slice is itself awaiting a decision |
| `migration-evidence-required` | the setter shipped before marks were logged, or a crossing's hold still stands | which setter, and the command that records the evidence |
| `awaiting-decision` | a `question` line stands open against it, or its fairway is parked | the question, and which siblings its answer would unblock |
| `preparation-ready` | cleared; its own marks not yet set | which marks its preparation will set |
| `implementation-ready` | cleared; its own marks set, or it sets nothing; no open question | whether a mark was recorded by baseline rather than earned |
| `running` | claimed and not merged | since when, and in which band — preparing or implementing |
| `awaiting-demo` | its capability has a `demo-due` with no later `accepted` | which capability |
| `done` | a `merged` line | the commit |

**Two bands.** *Preparation* — the example map, the contract files the slice's marks name, the gaps pass —
needs clearance and nothing else, because it is the stage that writes the slice's own `mark-set` lines.
*Implementation* — the plan onward — needs those lines written and no open question. A delegate is handed
one band (`prepare`, `implement` or `whole`), and the slice's state says which.

**The schedule says why, for every slice that does not start.** `clearance.py` with no argument prints
which slices start now and in which band, which are *queued* and for what reason — no slot (`boilers` in
`harbour.json`, less what is running), claimed on the forge by another session (`--claims a,b`), or
*claims could not be read* (`--claims-unreadable`), which starts nothing: every slice reading as unclaimed
is exactly the answer that lets two sessions take one — and which are running, waiting and done. A host
with a slot free and eligible work queued has its reason written down before it has to give one.

**A question is a line.** A delegate that meets a product question writes `question` (`fairway`, `slice`,
`id`, `what`) to the deck log and returns; the slice is *awaiting-decision* until a `decision` carries the
same `id`. The wait is that slice's and reaches only the siblings steering by a mark it has not set — the
sentence names them — so nothing else stops.

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

## Migrated prerequisites

A slice that shipped before this project logged marks has no `mark-set` line and no line at all. A sibling
steering by what it sets is told *migration-evidence-required*, not *blocked*, and nothing is cleared on the
done marker's word: the marker is read once, to name the wait, and that is the only time clearance reads
it. `--baseline-marks` records the evidence — a `mark-set` line in this machine's harbour log for every
such mark, carrying `provenance: baseline`, which machine wrote it and what it was read from — so a reader
can always tell a baselined mark from one a stage earned, and the sentence that clears on it says so. A
second baseline is refused; a slice finished since writes its own line at its own first stage. This is the
same shape as `check-decisions.py --adversary-baseline`, for the same reason.

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

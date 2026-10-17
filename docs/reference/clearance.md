# Clearance

**A slice has clearance when every mark that it steers by is set.** This rule lets a slice start. It
replaces the version 1 rule, "its own contract is settled". Under the version 1 rule, a slice could only
answer the question about itself. Nothing said what a slice was waiting *for*, so a new fairway ran its
slices one at a time.

```
python3 scripts/agents/clearance.py                    # every slice, its state and why, and the schedule
python3 scripts/agents/clearance.py BIL-01             # one slice: its state and what it waits on
python3 scripts/agents/clearance.py --json             # the same, for a board; reaches no network
python3 scripts/agents/clearance.py --baseline-marks   # once, after a crossing: record shipped marks
```

If there is no chart yet, `clearance.py` says so and exits 0. A project with no feature in progress has
nothing that waits on anything.

---

## Clearance is a state, not a yes

Version 1 used one word, *ready*, for several different things. *Ready* did not say whether a slice could
be prepared, could be implemented, or was waiting on a person. The version 1 page said *run every ready slice
whose contract is settled*. A slice can only settle its contract by preparing. So a host that followed the
page waited for the one thing that the wait itself stopped.

For this reason, clearance gives every slice one of eight states, and a sentence that says why:

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

**A slice has two bands.** A band is a part of the stages of a slice.

- *Preparation* is the example map, the contract files that the slice's marks name, and the gaps pass.
  Preparation needs clearance and nothing else, because preparation is the stage that writes the slice's own
  `mark-set` lines.
- *Implementation* is the plan and every stage after it. Implementation needs those `mark-set` lines, and no
  open question.

A delegate gets one band: `prepare`, `implement` or `whole`. The state of the slice says which band.

**The schedule gives a reason for every slice that does not start.** Run `clearance.py` with no argument.
It prints:

- which slices start now, and in which band;
- which slices are *queued*, and the reason for each;
- which slices are running, waiting and done.

A slice is queued for one of three reasons:

- There is no free slot. The number of slots is `boilers` in `harbour.json`, minus the slices that are
  running.
- Another session claimed the slice on the forge (`--claims a,b`).
- *Claims could not be read* (`--claims-unreadable`). In this case nothing starts. If every slice read as
  unclaimed, two sessions could take the same slice.

So when a host has a free slot and eligible work in the queue, the reason is already written down before
anybody asks.

**A question is a line in the log.** When a delegate meets a product question, the delegate writes a
`question` line (`fairway`, `slice`, `id`, `what`) to the deck log and returns. The slice is
*awaiting-decision* until a `decision` line has the same `id`. Only that slice waits. The wait also reaches
the siblings that steer by a mark that the waiting slice has not set, and the sentence names those siblings.
Nothing else stops.

---

## A mark is set by being written down, not by being merged

A mark is set when a slice writes a `mark-set` line for it. The slice writes this line at its own first
stage, in its own worktree. So **a sibling unblocks this slice when the sibling has planned, not when it has
merged.** This is all of the parallel work that version 2 promises. If a merge were the signal, every
fairway would wait on every other fairway.

The `mark-set` line is in the setting slice's own [deck log](the-logs.md). The harbourmaster copies the line
into the harbour log. Other fairways then see the mark without reading every deck log.

---

## State comes from the log, never from a status field

`clearance.py` folds the `mark-set` lines from every fairway's deck log and from every machine's harbour
log. It reads every machine's harbour log because a mark that another machine's harbourmaster carried can
clear a slice on this machine. If `clearance.py` read only one harbour log, clearance would depend on which
machine carried the mark.

`clearance.py` never reads a `status` field. In the first attempt, `model.yaml` said `planned` for eight
slices that were already built and merged. The field was written at plan time, and nothing updated it
later. A log line is different: the thing that did the work writes it, at the moment it did the work.

Two reading rules follow from this. They pull in opposite directions on purpose:

- **The reader ignores a line of a kind that it does not know.** The logs hold about a dozen kinds, and
  more will come. A reader that refused unknown kinds would break each time somebody added one.
- **A line in a newer format stops the read**, and the message names `slipwai upgrade`. A reader that
  guesses which fields moved can report a run that did not happen. A line that is not JSON also stops the
  read.

---

## What a refusal says

A refusal names every missing mark, not only the first one. If a fairway hears about one blocker at a
time, it is blocked once for each blocker. The refusal also names the slice that owes each mark:

```
clearance: BIL-01 steers by booking.confirmed (set by BOK-02), and none of those is set yet
```

If no slice sets a mark, the refusal says so. In that case the chart is wrong; the fairway is not blocked.

If the chart does not name a slice, `clearance.py` refuses that slice. It does not clear it. A yes for a
slice that is not on the chart would clear any slice that anybody asked about.

---

## Migrated prerequisites

A slice that shipped before this project logged marks has no `mark-set` line. It has no line of any kind.

A sibling that steers by a mark from such a slice is told *migration-evidence-required*, not *blocked*.
Nothing is cleared because the done marker says so. Clearance reads the done marker once, to name the wait,
and at no other time.

`--baseline-marks` records the evidence. For every such mark, it writes a `mark-set` line in this machine's
harbour log. The line carries `provenance: baseline`, which machine wrote it, and what it was read from. So
a reader can always tell a baselined mark from a mark that a stage earned, and the sentence that clears on a
baselined mark says so.

A second baseline is refused. A slice that finished after the baseline writes its own line, at its own first
stage. This is the same design as `check-decisions.py --adversary-baseline`, for the same reason.

---

## `observed` slices

When the chart marks a slice `observed`, the slice means *this is what the code already does*. Nobody builds
it, so clearance never offers it as ready. A ready set that included it would send a captain to build
something that is already built. The marks that an `observed` slice sets count as set from the moment the
chart is drawn, because the behaviour they describe shipped before the model existed.

---

## Where it lives, and why it is not in the keel

`clearance.py` ships in the toolkit, inside a generated project, beside `check-chart.py` and
`check-slice-scope.py`. The things that ask it are a `/sail` session and the captain. Both run inside the
project, and the project has no slipwai to import. The first version of clearance was a keel module, and
nothing that needed it could reach it.

A board asks `clearance.py` with `--json`. With `--json`, it reads and reports only. It never installs a
dependency and never reaches the network. If PyYAML is missing, it reports an error with the install command
instead of installing PyYAML.

---

Next: [the chart and the mark](the-chart-and-the-mark.md), which is what clearance reads ·
[the deck log and the harbour log](the-logs.md) ·
[a second person joins](../guide/a-second-person.md)

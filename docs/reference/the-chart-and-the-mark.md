# The chart and the mark

The chart is the contracts, written before the split, as one committed file per feature:
`specs/<feature>/chart.yaml`. It names the fairways, the marks each slice sets, the marks each slice steers
by, the paths each fairway owns, and the capability each slice is part of. It is the one file a captain and
a gate both read, on either profile, so a change to it shows in a diff.

A **mark** is one published contract that another slice steers by. Marks are what fairways share; they
share nothing else.

```
make check-chart
```

---

## The four kinds, and what each has to carry

A mark is typed, and the type says which file holds it. `scripts/check-chart.py` refuses any other kind, and
refuses a mark whose file is not in the tree — a mark naming a file nobody wrote is a promise discovered at
the far end, by the fairway that believed it.

| Kind | What it is | What the chart entry carries |
|---|---|---|
| `event` | A business fact the model names | `schema`, a JSON Schema file |
| `schema` | A typed payload that is not an event | `schema`, a JSON Schema file |
| `route` | One OpenAPI operation | `operation` |
| `port` | A name with typed inputs and outputs | `inputs` and `outputs` |

A path may carry a `#` fragment; the gate checks the file before it.

---

## A mark is set once and never moved

One mark has one setter. Two setters is two schemas for one name, resolved by whichever merged last, and
that is the one failure nobody can find by reading either slice on its own. `check-chart` refuses it by
name.

The chart is **frozen** before any slice is claimed, and frozen means a real thing: the gate reads the chart
as `origin/main` holds it — falling back to `main`, and saying nothing where git cannot answer — and refuses
any mark that was there and is not here now. A mark that disappears is a contract withdrawn from under
whoever steered by it.

So the files that hold marks only grow. When a slice needs the chart changed, it writes a fragment under
`fairways/<name>/chart.d/` and the harbourmaster folds the fragments on `main`. That is the pattern
`changelog.d/` already uses, and the refusal names it.

---

## The other three rules the gate holds

- **Every mark steered by is set by some slice.** Otherwise a slice waits on a mark nobody is building,
  [clearance](clearance.md) never comes, and the fairway looks blocked with nothing saying on what.
- **Every slice names the capability it is part of.** A capability is what a person's demo is for. A slice
  naming none would never complete one, so no demo would ever come due.
- **Once the split has run, every slice says `sets` and `steers_by` out loud.** An empty list is an answer;
  an absent key is refused. A slice that forgot the key used to take a demo-only gate by omission, which is
  the quietest way there is to pass a gate.

A malformed chart is reported as a shape fault and the five rules are not run over it, because every one of
them would otherwise report the same damage again in its own words. A project with no feature in flight has
nothing to hold, and the gate says so and exits 0.

---

## Where the chart comes from

On the **event-modelling profile** the model is the source and the chart is rendered from it:

```
make chart
```

`check-chart` then holds a sixth rule on that profile — the committed chart must be what `make chart` would
render from `docs/event-model/model.yaml`. The two are compared as data rather than as text, so a different
YAML writer or a reordered model is not drift; a fairway, a mark or a slice that says something different
is.

On the **standard profile** a `/chart` stage writes the file, and the same five rules hold it.

---

Next: [clearance](clearance.md), which is what the marks are for ·
[fairways, captains and the harbourmaster](fairways-and-captains.md) ·
[your first feature](../guide/first-feature.md), where a chart is rendered for the first time

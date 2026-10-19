# The chart and the mark

The chart is the contracts, written before the split. There is one committed chart file for each feature:
`specs/<feature>/chart.yaml`. The chart names:

- the fairways;
- the marks that each slice sets;
- the marks that each slice steers by;
- the paths that each fairway owns;
- the capability that each slice is part of.

The chart is the one file that both a captain and a gate read, on either profile. So every change to the
chart shows in a diff.

A **mark** is one published contract that another slice steers by. Fairways share marks. They share nothing
else.

```
make check-chart
```

---

## The four kinds, and what each has to carry

Every mark has a kind, and the kind says which file holds the mark. `scripts/check-chart.py` refuses any
other kind. It also refuses a mark whose file is not in the tree. If a mark names a file that nobody wrote,
the fairway that trusted the mark finds the broken promise only at the end.

| Kind | What it is | What the chart entry carries |
|---|---|---|
| `event` | A business fact the model names | `schema`, a JSON Schema file |
| `schema` | A typed payload that is not an event | `schema`, a JSON Schema file |
| `route` | One OpenAPI operation | `operation` |
| `port` | A name with typed inputs and outputs | `inputs` and `outputs` |

A path can have a `#` fragment. The gate checks the file before the `#`.

---

## A mark is set once and never moved

One mark has one setter. Two setters would give two schemas for one name, and the schema that merged last
would win. Nobody can find that failure by reading either slice alone. `check-chart` refuses two setters and
names them.

The chart is **frozen** before any slice is claimed. Frozen has an exact meaning here:

- The gate reads the chart as `origin/main` holds it. If there is no `origin/main`, the gate reads `main`.
  If git cannot answer, the gate says nothing.
- The gate refuses any mark that was in that chart and is not in the chart now. A mark that disappears is a
  contract taken away from every slice that steered by it.

So the files that hold marks only grow. When a slice needs a change to the chart, the slice writes a
fragment under `fairways/<name>/chart.d/`. The harbourmaster folds the fragments into the chart on `main`.
`changelog.d/` already uses this pattern, and the refusal names it.

---

## The other rules the gate holds

- **Some slice sets every mark that a slice steers by.** If no slice sets the mark, a slice waits on a mark
  that nobody is building. [Clearance](clearance.md) never comes, and the fairway looks blocked, with
  nothing to say what blocks it.
- **Every slice names the capability that it is part of.** A capability is what a person's demo is for. A
  slice that names no capability never completes one, so no demo would ever come due.
- **After the split has run, every slice states `sets` and `steers_by`.** An empty list is an answer. A
  missing key is refused. Before this rule, a slice that forgot the key got a demo-only gate without anybody
  choosing it. That is the quietest way to pass a gate.
- **The fairways come from a recorded context decision.** `specs/<feature>/decisions.md` must hold an
  entry asking which bounded contexts the feature touches, with the seam table that the answer was read
  from. This holds for one fairway too. One fairway means one captain takes every slice in turn, so that
  answer needs its reason most. A fairway with more than twelve slices also needs a `Why not split:` line
  that cites the invariant keeping them together. The count asks for the reason. It does not ask for a
  split.

If the chart is malformed, the gate reports a shape fault and does not run the rules on it. If it ran
them, each rule would report the same damage again in its own words. If a project has no feature in
progress, the gate has nothing to hold. It says so and exits 0.

---

## Where the chart comes from

On the **event-modelling profile**, the model is the source, and the chart is rendered from the model:

```
make chart
```

On that profile, `check-chart` also holds a sixth rule: the committed chart must be the chart that
`make chart` would render from `docs/event-model/model.yaml`. The gate compares the two as data, not as
text. So a different YAML writer or a reordered model is not drift. A fairway, a mark or a slice that says
something different is drift.

On the **standard profile**, a `/chart` stage writes the file, and the same rules hold it.

---

Next: [clearance](clearance.md), which is what the marks are for ·
[fairways, captains and the harbourmaster](fairways-and-captains.md) ·
[your first feature](../guide/first-feature.md), where a chart is rendered for the first time

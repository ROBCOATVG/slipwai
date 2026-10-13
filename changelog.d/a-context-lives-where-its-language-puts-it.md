PATCH

**A fairway in a multi-context service now owns its context's code in every language, and the gate that
refuses a slice for crossing that boundary works again.** `make chart` wrote each fairway's `owns` as
`<service>/src/<context>/**` — where a TypeScript service keeps a context, and nowhere a Go, Java, Python
or Rust one does. On every other language that pattern matched no file.

**It failed by passing, which is why it lasted.** `check-slice-scope` refuses a path another fairway owns,
and a path no fairway claims is nobody's to refuse — so with nothing owned, nothing was refused. A slice
branch could edit another fairway's code and the gate reported the branch in scope, which is the same thing
it says when the branch really is in scope, and nothing told the two apart. `check-chart` stayed green
throughout, because the chart was internally consistent; it just described directories that did not exist.

**The chart now says what `check-imports` has always said.** That gate finds a context by looking for its
name among a path's directory parts, at whatever depth the language keeps it; two files deciding where a
context lives, by different rules, was the defect and the `src/` was the symptom. A chart writes
`<service>/**/<context>/**`, and the matcher reads `**` as zero or more whole segments — so one pattern
covers `apps/x/billing/`, `apps/x/src/billing/` and `apps/x/internal/billing/`, and still refuses to see
`billings/` as `billing/`.

**Catch-up:** run `make chart` and commit the result. Every project migrated before this carries a chart
whose `owns` paths name directories that are not there, and `make check-chart` holds the committed chart to
what the renderer would write — so it will refuse the stale one until it is re-rendered. Read the new paths
before committing them: the fairway rule starts refusing things the moment they are right, and a slice
branch that was quietly out of scope will say so.

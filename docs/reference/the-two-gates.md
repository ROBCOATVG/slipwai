# The two gates

**There are two gates, not one.**

- The fast checks run inside a slice, at every increment.
- The full gate runs once, on the rebased branch, before `main`.

In version 1, one `make verify` did everything. So every increment paid for lint, typecheck, structure and
the whole suite. In the experiment, the owner's own note said *"use full verify sparingly, it's heavy"*. That
describes a gate that nobody runs. A gate that is not run is not a gate.

```
make unit        # the inner loop, with make lint and make typecheck
make verify      # once, on the rebased branch, before main
```

---

## In a generated project

| When | What to run | Why |
|---|---|---|
| Every increment inside a slice | `make unit`, `make lint`, `make typecheck` | Seconds. Run them often enough that a break is one edit old |
| Once, before the merge to `main` | `make verify`, on the rebased branch | Lint, typecheck, every `check-*` gate, and the whole suite |
| In CI, and nowhere else by default | `make ci` | `verify`, plus the dependency audit, the database and the integration suite |

`make unit` is only the test suite. **The language package decides which of a project's targets are fast.
The keel does not assume it.** `fast_targets` is a protocol member. Its default is `("test",)`: the test
suite and nothing else. By that default, integration, mutation, the image build and the audit belong to the
gate before the merge, whatever the language is.

In a generated project, `make verify` is the project's own gate. It runs, in this order:

1. the language's lint and typecheck;
2. every `check-` script that the profile ships: imports, migrations, [chart](the-chart-and-the-mark.md),
   rendered files, surfaces, slice scope, extensions, agents, Spec Kit, constitution, benchmark and
   decisions;
3. the test suite and the model gates.

When a project adds a check, every merge runs the check with no extra work, because
[the merge runs this same target](fairways-and-captains.md#the-merge-serialised-through-refsslipwaimerge).

`make ci` is deliberately **not** the merge gate. It needs Docker or the network. If it were the merge gate,
a laptop without them could never merge.

---

## In this repository

The keel uses the same split for itself. `AGENTS.md` holds the table that a session reads. The difference is
that the keel's full gate has platform legs, which a laptop cannot run.

| When | What to run | Why |
|---|---|---|
| Every increment inside a slice | `make unit`, `make lint`, `make typecheck` | Seconds |
| Once, before the merge to `main` | `make verify`, on the rebased branch | Lint, typecheck, structure, the shared-module and release checks, and the whole suite |
| Every push to `main` and every pull request | The gate again, in CI, on Linux, macOS and Windows | The platform legs |

In CI, Linux and macOS run `make verify`. Windows runs the same checks without `make`: lint, compile,
typecheck, structure and the whole suite.

**`make unit` stays useful because the slow modules are named.** The `Makefile` holds a `SLOW` list. `unit`
runs every test module that is not on the list. Add a test that generates a project, shells out, or reaches
the network to that list **in the same commit that adds the test**. All of the value of `make unit` is that
it stays quick. If an increment has to wait for the full suite, people stop running it.

The list is measured, not guessed. Two modules were once missing from the list: one that starts an HTTP
server and shells out, and one that shells out for each check. Together they took nine of the twelve seconds
that `make unit` took.

---

## The rule that makes the split safe

**Nothing merges red, and nothing merges with carried gaps.** An environment problem gets no standing
exemption. Fix the environment, or exclude the test once, in writing. The inner loop costs less than the
merge gate. It is not weaker about what it finds.

---

Next: [fairways, captains and the harbourmaster](fairways-and-captains.md), where the merge gate is run ·
[release modes](release-modes.md) · [start here](../guide/start-here.md)

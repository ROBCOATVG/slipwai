# The two gates

**Two gates, not one.** The fast checks run inside a slice, every increment. The full gate runs once, on the
rebased branch, before `main`.

In version 1 one `make verify` did everything, so every increment paid for lint, typecheck, structure and
the whole suite. The owner's own note in the experiment was *"use full verify sparingly, it's heavy"*, which
is a gate nobody runs. A gate that is not run is not a gate.

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

`make unit` is the test suite alone, and which of a project's targets count as fast is **the language
package's to say, not the keel's to assume**. `fast_targets` is a protocol member whose default is `("test",)`
— the test suite and nothing else. Integration, mutation, the image build and the audit belong to the gate
before the merge, by that default, whatever the language.

`make verify` in a generated project is the project's own gate: the language's lint and typecheck, then
every `check-` script the profile ships — imports, migrations, [chart](the-chart-and-the-mark.md), rendered
files, surfaces, slice scope, extensions, agents, Spec Kit, constitution, benchmark, decisions — then the
test suite and the model gates. A project that adds a check gets it at every merge for free, because
[the merge runs this same target](fairways-and-captains.md#the-merge-serialised-through-refsslipwaimerge).

`make ci` is deliberately **not** the merge gate: it wants Docker or the network, and a laptop without
either could then never merge.

---

## In this repository

The keel holds itself to the same split. `AGENTS.md` carries the table a session reads; the difference is
that the keel's full gate has platform legs a laptop cannot give you.

| When | What to run | Why |
|---|---|---|
| Every increment inside a slice | `make unit`, `make lint`, `make typecheck` | Seconds |
| Once, before the merge to `main` | `make verify`, on the rebased branch | Lint, typecheck, structure, the shared-module and release checks, and the whole suite |
| Every push and pull request | `make verify` again, in CI, on Linux, macOS and Windows | The platform legs |

**`make unit` stays worth running because the slow modules are named.** The `Makefile` holds a `SLOW` list,
and `unit` is every test module that is not on it. A test that generates a project, shells out, or reaches
the network goes on that list **in the same commit that adds it** — the entire value of the target is that
it stays quick, and an increment that waits on the full suite stops being run.

The list is measured rather than guessed. One module that stands up an HTTP server and shells out, and one
that shells out per check, were between them nine of the target's twelve seconds while never having been
listed.

---

## The rule that makes the split safe

**Nothing merges red, and nothing merges with carried gaps.** There is no standing exemption for an
environment problem: fix the environment, or exclude the test once, in writing. The inner loop is cheaper
than the merge gate; it is not weaker about what it finds.

---

Next: [fairways, captains and the harbourmaster](fairways-and-captains.md), where the merge gate is run ·
[release modes](release-modes.md) · [start here](../guide/start-here.md)

MINOR

**A migration no longer lands on gates nothing true can satisfy: `check-benchmark` warns rather than fails, the one
event model charges a slice to its own feature, and a project's slice history can be baselined for the adversary
log once.** A project migrating from a 1.2.0 snapshot met two gates that arrived in 1.2.0 without a word in its
catch-up note. `check-benchmark` failed on every slice finished before benchmark records existed, and those records
can only be taken at the time, so the only ways to pass were to invent them or never push again. It now prints
each of those findings as a `warning:` and passes, and its own self-test is still what fails it. Both it and
`check-decisions` counted every `status: implemented` slice in `docs/event-model/model.yaml`, which is the whole
project's, against every feature they checked: a second feature failed for the first feature's slices, and
nothing done inside the second could fix that. A slice now counts only for the feature its `spec` or `gwt` path
is under, or, where it names none, the feature holding `slices/<id>/`. An implemented slice that no feature holds
is reported once. `python3 scripts/check-decisions.py --adversary-baseline` writes, once, a `## <id> · predates
the adversary gate · <date>` row for every done slice with no row. The gate accepts that row. The row says the
slice was never attacked, and `/adversary` never relies on it. A second baseline is refused.

Four smaller fixes, found on the same migration. `make verify` now runs `check-python` first, and it names the
interpreter when `python3` is older than the 3.10 the gate scripts need. Before this, a non-interactive macOS
shell that found `/usr/bin/python3` (3.9) first died inside whichever gate first used a newer feature.
`check-codegraph` and `code_index.py health` now tell a database they cannot open apart from a damaged one. On
macOS's system SQLite, CodeGraph's WAL database with no `-shm` beside it refuses a read-only open. It is now
read with `immutable=1`, and an open failure is reported as one and never moves the database aside, so `health`
no longer rebuilds a sound index in a loop. The code index finds a Node that nvm, volta or fnm installed when a
hook's shell has none on `PATH`, and says that is the likely cause when it finds none. `check-ux-gates.py` can
now be loaded with `importlib` without being registered in `sys.modules`, and it says to unset an
`UX_GATES_SHARD` value it refuses.

**Catch-up.** These gates are new or stricter since 1.1: `check-benchmark` (warns since this release),
`check-decisions`' adversary rows (1.2.0), `check-deploy-role` on `aws` (1.3.0), `check-ux-gates` sharding and
its CI job (1.3.0), and `check-python` (1.3.0). If `check-decisions` reports `no row for` slices finished
before you migrated, run `python3 scripts/check-decisions.py --adversary-baseline` once and commit the rows it
writes. Slices finished after that need the row `/adversary` writes. Make sure the `python3` your shell finds
first is 3.10 or newer. Nothing else needs doing: the rest arrives whole with the merge.

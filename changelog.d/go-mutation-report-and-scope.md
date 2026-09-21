MINOR

**`make mutation` on a Go service keeps its report, and `make mutation SINCE=<branch-or-commit>` prices the
stage per change rather than per repository.** The report was Gremlins' own `gremlins.json`, written inside
the staging tree `scripts/go-mutation.py` builds and deletes, so the target left a scrollback where a slice
record expects its evidence; it is now copied to `<service>/gremlins.json` before the cleanup, whether the
run passed or failed, and git-ignored beside `coverage.out`. `SINCE` scopes the run to the production files
that differ from that ref: a project measured 324 mutants in 31 minutes where seven belonged to the change
being driven, and a stage that expensive gets routed around rather than read. The unscoped target is
unchanged and is the full sweep.

The scope is computed from git before anything is staged, not handed to Gremlins' `--diff`, which is
unusable from a module in a subdirectory: it resolves changed paths against the repository root, matches
them against paths within the module, and reports every mutant SKIPPED and the run successful — verified
against 0.6.0, from the module directory and the repository root alike. Gremlins has no include list either,
so the scope is a complement of `--exclude-files` patterns generated per run, and because that flag replaces
the yaml's list rather than adding to it, the wrapper reads `.gremlins.yaml`'s own exclusions and passes
them back. A change confined to files the project already excludes scopes to nothing and says so, rather
than failing as a run that mutated nothing. An `exclude-files` written inline is a loud failure: a scope
silently read as empty is the one outcome that would mutate what the project excluded on purpose.

**Catch-up.** A Go service's mutation stage takes all of this through the merge — `scripts/go-mutation.py`,
the `mutation:` recipe, the `.gitignore` line, the note above the target and the yaml's comments — so there
is nothing to install and no answer to give. Two things to look at while resolving that merge. A project
that edited `apps/<service>/.gremlins.yaml` or the `mutation:` recipe meets a conflict in the comments or on
the recipe line: keep its own values and take the `$(if $(SINCE),...)`, which
is what makes `SINCE` reach the script. And `gremlins.json` is now ignored at any depth, the way
`coverage.out` already is — a mutation report a project keeps deliberately, as a slice record's evidence,
must not be named `gremlins.json` or it stops being committed; name it for the run it belongs to, as a
report recovered by hand before this version already had to be. Anything a project built to rescue the
report from the staging directory can go.

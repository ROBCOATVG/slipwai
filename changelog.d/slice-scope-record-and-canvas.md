PATCH

**A slice branch run by `/cruise` can pass `make verify` again.** `check-slice-scope` refused two files that
two other gates require on a slice branch. `specs/<feature>/decisions.md`, which `/cruise` writes where the
ladder took the decision — during a slice's stages, that is the slice's branch — and which `check-decisions`
holds to `Written to` paths that exist only there, so the record could pass on neither branch. And
`docs/event-model/model.drawio`, which `check-drawio` requires to match the `model.yaml` block the slice is
allowed to advance, and which the scope gate refused as the host's docs. Both are now a slice's to write:
`decisions.md` beside the other cumulative artifacts the host merges in split order, and the canvas because
its own gate holds it to the model, so it can carry nothing of the slice's own. `commands/drive.md` and the
`drive-slice` brief say so, and say the canvas is regenerated again after each merge.

**A slice is compared with the newest `main` the checkout knows, not with `origin/main` first.** Both
`check-slice-scope` and `check-migrations` took `origin/main` as the base whenever it existed, so a `main`
that had moved locally and not been pushed — a migration run there, then merged into the slice — put its own
files into the slice's diff, and the slice stayed red until `main` was pushed, which `/catch-up`'s *green
before pushed* rule forbids while it is red. Every `main` is now tried and the base that is newest wins.
`/catch-up` and the upgrading page also say where a migration runs: on `main`, on a clean tree, never on a
`slice/<id>` branch.

**Catch-up.** `slipwai migrate` brings the two gates and the command text. A slice branch red on
`decisions.md` or `model.drawio` passes as it stands after the merge; a migration already run on a slice
branch is undone with `git reset --hard ORIG_HEAD` there and run again on `main`.

PATCH

**The dispatch ledger lives under `.slipwai/dispatch/`, not in `specs/`.** `make dispatch` now writes
`.slipwai/dispatch/<feature>.jsonl`, committed beside the run's other records, rather than
`specs/<feature>/dispatch-ledger.jsonl`, which sat in the feature's specification as though it were part of
it. A feature folder is what the product is to do; the ledger is evidence about how a run worked it. `/sail`
now also says how the ledger reaches trunk: in the merge that lands the first slice it names, never as a
commit of its own, because a push to `main` may be a deploy and one line of evidence is not a change.
`check-dispatch` and the `pre-push` hook read both homes, so nothing goes red between upgrading and
migrating.
The `pre-push` hook now judges the ledger in the commit being pushed rather than the working tree, so a
ledger written and never committed is refused before the push rather than by CI on a clean checkout.

**Catch-up:** `slipwai migrate` moves every committed `specs/<feature>/dispatch-ledger.jsonl` to
`.slipwai/dispatch/<feature>.jsonl` with `git mv`, in the commit it makes after the merge. Where a file is
already at the new home it is left alone and named in the report; append one to the other and remove the old
one when convenient.

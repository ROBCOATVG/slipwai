PATCH

**A migration no longer stops on `project.json` because its keys are in another order.** A project that
crossed from version 1 holds its manifest sorted, and the factory writes its own in the order it assembles
it, so git read every line as changed by both sides and each later `slipwai migrate` stopped on a conflict
whose only real difference was `generator.updatedWith`. `migrate` now merges `project.json` as the record it
is: a key only one side changed is taken, a key the project added (a `releaseMode`, say) is kept, and the
result is written in the order the project's copy already has. Where it was the only conflict the migration
is the one merge commit it always should have been. A key both sides gave different values is still a
conflict, left exactly as git leaves it. `slipwai replay` writes its `project.json` in the project's key order
too, so a merge made by hand meets a difference only where an answer differs.

**Catch-up:** nothing; the next `slipwai migrate` merges `project.json` this way, whatever order it is in.

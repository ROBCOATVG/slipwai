PATCH

**A checkout whose hooks path names its own `.githooks` in full is now treated as set up.** Some tools write
`core.hooksPath` as an absolute path. `make crossing` read that as somebody else's hooks and asked you to
chain them. In a slice's worktree, that absolute path also pointed at the main checkout's hooks rather than
the worktree's own. `make hooks`, `make crossing --fix-hooks` and `slipwai migrate` now rewrite it as
`.githooks`. A path to any other folder, such as husky's or lefthook's, is still left alone.

**Catch-up:** `slipwai migrate`, then `make hooks` once in each checkout.

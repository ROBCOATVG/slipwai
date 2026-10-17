PATCH

**On Windows the catch-up page is UTF-8, and `make dispatch` prints its ledger lines.** `slipwai migrate`
wrote `.slipwai/catch-up.md` in the machine's own encoding, which on Windows is cp1252, while `/catch-up` and
the archive read it as UTF-8 — so the first em dash on the page stopped both. It is written as UTF-8 now.
`make dispatch` printed each worktree after a `→` a Windows console cannot show, and stopped there with the
ledger written and nothing said; it prints `->`.

**Catch-up:** a catch-up page written on Windows before this version may not read; run `slipwai migrate` again
to write it afresh.

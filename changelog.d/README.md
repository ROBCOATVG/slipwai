# changelog.d

One file per change, `<slice>-<a-few-words>.md`. `make release` assembles them into `CHANGELOG.md`'s next
entry in the commit it tags, and deletes them.

A released entry is finished prose. The entry being written is not — every branch in flight adds a paragraph
to it — and while that entry was a block of lines at the top of one file, every pair of branches that
overlapped in time inserted at the same spot. `union` in `.gitattributes` made the merge itself clean and
was still not enough: a forge decides whether to *offer* the merge with `git merge-file` in a bare
repository, which knows nothing of merge drivers, so the pull request read as conflicted for a merge that
would have succeeded. One file per change has no shared line to conflict on, in any tool.

## The shape

```markdown
MINOR

**What changed, in a sentence a user would recognise.** Then a paragraph: what it does for them, and what
it cost if that matters.

**Catch-up:** what an existing project has to do to get it, as a command where there is one, or
`nothing; <why>` where the answer is genuinely nothing.
```

The first line is the level this change claims — `PATCH`, `MINOR` or `MAJOR`. The entry's level is the
highest any fragment claims: a release carrying a fix and a new option is a MINOR, not both.

**Write it for the person upgrading, not for the person who wrote it.** `slipwai upgrade` prints these, so
the reader is somebody who has just moved and wants to know what they got. "Refactored the registry" tells
them nothing; "a language package can now be installed from a git URL" tells them what is different.

**The catch-up line is the one people forget.** A change that needs `slipwai migrate` and does not say so
is a change that silently did not reach the projects that already exist. So `make check-release` refuses a
fragment without one: write `**Catch-up:** nothing; <why>` where the answer really is nothing.

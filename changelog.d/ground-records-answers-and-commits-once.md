PATCH

**`/ground` can record its answers one at a time and commit them once, as it says to.** `adopt --confirm`,
`adopt --decline` and `adopt --refresh` refused any uncommitted change at all, so the first answer was refused
by what `./init` had just left for the person to read, the second by the first, and the refresh by the rows it
exists to follow — and the first repository taken end to end got through by committing after every answer. They
now refuse only where they would write over somebody's work: a path they write, from the factory's `.written`
listing or the survey's pages, holding an uncommitted change that is not what slipwai last left there. What
slipwai left is recorded by digest in `.delivery-tools/written.json`, which every `.gitignore` the factory has
written already ignores, so it belongs to the checkout and is never committed. It is kept out of `.git` on purpose: Codex runs an agent's
commands in a sandbox that makes `.git` read-only, and a record there was silently never written.
`project.json`, what `./init` wrote and a person's own source no longer stop anything, because none of them is
written. `slipwai adopt` itself still refuses an unclean tree: it commits, and the `git reset --hard HEAD^` it
offers as the undo would take uncommitted work with it.

**The code-index guard holds only searches of its own repository.** A session opened in one repository searched
another checkout and was refused, because `version` is a name the first repository's index defines — an index
that cannot answer anything about code it never read. Where a search runs is now read from the hook's `cwd`, a
Grep `path`, or a `cd` earlier in the shell command, and a search wholly outside the repository is allowed.

Part of brownfield adoption, which is experimental (#74): what it offers may change in a MINOR, and what it
gets wrong belongs on that issue.

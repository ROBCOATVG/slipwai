# The entry being written

One file per change, and this one saying so. Together they are the `CHANGELOG.md` entry for the release
`VERSION` is a snapshot of; `make release` assembles them into it, in the commit it tags, and deletes them.
`CHANGELOG.md` itself holds released entries only, so nothing is ever appended to a line two branches share
— which is what a shared in-flight entry was: every branch adding its paragraph at the same spot, and the
forge calling the pull request conflicted even where Git merged it cleanly.

A fragment is a level and the prose, and the prose is the entry's, verbatim:

```md
MINOR

**One sentence saying what changed for whoever runs this.** Then as much as it takes — what was wrong, what
it does now, and why that is the right answer.

**Catch-up.** What this asks of a repository already generated: an answer to give, a tool to install, a
lockfile to take both sides of. Leave this paragraph out when a merge brings the change whole.
```

The first line is the level the change claims, from [AGENTS.md](../AGENTS.md#versioning-is-not-optional)'s
table — `PATCH`, `MINOR` or `MAJOR`, alone on the line. The highest level among the fragments is the
entry's, and it is the number `main` has to carry: `tests/test_changelog.py` fails when `VERSION` says
something else, so raising the number and claiming the level are one act rather than two.

Name the file after the change — `frontend-style-ownership.md`, not a date or an issue number — and write
it in the commit that makes the change, because the person making it is the only one who knows what it
costs somebody else's repository. `make changelog` lists what has landed since the last release, split by
whether it reached a user, so the fragment is a judgement rather than a memory test.

For the first public release, `VERSION` is `1.0.0.dev0` and there is no
released entry to bump from. Its fragments still carry a level so their shape
does not change; `make release` writes the first `## 1.0.0` heading without a
bump label. Every later release follows the arithmetic above.

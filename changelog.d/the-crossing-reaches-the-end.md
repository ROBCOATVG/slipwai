PATCH

**`slipwai migrate` crosses a version 1 project instead of ending in a traceback.** Two faults, both of
them only reachable on a real repository, and both of them raised after the crossing had already done its
work — which is the worst moment to say nothing useful.

**A project with its own design system.** The style checker resolves every path it returns, and the crossing
replays inside a staging directory under the system temporary directory — which on macOS is reached through
a symlink, `/var` being `/private/var`. So a token file the project imports was "not in the subpath of" the
project it is in, and the verb ended in a `ValueError`. Both sides of that comparison are resolved now, and
the page the crossing writes names the file the way the repository spells it rather than where the disk
keeps it.

**A model table the merge left conflicted.** The crossing carries version 1's model roles over by rewriting
`.specify/models.json`, and read the merged file to do it — including when the three-way merge had left
conflict markers in it, which ended the migration in a `JSONDecodeError` naming no file. A conflicted table
is now a line on the catch-up page saying what was not carried and what to set by hand, the way a conflicted
`project.json` already was: one unreadable file does not take the rest of the settings with it.

**Catch-up:** nothing, beyond running `slipwai migrate` again if it stopped on either of these. It changes
nothing until it reaches the end, so a crossing that ended in a traceback left your repository alone.

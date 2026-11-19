MINOR

**A package's release holds what its tag holds, and registering by hand lists the file that was published.**
`slipwai package release` and `package register` built the release file from the package directory as it
stood, so a clone holding anything a clean checkout does not built a different file from the one CI built
off the tag — an empty directory was enough, and it is how `codegraph` 1.0.1 was nearly listed under the
digest of a file nobody had published. A `.DS_Store` or a scratch note in the directory would have been
published with it. In a git repository the release now holds the files `HEAD` tracks under the package and
nothing else, so two clones of one commit build the same bytes; both verbs refuse while the package's
working tree differs from `HEAD`, naming what differs, as `migrate` does. Outside a repository the directory
is read as before, and a clean checkout builds the same bytes it always did, so no published digest moves.
The file is also compressed at a stated level, where a newer Python's default wrote a different file from
the same contents.

`package register` takes `--entry <file>`: the entry a release already wrote is listed as it stands and
nothing is built. A package's CI, where it has no token for the channel, now names that command.

**Catch-up:** nothing for a generated project. A publisher finishing a release by hand runs
`gh release download <tag> -p '<name>-<version>.json'` and
`slipwai package register . --entry <name>-<version>.json --channel <a channel checkout>`; a package
repository whose `dist/` is not ignored adds it to `.gitignore`, since an untracked file in the package
now refuses the next release.

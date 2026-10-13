PATCH

**`slipwai list` stops calling an installed target a language.** The four kinds of package share one
directory and are told apart by the manifest each carries; the installed half of the Languages listing read
every directory in it, so a target installed beside a language appeared under **Languages**, with its
version, as though a project could be generated in it.

The offered half had the same fault from the other end and was fixed first — this is the half on disk, and
the two are now the same rule: a language is a directory holding a `language.json`.

**Catch-up:** nothing.

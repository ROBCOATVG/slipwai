PATCH

**Every change now says what it asks of a project that already exists.** A migration's catch-up page reads
each change's **Catch-up:** line. Six changes in the 2.1 entry had none, so the page said "its author wrote
no catch-up paragraph", which leaves the reader guessing what it costs. `make check-release` now refuses a
change note without the line. A change that costs nothing says so with `**Catch-up:** nothing; <why>`.

**Catch-up:** nothing; a rule for the keel's own changelog.

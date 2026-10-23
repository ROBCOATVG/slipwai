PATCH

**A package's matrix runs with no managed target installed.** The matrix plans no production image where no
target is installed to deploy one to, and the run read that plan back as malformed — so every package CI
that installed no target ended its tag run on `backend <key> has no image, or more than one` before it
generated a row. A plan may now carry no image for a backend, and still not two.

**Catch-up:** nothing; a package's next CI run against the keel's `main` picks it up.

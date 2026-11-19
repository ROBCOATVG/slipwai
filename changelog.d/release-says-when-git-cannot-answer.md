PATCH

**A release says when git cannot answer, instead of packing the directory.** In a git repository a release
holds what `HEAD` tracks; outside one the directory is walked. Where git was not installed, or refused the
checkout — "dubious ownership" in a container or on a CI runner with a mounted checkout is the common one —
that read as "outside one", and the release was packed from the working directory without a word: whatever
the clone held, under a digest nobody could reproduce. Now, where there is a `.git` at or above the package
and git is missing or refuses, `package release` and `package register` refuse, quoting git's own line and
naming the fix (`git config --global --add safe.directory <path>`, or install git). A directory in no
repository is walked as it always was.

**Catch-up:** nothing; a release that was built from a checkout git answers for is the same file. Where a
release job now refuses, run the command the refusal names before it.

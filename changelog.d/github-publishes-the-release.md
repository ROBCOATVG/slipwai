PATCH

**GitHub is where slipwai lives and where it is published from.** `ROBCOATVG/slipwai` on GitHub is the
canonical repository; its standard runners are free for a public repository on Linux, macOS and Windows,
which is the three-platform gate this keel promises. A `v*` tag pushed there runs the gate on the tagged
commit, then builds and smokes the wheel and the executable on each platform, then publishes: the wheel and
source distribution to PyPI by trusted publishing, with no token stored anywhere, and a GitHub release for
the tag carrying each platform's executable and its `.sha256`. Nothing is published from a fork, from a pull
request or from `main` without a tag.

The project's links, the presets' `repository` and the upgrade message for the executable now name
GitHub, and the README carries the gate's badge and the Python versions beside the PyPI one.

**Catch-up:** none for a project. A copy of the executable installed earlier is replaced from
`https://github.com/ROBCOATVG/slipwai/releases`.

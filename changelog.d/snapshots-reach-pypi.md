PATCH

**`slipwai upgrade --pre` finds main's snapshots again.** Every push to `main` that passes now sends its
numbered snapshot (`2.1.0.dev113` and on) to PyPI, as version 1 did, as well as to the `dev` prerelease.
Since 2.0.0 snapshots went to the prerelease alone, which `upgrade` never reads, so an install on a snapshot
was told 2.0.1 was the newest there was however far main had moved. Releases are untouched: a `.dev` build is
a pre-release to `pip` and `uv`, so an install that never asked for one is never moved onto it.

**Catch-up:** nothing for a generated project. An install made from a checkout (`uv tool install` from a
directory) keeps rebuilding from that directory; to follow the snapshots instead, reinstall once from PyPI
with `uv tool install --force --prerelease allow slipwai`, and `slipwai upgrade` keeps it current after that.

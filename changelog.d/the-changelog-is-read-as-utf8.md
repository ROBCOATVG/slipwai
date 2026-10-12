PATCH

**`slipwai upgrade` on Windows offered a project the release it already had.** The catch-up notes are read
from `CHANGELOG.md`, whose entries are headed `## 2.0.0 — MINOR` — with an em-dash. The file was read in
the machine's locale encoding rather than as UTF-8, so on Windows that heading arrived as
`## 2.0.0 â€" MINOR`, no entry matched, every released version looked unreleased, and the release in flight
was offered a second time on top of the entry already in the changelog.

Nothing was lost and nothing was skipped — the notes were duplicated, not dropped. The read names its
encoding now, and the test that holds it forces a non-UTF-8 locale in a subprocess, so it is proved on
every platform rather than only on the one runner that happened to say so.

**Catch-up:** nothing. Run `slipwai upgrade` again if the last run's notes repeated themselves.

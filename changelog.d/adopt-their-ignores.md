PATCH

**Adopting a repository whose `.gitignore` matches a delivery path no longer stops half-done.** An older
`.gitignore` with a bare `bin`, `build` or `scripts` rule — the Python template has `bin` — matched a file
the adoption writes, such as the codegraph launcher under `scripts/extensions/codegraph/bin/`, and `git add`
refuses an ignored path it is named. The adoption wrote everything, staged it, and failed before its commit
with a traceback, so `init` never ran. Slipwai now force-adds the files it writes itself, so they are
committed whatever the repository's ignores say; grounding, the strategy decision and the migration
manifest stage their files the same way.

**Catch-up:** nothing for a repository that adopted cleanly. One that stopped at this error: reset it to
the commit before the adoption (`git reset --hard HEAD && git clean -fd` with nothing else uncommitted) and
adopt again.

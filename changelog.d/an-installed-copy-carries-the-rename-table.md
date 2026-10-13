PATCH

**`slipwai migrate` works in an installed copy.** It applies the committed rename table to a version 1
project, and read that table from beside the keel — where the wheel, the source distribution and the
executable had never carried it. In a checkout the file is at the repository root and every gate was
green; everywhere else the verb ended in a `FileNotFoundError` naming a path inside the installed package.
All three distributions carry it now, and a copy that somehow has not got it refuses in one line saying
nothing has been changed, rather than raising a traceback at somebody halfway through a migration.

**What a distribution carries is now said once.** `assets.BUNDLED` names it, and `tests/test_bundled.py`
holds the wheel, the source distribution and the executable's spec to that list — the gate that was missing,
since the one thing no checkout can notice is a file it has and an installed copy does not.

**Catch-up:** `slipwai upgrade`, or reinstall, if `migrate` ended in a traceback for you.

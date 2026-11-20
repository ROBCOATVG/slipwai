PATCH

**A further feature's slices are built, merged and logged like the first feature's.** A project has one chart,
written under its first feature, and a later feature's slices are rows on it that name their own feature. The
fleet took the chart's feature for every slice, so a later feature's slice was read in the wrong folder: its
hand-overs counted as failed attempts, its story was never owed a seed, its capability's gates were not found
at the merge, `clearance.py --feature <later feature>` refused to answer, and its decisions hid behind the
first feature's of the same number. A slice's files are now read under the feature its chart row names. A
stream has one log, under the chart's feature, and a session is told where it is in `$SLIPWAI_DECK`; lines a
session already wrote to a log under the later feature are still read, and still travel. A project with one
feature behaves as it did.

**Catch-up:** `slipwai migrate` carries the toolkit's scripts under `scripts/agents/`, `scripts/render-fairways.py`
and the three pages that say where a session writes its lines (`/sail`, `/chart`, the captain's brief).

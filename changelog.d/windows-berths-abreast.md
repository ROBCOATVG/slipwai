PATCH

**Slices running abreast on Windows no longer park because a sibling's berth was being made at the same
moment.** Git on Windows can read another worktree's half-written admin folder and refuse with `failed to
read .git/worktrees/…/commondir`, and the captain then parked the slice as having no berth. It now waits a
moment and tries again, up to four times, and parks only if git still refuses. macOS and Linux are unchanged.

**Catch-up:** none.

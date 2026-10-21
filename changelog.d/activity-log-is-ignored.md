PATCH

**The live activity log is ignored by Git.** `.slipwai/activity/`, where each slice's activity is written for the board's Now strip, is now in the project's `.gitignore` with the rest of the run state. Before, it was an untracked folder, and `slipwai migrate` refused to run until it was moved.

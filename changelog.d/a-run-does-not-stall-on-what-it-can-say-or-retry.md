PATCH

**A run no longer stalls on a worktree git refused once, a refusal that names no reason, or a conflict git
hid.** A project's second feature stopped with every remaining slice waiting for a person, for three causes.

- *A slice's worktree is made without an upstream, and tried again where only the branch was made.* Cut
  from `origin/main`, git wrote each new branch an upstream in `.git/config`; with several made at once one
  attempt lost that file, the branch was left with no worktree, and the slice parked for a person on a
  command that works when run again.
- *A refused merge says what the failed check said.* The refusal carried make's line alone, such as
  `make[1]: *** [check-decisions] Error 1`. It now carries the failing target and the check's own last
  lines, so the slice is told which decision, row or file the check named.
- *The harbourmaster's rebase does not use `rerere`.* Where a checkout has it on with `rerere.autoupdate`,
  git staged a conflicted file from a recorded resolution and still stopped, leaving no path unmerged: the
  merge was refused for "files git did not name", and nothing could weave the file or send the mender.

- *Merge attempts are counted per cause.* A slice refused for its capability gates, then for a conflict,
  then for a check, has answered each one; it parks only when the same refusal has come back `attempts`
  times. The runs one slice may have between a person's words still bound the whole.
- *A park answered from the terminal gives the slice its runs back.* `harbourmaster.py --clear` writes its
  `cleared` line `by: person`, and it counts as a person's word as a `told` does. A slice cleared that way
  parked again on its next run as spent.
- *A park about a slice that has merged since clears itself.*
- *Another slice's `code` list follows a file this slice moved.* `check-model` wants every path a block's
  `code` names to exist; a slice that renamed or deleted a file an earlier slice lists could not correct the
  list, and the fleet could not land the correction ahead of the slice. `check-slice-scope` now allows that
  one change to another slice's block: paths gone from the tree leave its `code` list, and paths added to
  it exist.

**Catch-up:** `slipwai migrate` carries `scripts/agents/harbourmaster.py`, `captain.py`, `moorings.py` and
`scripts/check-slice-scope.py`. Nothing to
change in a project. A slice already parked on *a worktree … could not be made* is answered once (say go)
and carries on.

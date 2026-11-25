PATCH

**Your checkout now keeps up with trunk while the fleet merges, and commits only it holds are named instead of
left silent.** Before, the harbourmaster pushed each merge to the forge and never touched your local `main`, so
on a long run your checkout fell further and further behind. The board read that old project as if it were
current, the harbourmaster ran the scripts it held, and commits you made on that `main` were never pushed and
never mentioned. On manda that was 493 commits and three of the person's own records. Now, after each push:

- **If your checkout is on trunk**, it is fast-forwarded with git's own `merge --ff-only`. Where an
  uncommitted change would be overwritten, git refuses, the tree is left exactly as it is (never detached,
  reset or rebased), and the merge's `granted` line says so.
- **If it is on another branch**, the local trunk ref moves only as a strict fast-forward, the way `git fetch
  origin main:main` would move it, and never under a worktree that has it checked out.
- **If local trunk holds commits the forge's does not**, it is never moved. The harbourmaster names those
  commits at start and at every merge. The board puts them under *Waiting on you* with their subjects and how
  to land them: put them on a branch and push it.

The board also says at the top when the folder it reads is behind the forge's trunk, and by how many commits.
The harbourmaster says at start when its checkout is behind. After a merge that changes its own scripts on
disk, it says it is running older code and wants a restart.

**Catch-up:** `slipwai migrate` brings the new harbourmaster. Your checkout may already be behind, so before
pulling, run `git log --oneline origin/main..main` (use your trunk's name if it is not `main`). Any commits it
lists are yours alone: put them on a branch and push it (`git branch keep-local main`, `git push origin
keep-local`), then `git switch -C main origin/main`. With nothing listed, `git pull --ff-only` is enough. Then
restart the harbourmaster.

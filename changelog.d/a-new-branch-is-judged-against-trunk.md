PATCH

**The first push of a branch is judged against trunk, not the whole history.** Git's `pre-push` reports
forty zeros for a branch the remote has never seen. The dispatch gate treated that as every commit
reachable from here, so a project with any pre-ledger history could not push a new branch at all — the
refusal named commits already on trunk. The range is now the same one `make check-dispatch` already uses
with no arguments: trunk, up to the branch being pushed.

**Catch-up:** nothing. The next push uses the corrected range; nothing already in the repository has to
be rewritten.

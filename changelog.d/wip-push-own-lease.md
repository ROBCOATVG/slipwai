PATCH

**The harbourmaster no longer blames another machine for its own earlier push.** On a harbour of one
machine, its log could fill with "refs/slipwai/wip/accounts moved under this pass … which is another machine
holding slice/AC2" on every pass. The push was guarded by this machine's own copy of the ref, which can go
missing or fall behind while the forge still holds what this machine pushed. Now, when the forge's commit is
one the branch holds, or held before a rebase, the push goes ahead. Only commits this machine has never seen
are named as another machine's.

**Catch-up:** `slipwai migrate` carries the new `scripts/agents/travel.py`.

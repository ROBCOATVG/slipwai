PATCH

**Triage, and any stage run while a fleet is going, no longer commits onto your local `main`.** The board's
triage used to commit its proposals onto local `main` in your checkout and push nothing. The harbourmaster
could then not bring that `main` up to the forge's without throwing those commits away, so it left it, and
the board — drawn from that folder — showed an ever older project. Triage now commits on `triage/<numbers>`,
built from the forge's trunk, without touching your checkout. It pushes that branch, and the harbourmaster
lands it through the full gate like a slice. Assess, draft and launch, while a harbourmaster is running,
work on a branch of their own (`assess/<slug>`, `draft/…`, `launch/<feature>`) and are landed the same way.
When local `main` does hold commits the forge has not got, the board says so once under *Waiting on you*,
with the safe fix. A branch the harbourmaster would not land is listed there too. And the captain's
timeline now shows a merge's `note` (why your checkout was not brought level) instead of hiding it.

**Catch-up:** `slipwai migrate` and `/catch-up` check whether local `main` has commits `origin/main` has
not got (`git log --oneline origin/main..main`), and the page lists them. Nothing moves them. Put them on a
branch (`git branch keep-local main`, `git push origin keep-local`), open a pull request, and only once it
has merged run `git switch -C main origin/main`.

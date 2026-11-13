PATCH

**A story step can wait for what a worker writes.** A step that reads something a sweep writes after an earlier
step — a recap, its speech, a transcript — says `"wait": <seconds>` in `try-it.json`, and Try it asks it again
each second while the answer is a 4xx, until the time is up. recap's catch-up stories asked for a recap and
then for its speech at once, and whenever the seed outran the sweep the speech was a 404 and four stories
failed on a machine that was merely quick. A step with no `wait` is asked once, as before.

**Catch-up:** `slipwai migrate` brings the new `scripts/agents/try_it.py` and the ladder's page; add `"wait"` to a story step only where it reads what a worker writes later.

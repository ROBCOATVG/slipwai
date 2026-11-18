PATCH

**Two captains starting at once no longer lose a slice's live session to npm.** An agent launched through
the package runner (`npx`) is fetched into a cache the launches share. Two captains launching the same agent
in the same second met there — `ENOTEMPTY: directory not empty, rename …` — and one slice fell back to print
mode for its whole run: no messages, no interrupt, no pause. Such launches now take turns on a machine until
each has shaken hands, and one that falls over because the runner itself exited is tried once more.

**Catch-up:** run `slipwai migrate` to carry the corrected launch into a project; nothing else to do.

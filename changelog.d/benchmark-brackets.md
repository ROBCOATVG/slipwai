MINOR

**A benchmark bracket now counts only its own lines, an entry a session leaves open is cut off rather than left
running, and a delivered slice with no record fails `make verify`.** A run's records showed all three holes: two
skipper rounds opened while the implementers were running counted the implementers' Sonnet tokens as the
skipper's; two entries opened by an iteration that was then stopped stayed open for good; and a whole slice was
delivered with no record at all, through a gate that only ran the script's self-test. Now a line goes to the
innermost bracket covering it, and a delegate's lines to the bracket whose stage owns the type that ran them,
across every record in the project, with the request count left to another bracket written into the entry's
`read`. The `/cruise` runner closes what an iteration left open — when it ends, or when `stop --now` ends it —
as `cut off` with the reason, no tokens and no signals, and the overview's notes say so. And
`python3 scripts/agents/benchmark.py check`, run by `make check-benchmark`, fails on an entry still open, on a
slice the ladder calls done (a row in `slices/README.md`, or `status: implemented` in the event model) with no
record or an unclosed one, and on a feature with done slices and no record above the slice loop. Two things
found on the way: `make check-decisions` now also holds every finished slice to a row in `adversary-log.md`,
the attack or the recorded skip `/adversary` writes after every acceptance, which nothing checked; and the
runner ends an iteration's whole process group, so `stop --now` no longer leaves a dev server the session
started running on.

**Catch-up.** `slipwai migrate` brings the script, the runner and the Make target. A project whose delivered slices
have no record will fail `make verify` on the next run: those brackets cannot be recovered, so either write the
missing records by hand as unbracketed entries, or accept the finding until the next slice.

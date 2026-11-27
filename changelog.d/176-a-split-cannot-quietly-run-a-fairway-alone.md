PATCH

**A split can no longer quietly make a fairway run one slice at a time.** The split template offered `—`
for "none" in `depends_on`, and the fleet read the same `—` in `parallel_ok_with` as "runs beside nothing".
A split written with nobody present put `—` on every row of a 38-slice fairway, which then ran serially all
night with sessions free. `—` now means "nothing declared" in both columns. "Runs beside nothing" is the
word `alone`. The split stage fills the column from what slices would actually collide on (the same
stream, screen or file) with `python3 scripts/agents/beside.py --fill`, and records that as a decision for
a person to confirm. `make check-chart` refuses a fairway of more than one slice whose column was never
filled, or in which no two slices may run together, unless a decision says why. The board now says "can
only run one slice at a time because the split says so" where it used to show an ordinary *working*.

**Catch-up:** `slipwai migrate` lists any fairway whose split has `—` on every `parallel_ok_with` row and
no decision about it. For each one, `/catch-up` runs `python3 scripts/agents/beside.py --fill --feature
<feature>`, then `make check-chart`, and you commit the split and `decisions.md`. Until you do, those
fairways run unrestricted: slices that share a stream or a screen are no longer kept apart. A running fleet
picks up the refilled graph at its next boundary, with no restart.

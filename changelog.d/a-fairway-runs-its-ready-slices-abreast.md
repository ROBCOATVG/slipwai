MINOR

**The fleet now runs a fairway's ready slices at the same time, each in a worktree of its own.** A person who
typed `/sail fairway=<name>` had every ready slice fanned out, because rule 6 of *Ready-set selection* says to
run them concurrently. The fleet, given the same fairway, dispatched one slice per turn — so a split with a
walking skeleton and twenty-two independent slices behind it ran those twenty-two one after another. Now a
captain starts every slice that is ready and that the slice graph lets run together. Each slice runs in
`../<project>-<id>` on `slice/<id>`, with its own session, stage bound, retries and gate, and its own merge
request. As each one merges or parks, the next ready slice starts in the space it left. Merges still go one at
a time through the harbourmaster, so every slice is rebased and gated on the trunk the last one left.

**Ready now includes the slice graph's `depends_on`.** Clearance used to read marks alone. A split whose
slices steer by no mark but depend on a walking skeleton was offered all at once while the skeleton was still
being planned. `clearance.py` now reads `depends_on` where `/sail` says the graph is: each slice's entry in
`docs/event-model/model.yaml`, or `## Slice graph` in the split. A slice whose dependency has not merged reads
`blocked` and names it. The split's `parallel_ok_with` decides which ready slices may run side by side. A
slice it does not mention may run beside any other, as the page has always said.

**`boilers` now counts slice sessions across every fairway, not captains.** The harbourmaster shares them out
on every pass, and it writes the result as a `slots` line per fairway in the harbour log. Every fairway with
work gets one session before any fairway gets a second. Spare sessions then go by your fairway order, then by
the slice whose merge unblocks the most, then by the fairway with the most ready slices. A fairway waiting on
a merge answer starts nothing new, and no running slice is ever stopped to make room. A new setting,
`abreast`, caps how many slices one fairway runs at once. It defaults to 3 and is never more than `boilers`:

```sh
slipwai telegraph --set abreast=1     # one slice at a time in every fairway: the fleet as it was
```

**A park can now hold one slice and leave its siblings running.** A `parked` line that names a `slice` holds
that slice only. A park that names no slice still holds the whole fairway. A stop ends every slice in flight
and writes a `stopped` line for each one. The next captain lit carries all of them on, not only the last one
claimed. The board's slice column lists every slice in flight.

**Catch-up:** `slipwai upgrade` brings the new `scripts/agents/abreast.py` and `moorings.py` and the changed
captain, harbourmaster, clearance and fleet scripts. Check that `chart.yaml` and the slice graph are
committed, because a slice running abreast works in a worktree made from what is committed. To keep one slice
at a time, run `slipwai telegraph --set abreast=1`.

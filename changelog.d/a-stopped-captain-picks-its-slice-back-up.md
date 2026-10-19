PATCH

**A slice in flight is carried on whatever stopped its captain.** A captain killed, stopped or rebooted and
relit on the same machine took its own claim back, found no park and no takeover, stepped past the slice it
had claimed and said *nothing to start* for ever. A slice claimed and not merged is now resumed whenever it
is not parked, unless another captain on the same machine is working it at that moment.

**`fleet stop` ends the running stage and writes `stopped`.** The captain had no handler for the signal, so
it died where it stood: its `/sail` went on running with nothing watching it, the claim stayed taken and the
log said nothing. Now the stage's whole process group is ended, a `stopped` line names the slice, the claim
is given back once that line has travelled, and `fleet stop` says this instead of promising a boundary. The
board shows such a stream as `stopped` rather than, after a while, `stalled`.

**A dead harbourmaster is started again.** Nothing restarted one while any captain was alive, so a captain
waiting on a merge sat out the wait bound and parked a slice that had passed its gate. Each captain now
checks at the top of its turn and while it waits on an answer. Where the harbourmaster's pid file names a
process that has gone, the captain starts a new one and says so. It holds a lock while it does, so that
two captains start only one. A harbourmaster with no pid file, which is one a person started by hand, is
never doubled.

**A run that falls over is retried before it parks.** A missed mark, no demo, a stage ended because its log
went quiet and a `/sail` that exited non-zero all parked on the first run. Only a demo sent back was
retried. They now all count against `attempts`. Each retry is told why the last run did not close, in its
prompt and in `SLIPWAI_RETRY`. When `attempts` is spent, the park gives the last reason and how many runs it
took.

**Catch-up:** none needed. Fairways stuck on *nothing to start* with a slice claimed and not merged pick it up
on their next turn once this version is installed.

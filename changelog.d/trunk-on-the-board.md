PATCH

**A red trunk, and what the trunk mender did about it, are on the board.** The Voyage shows a band above its
tabs whenever trunk is red: at which commit, since when, which jobs failed, that no merge is granted until it
is green, and what is being done about it — the mender's attempt in flight and how long it has run, a fix
that landed and waits on CI, or the mender's attempts spent and a person deciding. It says *Trunk is green
again* for a while once a mended trunk passes, and nothing otherwise. The Fleet tab has a Trunk card with each
attempt (when, commit, branch, outcome, why), what the attempt in flight is doing, the mender's own last
answer rendered as a document, and the CI run's link where the run carries one. The mender's output is read
from its tail, and only when it has changed. A trunk the harbour parked for a person is listed under *Waiting
on you* and counted, linking to the band; trunk going green is the only thing that clears that park, so the
band says so rather than offering a button. A slice whose merge a red trunk holds says on its card that it is
waiting for trunk to be green.

**Catch-up:** nothing; the board is served from the installed command and reads the logs the fleet already writes.

PATCH

**A park written before needs were records no longer stops its captain, and a log nobody can read is
waiting on you.** A park whose `needs` were sentences, as they were before each need became `{"what", "by"}`,
is read as needs only a person can tick; writing one is still refused. Before, the captain refused the
whole log at that line and exited at every relight, and the board drew the stream with nothing waiting —
recap's library sat like that for twelve days behind LB10's park. Now any deck log the board cannot fold is
listed under *Waiting on you* as *Repair a log*, naming the line that broke, and `slipwai fleet` lists it
the same way.

**Mark every one shown as read no longer fails on your own answers.** A decision you answered was drawn
unread on the Decisions tab — counted in its badge, shown under *Unread* and sent with *Mark every one shown
as read*, which then said `nothing to mark read`. It is drawn read, as the log already held it.

**A build with every slice merged says it is built, and says what it has not been shown.** The voyage held
the Slices stage at *stopped until you act* over notes and old questions once every slice had merged, the
Fleet headline called a stream with nothing left in it *stalled* because a person's read receipts came
after its last merge, and the Accepted stage read *every capability demoed* over a run with no `accepted`
line at all. Now Slices is done once every slice has merged (an open park still holds it), the headline
reads *Built: every stream has merged what it claimed*, and Accepted says no capability has been through
its gates or demoed yet, and that `/sail` is what takes each one there.

**A slice with a try-it story cannot merge until the story ran green, or says what keeps it dark.** The
captain's `seeded` check ran after the turn, and a turn that had merged was counted as done before the check
was reached, so recap merged five slices whose stories never seeded, two of which never could. The
harbourmaster now refuses that merge, as something the berth can fix: seed the story with
`try_it.py seed --slice <id>`, or, where it is dark until a shared need lands, hand the need back with
`fleet.py tell --need` and ask again.

**Try it signs a declared person in by the name their realm stores.** In a realm with
`registrationEmailAsUsername`, a person declared as `ines` is stored under her email, so every story signed in
as `ines` was refused `invalid_grant`, and the next start looked her up by the short name, found nobody, and
stopped on a 409 creating her again. Try it now uses the email where the realm makes it the username, and the
card shows that name.

**Try it starts what a project's stories connect to.** A project lists the processes to run beside its apps
in `docker/try-it/alongside.json`, each a `name`, a `run` command and the `answers` address Try it waits on,
such as a stub of a server a story connects to. Try it starts them before the apps and stops them with the
apps. recap's six stories that connect an Audiobookshelf server answered `serverUnreachable` on every run
until its stub was listed there.

**Catch-up:** `slipwai migrate` brings the toolkit's reader to an existing project, so its captains read the
older parks; the board's part arrives with the upgrade itself.

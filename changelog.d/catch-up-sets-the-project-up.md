MINOR

**The catch-up notes now open with the way from a merge to a project your coding agent can work in, whether
or not the migration stopped at conflicts.** A migration that stopped at conflicts used to leave the rest of
the way — `slipwai migrate` again, `make agents`, a new agent session — in a report that scrolled off, so a
project could be merged with its agent still running the old ladder and only a failing `check-agents` to
say so. `.slipwai/catch-up.md` now opens with *First: set the project up* on every migration, the crossing
from version 1 included. It names the files the merge stopped at and walks seven steps in order: resolve
each file (take the factory's side of `commands/sail.md` and the other generated pages, then re-apply your
own edits), commit, `slipwai migrate` again, `make agents`, `make check-agents`, start a new session, and
confirm with `make crossing` and `make verify`. A clean migration did the first four steps itself, and the
section says where to start. The stop report points at the section rather than repeating it, and `/catch-up`
will not go on while a merge is in progress or `check-agents` fails.

**A catch-up page is archived, never deleted or overwritten.** The page used to be thrown away when the work
was done and overwritten by the next migration, losing the one record of what that upgrade asked. Now each
page ends naming its own archive path, `.slipwai/catch-up/archive/<from>-to-<to>-<UTC time>.md`. `/catch-up`
moves it there when the work is done. Before writing a new page, `slipwai migrate` moves whatever page it
finds there too, the crossing from version 1 included. A page from before this change is named from the
versions in its title and the time it was last written. A page already archived is never archived twice, and
an archived page is never overwritten: a different page under the same name takes the next free suffix. The
archive stays on the machine and is git-ignored, like the page.

**Catch-up:** `slipwai migrate` brings the new `/catch-up` page and the `.gitignore` line for
`.slipwai/catch-up/`. A `.slipwai/catch-up.md` left by an earlier upgrade is moved into the archive by that
same migration, so there is nothing to do by hand.

Step 4 of that section says `make agents` installs a coding agent the project has moved to since `./init`,
where that agent names itself in its environment, and that `./init --integration <agent>` is for the case it
could not tell — rather than sending everyone to `./init`.

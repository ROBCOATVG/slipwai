PATCH

**The first merge gives a new remote its trunk.** The harbourmaster pushed a merge only where the remote
already had trunk, so a project given a remote on the board — an empty repository on the forge — merged on
this machine indefinitely: nothing reached the repository and its CI never ran, without anybody being told.
The first merge now pushes trunk there and moves the local branch with it, and every merge after pushes as
before. Where the forge cannot be asked although there is a remote, the refusal says to create the
repository or sign `gh` in, rather than to add a remote that is already there.

**A brief naming a cloud whose package is not installed is still read as naming it.** The places a brief
can say were read off the installed targets alone, so on a machine without that target's package the line
read as not said and the build started on this machine with no word about why. The clouds the carried
quickstarts start on count too, and the hand-over says the target is what is missing. The first page asks
for "your own cloud account (which one?)" rather than offering two by name.

**Catch-up:** a project whose remote never got trunk: its next merge pushes it, or `git push -u origin main`
now.

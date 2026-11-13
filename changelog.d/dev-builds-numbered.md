PATCH

**Each dev build of main now has its own version number.** Every build published from main used to say
`2.1.0.dev0`, though each was different code. Each now carries the number of commits since the last release,
for example `2.1.0.dev52`. Every new build sorts above the last and below the release itself. This lets
catch-up tell which builds a migration crossed, and lets the app tell when a project was written by a newer
dev build than the app.

**Catch-up:** nothing; install the next dev build.

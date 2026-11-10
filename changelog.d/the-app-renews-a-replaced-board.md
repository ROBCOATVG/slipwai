PATCH

**Opening a newly installed app opens the board it installed, not the one it replaced.** The board runs as
a login service, so dragging a new `Slipwai.app` over the old one left the board running the old file from
the Trash, and opening the new app opened that. Every answer the board gives now names the file it was
started from, and the app, finding a board started from its own path but from a file no longer there,
reloads the service before it opens the page. A board too old to say is reloaded the same way on a Mac. A
board from another path, such as a `slipwai` of your own, is left alone. On Windows, placing the new
`slipwai-board.exe` moves the running one aside instead of failing to overwrite it, and the board it was
running is stopped and started again from the new file.

**Catch-up:** nothing; how the app starts, and nothing a project carries.

PATCH

**The Windows app shows that it is opening.** Opened from a download, the app showed a blank terminal that
closed again, then nothing, and the board's page a good while later. The app is one file that unpacks
itself before it runs, twice on a first launch, and then waited fifteen seconds for a board that Windows
starts only at the next sign-in. It now shows the slipwai mark from the moment it is opened, with a line
under it — *Installing slipwai...*, *Starting the board...* — until the page opens; the blank terminal,
which was PowerShell writing the Start menu shortcut, is no longer shown; and the fifteen seconds are gone.
The picture is for a double-click alone: the board at sign-in and every `slipwai` an agent runs open
without it. Nothing changes on macOS or Linux.

**Catch-up:** nothing; install the new build. The Startup file and the `slipwai` wrappers are written
again by the app's next launch.

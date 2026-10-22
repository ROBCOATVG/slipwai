PATCH

**The plan's progress script and the two other history readers decode git as UTF-8, and a captain on Windows
says its line whatever character is in it.** On Windows a pipe is read on a thread, and a commit message with
one byte cp1252 has not got — the `←` in a body here — killed that thread and left the output `None`, so the
progress gate fell over on every Windows run. And a captain whose words carried the harness's replacement
mark ended in a traceback at `print`; its streams replace what the console cannot show.

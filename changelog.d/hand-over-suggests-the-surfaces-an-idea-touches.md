MINOR

**The hand-over says which existing surfaces an idea seems to touch.** The agent in **Hand over a further
feature** is now asked to name the screens or other surfaces the project already has that the idea seems to
change. What it names is saved with the idea as `docs/intake/<slug>/surfaces.json` and shown under the idea on
the **Next features** tab as *Seems to touch (a suggestion)*. It is a hint and says so in itself
(`"authoritative": false`): nobody checked it against the app, nothing acts on it yet, and the storyboard
stage is free to start from it and end somewhere else. An agent that names none leaves no file.

**Catch-up:** `slipwai migrate` brings `docs/intake/README.md` its description of the file; ideas captured
before this have no hint, and need none.

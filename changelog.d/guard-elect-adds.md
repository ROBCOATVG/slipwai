PATCH

**Agreeing to one extension's guard no longer withdraws the others.** `guards.py --elect <key>` wrote the
registry from the keys it was given and nothing else, so a second agreement silently removed the first,
and `./init --extension <key>` on a project that already had an agreement did the same. `--elect` now adds
to what is agreed, and `./init` asks only about the extensions it was given. Taking an agreement back is
its own command: `python3 scripts/extensions/guards.py --remove <key>`.

**Catch-up:** `slipwai migrate` brings the script, and `.slipwai/guards.json` is read as it is. If you
agreed to more than one extension's guards and only the last one fires, run
`python3 scripts/extensions/guards.py --elect <key>` once for each of the others.

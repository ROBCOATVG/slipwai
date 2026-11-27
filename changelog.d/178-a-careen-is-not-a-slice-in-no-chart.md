PATCH

**`make crossing` no longer reports a finished careen as a slice folder in no chart.** A careen slice
(`<fairway>-careen`) is started by the captain after every planned slice of its fairway and is never put on
the chart, so its folder under `specs/<feature>/slices/` is finished work. The report flagged it anyway and
told you to add it to the model, which would have been wrong. It now recognises a careen's id the way the
captain names it, and still asks about any other folder the chart does not name.

**Catch-up:** nothing; `slipwai migrate` brings the corrected `scripts/check-crossing.py`, and a careen
folder it used to flag needs no change.

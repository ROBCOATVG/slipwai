PATCH

**`slipwai release-state` writes the product's state on the line a migration writes it.** It put `state`
after `target`, but the factory writes it after `shape`. The next `slipwai migrate` merged the two
positions and left the key in `project.json` twice, which lean-coffee-club found. It now goes where the
factory puts it.

**Catch-up:** where `project.json` holds `"state"` twice, delete the copy after `"target"`. Both copies say
the same thing, and the last one is what is read.

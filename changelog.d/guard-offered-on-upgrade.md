MINOR

**A guard that an extension gained on an upgrade is now said, with the command that agrees to it.** A guard
was only ever offered at `./init`, so a project that elected an extension before it had a guard was never
asked, and the guard never fired. `slipwai migrate` now prints a line for each elected extension with a
guard nobody has agreed to, and writes it on the catch-up page. `make agents` prints the same line every
run, and asks at a terminal. Neither agrees for you: with no terminal, `.slipwai/guards.json` is left
exactly as it was. A guard whose declaration changed since you agreed to it is said in the same way, and
the one you agreed to goes on firing until you agree again.

**Catch-up:** `slipwai migrate`, then read its last lines or run `make agents`. For each extension named,
`python3 scripts/extensions/guards.py --elect <key>` agrees; doing nothing leaves the guard off. An
extension author does nothing: declare the guard in `extension.json` and never write the registry.

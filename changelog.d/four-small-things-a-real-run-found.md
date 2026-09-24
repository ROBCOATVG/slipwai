PATCH

**A flag that describes the adoption is refused on a `--confirm` or `--decline` run, rather than read and
thrown away.** `slipwai adopt --confirm shop --integration cursor` looked like it recorded a coding agent and
recorded nothing: the settling path never reads those flags. It now names each one and says where it belongs —
`--integration` after the method is installed is `./init`'s. The same rule the reshaped intro already applies
to flags that describe an application, and nothing that previously worked stops working: a flag that did
nothing now says so.

**`check-codegraph` no longer fails a repository for files CodeGraph deliberately declined.** It inferred what
should be indexed from the suffixes already in the index, so a vendored `bootstrap.min.js` beside a `src/app.js`
read as a hole in the graph — and a real adoption failed a gate that `codegraph sync` said was already up to
date, the two tools calling each other wrong. Which files belong in the index is CodeGraph's decision; a file
the index has never seen is now a finding only where it appeared *after* the index last ran, which is the
question the check was always asking.

**A harness that cannot be projected says where its skills live instead of only that they are elsewhere.** The
registry already records the reason — Hermes keeps them at `~/.hermes/skills` — and the refusal now quotes it,
because a person told "outside the repository" still has to go and find out where.

**`docs/change-strategy.md` stopped opening by asserting that `make verify` is green.** It is written before
any gate has run, and on a repository whose build tool is not on the machine it is not true. The page says what
the gate actually does instead: runs the build's own commands, green where the ratchet has a baseline to hold
them to and plainly red where it does not.

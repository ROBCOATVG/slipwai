MINOR

**`slipwai upgrade` moves an installed extension as it moves a language.** It listed each extension against
what was published and left the moving to you, one `extension install` at a time. Now an extension that a
newer compatible release reaches is upgraded in the same run; `slipwai upgrade --check` prints the command
that would run and changes nothing; and one whose newer release needs another core schema is held back, with
that reason, in the words a language gets. `slipwai extension upgrade [<key>...]` is the same move by name,
or for every installed extension where you name none. An upgrade agrees to nothing for you: a release from a
publisher this machine has not accepted is refused, with the command that accepts them, and the upgrade
exits non-zero; and a guard a newer package declares is still agreed to in each project, at election.

**Catch-up:** `slipwai upgrade`, then `slipwai migrate` in each project that elected an extension that moved —
the installed package is what moved, and a project's copy under `scripts/extensions/<key>/` follows at its
next migration.

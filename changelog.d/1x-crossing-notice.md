PATCH

**`slipwai upgrade --check` explains the crossing when its registry offers version 2.** A version 1 copy
now links the migration page, names the check and migration commands, and says what crossing costs:
package setup, renames, three-way conflicts and fairway confirmation.

It fires on version 2 **or anything past it**: the crossing out of 1.x is version 2's `migrate`, so a copy
offered a later major is still told to cross to 2 first rather than told nothing — which is what a rule
recognising only major 2 would have done, exactly when the gap was widest.

A development snapshot of version 2 is announced too, and named as one — "not the 2.0.0 release and not a
version to move a project you care about onto". A snapshot only ever reaches this line where somebody
asked for snapshots, under `--pre` or because this copy is one, so staying quiet there would be quiet for
exactly the people watching version 2 arrive.

It is said on `--check` and not on a plain upgrade: upgrading the tool does not migrate a project, and a
notice on every upgrade would be telling people about work they have not asked to do. Checking installs
nothing and changes no project. Nothing on the 1.x line is deprecated by this; `slipwai upgrade` goes on
keeping you on the newest 1.5.x until you choose to cross.

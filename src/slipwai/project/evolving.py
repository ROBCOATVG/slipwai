"""The generated `docs/evolving-the-project.md`: what the project owns, and how a newer factory reaches it.

Split from `docs.py` when that module reached its budget, and a page of its own because it states the one
relationship a generated project has with this factory afterwards: ownership of every file, and `replay`
as the way later versions are offered rather than applied.
"""
from __future__ import annotations


def evolving_page() -> str:
    return """# Evolving this project

This repository owns every file the factory scaffolded, and the factory never writes into it uninvited.
Rename, move, replace, or delete any file as the product evolves. Add deployables under `apps/` and shared
modules under `packages/`; keep `make verify` as the repository-wide local and CI contract. Backend
language, frontend framework, and persistence style are deployable-scoped decisions, not repository-wide
assumptions. No source checkout or remote is required.

## Taking a newer factory's changes

`project.json` records the answers this repository was generated from and, under `generator`, which factory
version did it (`generatedWith`) and which last wrote a file here (`updatedWith`); the factory's own
`CHANGELOG.md` read against those two says what later versions bring. To take them, run the newer factory
from this directory, on `main` and on a clean tree — never on a `slice/<id>` branch, whose gate refuses the
host's files a migration rewrites:

```sh
slipwai migrate                  # one merge commit; `git reset --hard ORIG_HEAD` undoes it
```

Then `/catch-up`, in an agent session, for what the merge could not do.

A file only the factory changed is taken, a file only this repository changed is kept, and a file both
changed conflicts where the same lines moved — `migrate` stops there with the merge in progress and names
each file, and this repository decides: resolve and `git commit`, or `git merge --abort`. Skills, commands,
gate scripts, CI and the Makefile mostly come through clean; the walking skeleton under `apps/` conflicts
where both sides built on it, and should. Whatever `./init` pruned stays pruned. Elected extension guidance
and the projections `./init` made into your agent harness are re-derived for you, in a commit of this
repository's own, because the factory has never written those project-local copies and no merge can move them.

A migration can bring a gate that did not exist when the code it now judges was written, and a rule that
contradicts a decision this repository already made on purpose; neither is a mistake by anyone, and neither
is something the factory can fix from outside. So `migrate` writes what each version crossed asks of a
repository that already existed — the note its author wrote in the commit that made the change — into
`.slipwai/catch-up.md`, git-ignored and disposable — whether the merge committed or stopped at conflicts,
and saying why when the versions crossed cannot be told, rather than leaving no file. `/catch-up` reads it,
runs `make verify`, and works each failure back to the rule that caused it. One command to run, and the
rest is the ordinary loop.

`slipwai replay` writes the same output beside this repository instead of merging it, to look at first. The
factory's `docs/upgrading.md` has the full recipe.
"""

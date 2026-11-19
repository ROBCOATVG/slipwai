MINOR

**A project's copy of an extension holds what runs or is read there, and no longer the package's repository.**
Electing an extension copied every file of its package into `scripts/extensions/<key>/`: its `.github/`
workflows, its `tests/`, its `CHANGELOG.md` and `changelog.d/`, its `.gitignore`. Nothing in a project runs
any of them, and an agent reading the tree took them for the project's own. Those paths at a package's root
now stay in the package, for every extension, with no line in any manifest, and a package can name more of
its own under `withhold` in `extension.json`. A script the manifest declares at a hook or a guard is always
given, with every module of the package it imports; so are `README.md`, a licence and a notice. What a
release packs, and its checksum, are unchanged. `slipwai extension check <dir>` says what a project is
given, and conformance runs the entry point against exactly that.

**Catch-up:** `slipwai migrate` — the merge removes each of those files this project left as it was given;
one somebody changed here is kept as it is, without a conflict, and `.slipwai/run/catch-up.md` names it
under *Extension files a project is no longer given, and this one still has*: `git rm` it, or keep it on
purpose. An extension author has nothing to do unless a hook opens a file under `tests/`, `.github/` or
`changelog.d/` as data rather than importing it: move that file, then `slipwai conformance --extension <dir>`.

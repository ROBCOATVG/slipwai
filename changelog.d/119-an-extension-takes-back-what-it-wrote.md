MINOR

**An extension can be un-elected, and can take back what it wrote outside its own directory.** An extension
may write a file elsewhere in a project — `codegraph` writes `scripts/codegraph` — and nothing recorded that
it had, there was no moment at which it could remove it, and no way to un-elect an extension at all. Three
things are new. An `extension.json` may declare `writes`, the paths it writes outside
`scripts/extensions/<key>/`, and an election records them. There is an eleventh hook point, `remove`, fired
for one extension as it is un-elected. And `python3 scripts/extensions/hooks.py --remove <key>` un-elects:
it fires that hook, names every recorded path still in the project, and takes the extension out of
`.slipwai/hooks.json`, `.slipwai/extensions.json` and `AGENTS.md`. It removes no file itself, and a hook
that crashes is reported and does not stop it. `slipwai extension remove <key>`, run in a project that
elected the extension, does that first; anywhere else it prints the line to run in each project.

**Catch-up:** `slipwai migrate`, which brings a project the runner that can un-elect; nothing else for a
project that keeps its extensions. A guard an un-elected extension was agreed to stays in
`.slipwai/guards.json` until a person withdraws it. An extension author who writes outside the package's own
directory: declare each such path under `writes`, and a `remove` hook that takes back what is wholly the
extension's — a package that declares either needs this version of slipwai or newer to load.

MINOR

**An adoption puts the method under `adopt/` by default, not `delivery/`.** The adoption tab's "Where the
method's files go" and `slipwai adopt --delivery` both default to `adopt`. A repository adopted before keeps
the directory its `project.json` records; `--delivery delivery` still puts a new one where it used to go.

PATCH

**An extension's files are listed in the same order on every platform.** The list of what an extension
package gives a project promised a stable order and sorted paths as paths, which Windows compares without
case: `README.md` came after `bin/` there and before it on Linux and macOS. It is now sorted on the path as
a `/`-separated string, which reads the same everywhere. Nothing a project is given changes — the same
files, written to the same places.

**Catch-up:** nothing; only the order a list is read in moved, and no file's contents or place.

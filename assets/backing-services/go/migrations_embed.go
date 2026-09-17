// Package migrations carries the event-store migrations into the binary that applies them.
//
// They are embedded rather than read from disk because the image `cmd/migrate` ships in is built
// by ko, and ko ships a compiled Go binary and nothing else — no working directory, no .sql files
// beside it. A disk read resolves on a developer's machine, where `make migrate` runs from the
// service directory and `migrations/` is right there, and matches nothing at all inside the
// container — including when the repository *does* have .sql files, which is how a deploy once
// reported success against an empty database.
//
// Embedding closes that gap by construction: whatever .sql files the commit has are in the binary.
// An empty set is still legitimate (Minimum CD's first commit may ship before any schema exists),
// so this package also embeds `keep` — a non-SQL placeholder — because `go:embed` refuses a
// pattern that matches no files. `cmd/migrate` only applies `*.sql`.
package migrations

import "embed"

// FS holds every file in this directory. `cmd/migrate` selects `*.sql` from it; `keep` exists only
// so the package compiles when there are not yet any migrations.
//
//go:embed *
var FS embed.FS

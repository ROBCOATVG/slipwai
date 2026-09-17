package main

import (
	"context"
	"path/filepath"
	"runtime"
	"sort"
	"testing"
	"testing/fstest"

	"example.com/delivery-starter/migrations"
)

// The bug this file exists for: the migrate image is built by ko, which ships the binary alone, so
// a command that read its .sql files from the working directory found none even when the repository
// had them — and the deploy, which judges the task by its exit code, called that "migrations
// applied". Embedding is what closes that. An empty *.sql set remains legitimate (Minimum CD may
// ship before any schema exists); the lock is disk↔embed equality, not "empty must fail".

func TestTheBinaryCarriesEveryOnDiskMigration(t *testing.T) {
	found, err := pendingMigrations(migrations.FS)
	if err != nil {
		t.Fatalf("reading the embedded migrations: %v", err)
	}

	// Equality with the directory on disk: a narrowed //go:embed that kept only a subset would
	// ship an incomplete schema behind a green deploy — the same class of failure as reading an
	// empty working directory inside the ko image.
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("could not locate this test file to compare against migrations/ on disk")
	}
	onDisk, err := filepath.Glob(filepath.Join(filepath.Dir(thisFile), "..", "..", "migrations", "*.sql"))
	if err != nil {
		t.Fatalf("listing migrations on disk: %v", err)
	}
	diskNames := make([]string, 0, len(onDisk))
	for _, path := range onDisk {
		diskNames = append(diskNames, filepath.Base(path))
	}
	sort.Strings(diskNames)
	if len(found) != len(diskNames) {
		t.Fatalf("embedded %v does not match disk %v", found, diskNames)
	}
	for i := range diskNames {
		if found[i] != diskNames[i] {
			t.Fatalf("embedded %v does not match disk %v", found, diskNames)
		}
	}
}

func TestMigrationsAreAppliedInLexicalOrder(t *testing.T) {
	files := fstest.MapFS{
		"010_later.sql":  {Data: []byte("SELECT 1")},
		"001_first.sql":  {Data: []byte("SELECT 1")},
		"003_middle.sql": {Data: []byte("SELECT 1")},
		"ignored.txt":    {Data: []byte("not a migration")},
		"002_second.sql": {Data: []byte("SELECT 1")},
	}
	found, err := pendingMigrations(files)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"001_first.sql", "002_second.sql", "003_middle.sql", "010_later.sql"}
	if len(found) != len(want) {
		t.Fatalf("got %v, want %v", found, want)
	}
	for i := range want {
		if found[i] != want[i] {
			t.Fatalf("got %v, want %v", found, want)
		}
	}
}

// Minimum CD's first commit may reach main before any schema exists. Empty must succeed without
// needing a database — otherwise the walking skeleton cannot deploy until somebody invents a
// migration.
func TestAnEmptyMigrationSetIsSuccess(t *testing.T) {
	t.Setenv("DATABASE_URL", "")

	err := run(context.Background(), fstest.MapFS{"keep": {Data: []byte("")}})

	if err != nil {
		t.Fatalf("an empty migration set must succeed (Minimum CD may ship before any schema): %v", err)
	}
}

// Command migrate applies the event-store migrations, in order, exactly once each.
//
//	make migrate
//	cd apps/service && DATABASE_URL=postgres://app:app@localhost:5433/app go run ./cmd/migrate
//
// Deliberately small rather than a migration framework. What a framework buys is branching,
// squashing and generated rollbacks; what this needs is "run these files once, in order, and
// record it". The day that stops being enough, replace this command — the .sql files and the
// ledger table are the part worth keeping.
//
// There are no down migrations. Reversing an event-log schema change is a reviewed operation, and
// a rollback that lives next to its migration is a rollback that eventually runs by accident.
package main

import (
	"context"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"example.com/delivery-starter/migrations"
	"github.com/jackc/pgx/v5"
)

const ledger = `
  CREATE TABLE IF NOT EXISTS schema_migrations (
    name    TEXT        PRIMARY KEY,
    run_on  TIMESTAMPTZ NOT NULL DEFAULT now()
  )
`

func main() {
	// No -dir flag. The migrations are compiled in (see the migrations package), so there is no
	// directory to point at and nothing a caller could usefully override.
	if err := run(context.Background(), migrations.FS); err != nil {
		fmt.Fprintf(os.Stderr, "migrate: %v\n", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, files fs.FS) error {
	pending, err := pendingMigrations(files)
	if err != nil {
		return err
	}
	// Zero *.sql files is legitimate: Minimum CD's first commit may reach main (and the migrate
	// task) before any schema exists. The defect that left databases empty was not "empty set
	// exits 0" — it was "the repository had .sql files and the ko image did not". Embedding
	// closes that; the disk↔embed equality test in main_test.go holds it. An empty set here
	// means there is nothing to apply, not a missing embed of files the repository has.
	if len(pending) == 0 {
		fmt.Println("migrate: no migrations to apply")
		return nil
	}

	url := os.Getenv("DATABASE_URL")
	if url == "" {
		return fmt.Errorf(
			"DATABASE_URL is not set. `make migrate` exports the value from the Makefile; " +
				"outside make, copy it from .env.example")
	}

	connection, err := pgx.Connect(ctx, url)
	if err != nil {
		return fmt.Errorf("connect: %w", err)
	}
	defer connection.Close(ctx)

	if _, err := connection.Exec(ctx, ledger); err != nil {
		return fmt.Errorf("create the migration ledger: %w", err)
	}

	applied, err := appliedNames(ctx, connection)
	if err != nil {
		return err
	}

	for _, path := range pending {
		name := strings.TrimSuffix(filepath.Base(path), ".sql")
		if applied[name] {
			continue
		}
		statements, err := fs.ReadFile(files, path)
		if err != nil {
			return fmt.Errorf("read %s: %w", path, err)
		}
		// One transaction per migration, including its ledger row: a migration that half-applied
		// and still counted as done is the failure mode this exists to prevent. Postgres runs DDL
		// transactionally, so this is a real guarantee rather than a hopeful one.
		transaction, err := connection.Begin(ctx)
		if err != nil {
			return fmt.Errorf("begin %s: %w", name, err)
		}
		if _, err := transaction.Exec(ctx, string(statements)); err != nil {
			_ = transaction.Rollback(ctx)
			return fmt.Errorf("%s failed and was rolled back: %w", name, err)
		}
		_, err = transaction.Exec(ctx, "INSERT INTO schema_migrations (name) VALUES ($1)", name)
		if err != nil {
			_ = transaction.Rollback(ctx)
			return fmt.Errorf("%s failed and was rolled back: %w", name, err)
		}
		if err := transaction.Commit(ctx); err != nil {
			return fmt.Errorf("commit %s: %w", name, err)
		}
		fmt.Printf("migrate: applied %s\n", name)
	}

	fmt.Println("migrate: up to date")
	return nil
}

// pendingMigrations returns every migration in lexical order — which the shipped ones' zero-padded
// numbers and a new one's YYYYMMDDHHMM stamp both keep, every stamp sorting after every number.
// Takes an fs.FS rather than the embedded set directly so a test can hand it a fabricated one,
// including an empty one.
func pendingMigrations(files fs.FS) ([]string, error) {
	paths, err := fs.Glob(files, "*.sql")
	if err != nil {
		return nil, fmt.Errorf("list the embedded migrations: %w", err)
	}
	sort.Strings(paths)
	return paths, nil
}

func appliedNames(ctx context.Context, connection *pgx.Conn) (map[string]bool, error) {
	rows, err := connection.Query(ctx, "SELECT name FROM schema_migrations")
	if err != nil {
		return nil, fmt.Errorf("read the migration ledger: %w", err)
	}
	defer rows.Close()

	applied := map[string]bool{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, fmt.Errorf("read the migration ledger: %w", err)
		}
		applied[name] = true
	}
	return applied, rows.Err()
}

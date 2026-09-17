package eventstoresqlite_test

import (
	"context"
	"database/sql"
	"path/filepath"
	"strings"
	"testing"

	"example.com/delivery-starter/adapters/driven/eventstoresqlite"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/eventstorecontract"
)

// The shared contract, against SQLite. This runs in `make verify` and needs no Docker — an
// embedded database is created by the process that opens it, so there is nothing to start and
// nothing to migrate.
//
// ":memory:" for the contract, because the contract is about behaviour and a fresh database per
// case is what keeps them independent.
func TestSqliteEventStoreSatisfiesThePort(t *testing.T) {
	eventstorecontract.Run(t, func(t *testing.T, tagsOf events.TagsOf) events.Store {
		store, err := eventstoresqlite.OpenTagged(":memory:", tagsOf)
		if err != nil {
			t.Fatalf("open sqlite: %v", err)
		}
		t.Cleanup(func() { store.Close() })
		return store
	})
}

// One id for the whole file: these writes are about durability, and a correlation id that changed
// per event would say they belonged to different business transactions, which they do not.
var correlationID = mustCorrelationID("018f3a2b-6c41-7c9d-9f0e-2a5b7c1d4e83")

// mustCorrelationID panics rather than returning an error: the argument is a literal in this file,
// so a malformed one is a bug here and not a condition a caller could handle — the same reason
// regexp.MustCompile exists.
func mustCorrelationID(raw string) events.CorrelationID {
	id, err := events.NewCorrelationID(raw)
	if err != nil {
		panic(err)
	}
	return id
}

func event(streamID, eventType string) events.DomainEvent {
	return events.DomainEvent{
		Type:          eventType,
		SchemaVersion: 1,
		StreamID:      streamID,
		Payload:       map[string]any{"step": eventType},
		OccurredAt:    "2024-01-01T00:00:00.000000+00:00",
		Actor:         events.Actor{Kind: "test", ID: "durability"},
		CorrelationID: correlationID,
	}
}

// The whole reason to choose SQLite over the in-memory adapter.
func TestKeepsTheLogAcrossACloseAndReopen(t *testing.T) {
	location := filepath.Join(t.TempDir(), "events.sqlite3")

	first, err := eventstoresqlite.Open(location)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	if _, err := first.Append(context.Background(), "order-1", events.NoStream,
		[]events.DomainEvent{event("order-1", "Placed")}); err != nil {
		t.Fatalf("append: %v", err)
	}
	first.Close()

	reopened, err := eventstoresqlite.Open(location)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer reopened.Close()

	recorded, err := reopened.Read(context.Background(), "order-1")
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(recorded) != 1 || recorded[0].Type != "Placed" || recorded[0].Version != 0 {
		t.Fatalf("the log did not survive the reopen: %+v", recorded)
	}

	// A caller that has not noticed the restart is still refused, by the same rule as before it.
	result, err := reopened.Append(context.Background(), "order-1", events.NoStream,
		[]events.DomainEvent{event("order-1", "Raced")})
	if err != nil {
		t.Fatalf("append: %v", err)
	}
	if result != events.VersionConflict(0) {
		t.Fatalf("expected VersionConflict(0), got %+v", result)
	}
}

// The append-only rule lives in the database, not in the adapter. A rule the application
// enforces is a rule the next process to open the file — a migration script, a sqlite3 shell, a
// well-meaning fix in production — will not.
func TestRefusesToRewriteOrEraseWhatHasBeenRecorded(t *testing.T) {
	location := filepath.Join(t.TempDir(), "events.sqlite3")
	store, err := eventstoresqlite.Open(location)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	if _, err := store.Append(context.Background(), "order-1", events.NoStream,
		[]events.DomainEvent{event("order-1", "Placed")}); err != nil {
		t.Fatalf("append: %v", err)
	}
	store.Close()

	db, err := sql.Open("sqlite", location)
	if err != nil {
		t.Fatalf("open raw: %v", err)
	}
	defer db.Close()

	for _, statement := range []string{
		"UPDATE events SET event_type = 'Rewritten'",
		"DELETE FROM events",
	} {
		if _, err := db.Exec(statement); err == nil {
			t.Fatalf("%q was permitted", statement)
		} else if !strings.Contains(err.Error(), "append-only") {
			t.Fatalf("%q failed for the wrong reason: %v", statement, err)
		}
	}

	var remaining string
	if err := db.QueryRow("SELECT event_type FROM events").Scan(&remaining); err != nil {
		t.Fatalf("read back: %v", err)
	}
	if remaining != "Placed" {
		t.Fatalf("the recorded event became %q", remaining)
	}
}

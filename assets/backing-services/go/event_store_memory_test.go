package eventstorememory_test

import (
	"context"
	"testing"

	"example.com/delivery-starter/adapters/driven/eventstorememory"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/eventstorecontract"
)

// The contract, against the fake. This runs in `make verify` and needs no Docker, which is the
// whole reason the fake exists. `make test-integration` runs the same contract against Postgres.
func TestInMemoryEventStoreSatisfiesThePort(t *testing.T) {
	eventstorecontract.Run(t, func(_ *testing.T, tagsOf events.TagsOf) events.Store {
		return eventstorememory.NewTagged(tagsOf, eventstorememory.NewDatabase())
	})
}

// Reindexing a log the index is behind on, from a position part-way through it.
//
// `fromPosition` is inclusive: an event *at* that position is one the index does not have yet.
// That is what makes a long adoption run resumable — it stops, and the next run is handed the
// position it stopped at, rather than starting over or skipping an event.
//
// The shared contract cannot reach this. It needs a log whose events were written under one
// tagging function and a store that reads them under another, and two stores over one Database is
// how this adapter arranges that. It is also exactly what an already-running project does: the log
// is not touched, only the index over it.
func TestReindexesTagsFromTheGivenPositionInclusive(t *testing.T) {
	database := eventstorememory.NewDatabase()
	before := eventstorememory.NewTagged(eventstorecontract.NoTags, database)
	stream := "course-adoption"
	if _, err := before.Append(context.Background(), stream, events.NoStream, []events.DomainEvent{
		enrolment(stream, "one"), enrolment(stream, "two"), enrolment(stream, "three"),
	}); err != nil {
		t.Fatalf("append: %v", err)
	}
	log, err := before.Read(context.Background(), stream)
	if err != nil {
		t.Fatalf("read: %v", err)
	}

	after := eventstorememory.NewTagged(eventstorecontract.PayloadTags, database)
	indexed, err := after.ReindexTags(context.Background(), log[1].GlobalPosition)
	if err != nil {
		t.Fatalf("reindex: %v", err)
	}

	if indexed != 2 {
		t.Fatalf("expected the second event and everything after it indexed, got %d", indexed)
	}
	if found := findByTag(t, after, "course:one"); len(found) != 0 {
		t.Fatalf("expected the events before the position left alone, got %d", len(found))
	}
	// The position itself, which is the difference between resuming and skipping an event.
	if found := findByTag(t, after, "course:two"); len(found) != 1 {
		t.Fatalf("expected the event at the position indexed, got %d", len(found))
	}
	if found := findByTag(t, after, "course:three"); len(found) != 1 {
		t.Fatalf("expected the events after the position indexed, got %d", len(found))
	}
}

func enrolment(stream string, course string) events.DomainEvent {
	correlationID, err := events.NewCorrelationID("018f3a2b-6c41-7c9d-9f0e-2a5b7c1d4e84")
	if err != nil {
		panic(err)
	}
	return events.DomainEvent{
		Type:          "Enrolled",
		SchemaVersion: 1,
		StreamID:      stream,
		Payload:       map[string]any{"courseId": course},
		OccurredAt:    "2024-01-01T00:00:00.000000+00:00",
		Actor:         events.Actor{Kind: "test", ID: "adoption"},
		CorrelationID: correlationID,
	}
}

func findByTag(t *testing.T, store events.Store, tag string) []events.CommittedEvent {
	t.Helper()
	found, err := store.ReadTagged(
		context.Background(),
		events.TagQuery{Filters: []events.TagFilter{{Tags: []string{tag}}}},
		0,
		0,
	)
	if err != nil {
		t.Fatalf("read tagged: %v", err)
	}
	return found.Events
}

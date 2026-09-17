// Package eventstorecontract holds one contract, run against every event-store adapter.
//
// The infrastructure-free adapters run it in `make test`; Postgres runs it in
// `make test-integration`. Two adapters that pass different tests are two different ports
// wearing one name, and the day they diverge is the day a slice that worked on the fake stops
// working in production.
//
// Nothing here truncates or deletes: the log is append-only, and a real store enforces that with
// a trigger, so a shared table cannot be cleaned between tests. Every test therefore works in
// freshly named streams and asserts only about those. That is not a workaround — it is what
// testing against a real append-only log actually looks like.
package eventstorecontract

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"testing"

	"example.com/delivery-starter/application/ports/events"
)

// NewStore builds the adapter under test, indexing each event by what tagsOf returns for it.
// Called once per case, so each starts clean where the adapter can be clean and works in fresh
// streams where it cannot.
type NewStore func(t *testing.T, tagsOf events.TagsOf) events.Store

// PayloadTags is a tagging function of the shape a real project writes: the stream, plus the
// identifying attributes of the payload.
//
// Tags are derived from the event and nothing else, which is what makes the index rebuildable — so
// this function is called on the way in *and* during a reindex, and the contract below proves the
// two agree.
func PayloadTags(event events.DomainEvent) []string {
	tags := []string{events.StreamTag(event.StreamID)}
	for _, attribute := range []struct{ key, kind string }{
		{"courseId", "course"},
		{"studentId", "student"},
	} {
		if value, ok := event.Payload[attribute.key].(string); ok {
			tags = append(tags, attribute.kind+":"+value)
		}
	}
	return tags
}

// NoTags is what a project that has not adopted tags has: a log with no index over it. Every event
// already in a running project's log was written by a store that behaved exactly like this, which
// is why it is worth a named function rather than a comment.
func NoTags(events.DomainEvent) []string { return nil }

// Run holds an adapter to the port's contract.
func Run(t *testing.T, newStore NewStore) {
	t.Helper()

	// The store every case below uses unless it wants tags: indexed by stream, which is what the
	// port does when a project has not said otherwise.
	plainStore := func(t *testing.T) events.Store { return newStore(t, events.DefaultTagsOf) }
	// A store whose events are findable by their payload's ids as well as their stream — which is
	// the only reason a Dynamic Consistency Boundary can be drawn at all.
	taggedStore := func(t *testing.T) events.Store { return newStore(t, PayloadTags) }

	run := randomID(t)
	correlationID, err := events.NewCorrelationID(randomUUID(t))
	if err != nil {
		t.Fatalf("correlation id: %v", err)
	}
	counter := 0
	newStream := func() string {
		counter++
		return fmt.Sprintf("contract-%s-%d", run, counter)
	}
	// The value a case's tags are built from. Unique per case, not per run, because Postgres runs
	// this suite against a database it shares with every other case and every previous run — and a
	// tag is not scoped to a stream, so two cases tagging by the same id would find each other's
	// events. The in-memory and SQLite adapters get a fresh database per case and would never have
	// shown it.
	newSubject := func() string {
		counter++
		return fmt.Sprintf("%s-%d", run, counter)
	}
	event := func(streamID, eventType string, payload map[string]any) events.DomainEvent {
		if payload == nil {
			payload = map[string]any{}
		}
		return events.DomainEvent{
			Type:          eventType,
			SchemaVersion: 1,
			StreamID:      streamID,
			Payload:       payload,
			OccurredAt:    "2024-01-01T00:00:00.000000+00:00",
			Actor:         events.Actor{Kind: "test", ID: run},
			CorrelationID: correlationID,
		}
	}

	t.Run("reads an unknown stream as empty rather than failing", func(t *testing.T) {
		store := plainStore(t)
		stream, err := store.Read(context.Background(), newStream())
		if err != nil {
			t.Fatalf("read: %v", err)
		}
		if len(stream) != 0 {
			t.Fatalf("expected an empty stream, got %d events", len(stream))
		}
	})

	t.Run("appends to a stream that does not exist yet", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()

		result, err := store.Append(context.Background(), stream, events.NoStream,
			[]events.DomainEvent{event(stream, "Started", nil), event(stream, "Continued", nil)})
		if err != nil {
			t.Fatalf("append: %v", err)
		}
		if result != events.Appended(1) {
			t.Fatalf("expected Appended(1), got %+v", result)
		}
	})

	t.Run("returns the stream in version order with what only the store knows", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Started", map[string]any{"step": float64(1)}))
		mustAppend(t, store, stream, 0,
			event(stream, "Continued", map[string]any{"step": float64(2)}))

		recorded := mustRead(t, store, stream)

		if len(recorded) != 2 {
			t.Fatalf("expected 2 events, got %d", len(recorded))
		}
		if recorded[0].Type != "Started" || recorded[0].Version != 0 {
			t.Fatalf("first event is %+v", recorded[0])
		}
		if recorded[1].Type != "Continued" || recorded[1].Version != 1 {
			t.Fatalf("second event is %+v", recorded[1])
		}
		if recorded[1].GlobalPosition <= recorded[0].GlobalPosition {
			t.Fatalf("global position did not advance: %+v", recorded)
		}
		if recorded[0].Payload["step"] != float64(1) {
			t.Fatalf("payload did not survive the round trip: %+v", recorded[0].Payload)
		}
		if recorded[0].Actor != (events.Actor{Kind: "test", ID: run}) {
			t.Fatalf("actor did not survive the round trip: %+v", recorded[0].Actor)
		}
		if recorded[0].RecordedAt == "" {
			t.Fatal("the store recorded no storage time")
		}
	})

	// Every adapter stores these ids the way its database can and hands back the same UUIDs.
	// Postgres has a uuid column, SQLite has text, the in-memory store has neither. The difference
	// stops at the adapter, and it is provable here rather than by reading three implementations.
	t.Run("round-trips the correlation and causation ids as UUIDs", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		cause, err := events.NewCausationID(randomUUID(t))
		if err != nil {
			t.Fatalf("causation id: %v", err)
		}
		caused := event(stream, "Caused", nil)
		caused.CausationID = cause

		if _, err := store.Append(context.Background(), stream, events.NoStream,
			[]events.DomainEvent{event(stream, "Started", nil), caused}); err != nil {
			t.Fatalf("append: %v", err)
		}

		recorded, err := store.Read(context.Background(), stream)
		if err != nil {
			t.Fatalf("read: %v", err)
		}
		if recorded[0].CorrelationID != correlationID {
			t.Fatalf("expected correlation id %q, got %q", correlationID, recorded[0].CorrelationID)
		}
		// The first event of a transaction has no cause, and the store does not invent one.
		if recorded[0].CausationID != "" {
			t.Fatalf("expected no causation id, got %q", recorded[0].CausationID)
		}
		if recorded[1].CausationID != cause {
			t.Fatalf("expected causation id %q, got %q", cause, recorded[1].CausationID)
		}
	})

	t.Run("reports a stale expected version as a value, not an error", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		result, err := store.Append(context.Background(), stream, events.NoStream,
			[]events.DomainEvent{event(stream, "Raced", nil)})
		if err != nil {
			t.Fatalf("a version conflict must not be an error: %v", err)
		}
		if result != events.VersionConflict(0) {
			t.Fatalf("expected VersionConflict(0), got %+v", result)
		}
	})

	t.Run("writes nothing when the expected version is stale", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		if _, err := store.Append(context.Background(), stream, events.NoStream,
			[]events.DomainEvent{
				event(stream, "Rejected", nil), event(stream, "AlsoRejected", nil),
			}); err != nil {
			t.Fatalf("append: %v", err)
		}

		if types := typesOf(mustRead(t, store, stream)); len(types) != 1 || types[0] != "Started" {
			t.Fatalf("a rejected append wrote something: %v", types)
		}
	})

	t.Run("continues a stream from the version it reports", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))
		history := mustRead(t, store, stream)

		if events.CurrentVersion(history) != 0 {
			t.Fatalf("current version is %d", events.CurrentVersion(history))
		}
		result, err := store.Append(context.Background(), stream, events.CurrentVersion(history),
			[]events.DomainEvent{event(stream, "Continued", nil)})
		if err != nil {
			t.Fatalf("append: %v", err)
		}
		if result != events.Appended(1) {
			t.Fatalf("expected Appended(1), got %+v", result)
		}
	})

	t.Run("treats an empty append as a no-op at the expected version", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		result, err := store.Append(context.Background(), stream, 0, nil)
		if err != nil {
			t.Fatalf("append: %v", err)
		}
		if result != events.Appended(0) {
			t.Fatalf("expected Appended(0), got %+v", result)
		}
		if len(mustRead(t, store, stream)) != 1 {
			t.Fatal("an empty append wrote something")
		}
	})

	t.Run("keeps streams apart", func(t *testing.T) {
		store := plainStore(t)
		one, other := newStream(), newStream()
		mustAppend(t, store, one, events.NoStream, event(one, "Mine", nil))
		mustAppend(t, store, other, events.NoStream, event(other, "Theirs", nil))

		if types := typesOf(mustRead(t, store, one)); len(types) != 1 || types[0] != "Mine" {
			t.Fatalf("stream one holds %v", types)
		}
		if types := typesOf(mustRead(t, store, other)); len(types) != 1 || types[0] != "Theirs" {
			t.Fatalf("stream two holds %v", types)
		}
	})

	t.Run("replays across all streams in global-position order", func(t *testing.T) {
		store := plainStore(t)
		one, other := newStream(), newStream()
		mustAppend(t, store, one, events.NoStream, event(one, "First", nil))
		mustAppend(t, store, other, events.NoStream, event(other, "Second", nil))
		mustAppend(t, store, one, 0, event(one, "Third", nil))

		replayed := replay(t, store, 0, func(e events.CommittedEvent) bool {
			return e.StreamID == one || e.StreamID == other
		})

		types := typesOf(replayed)
		if len(types) != 3 || types[0] != "First" || types[1] != "Second" || types[2] != "Third" {
			t.Fatalf("replay produced %v", types)
		}
		for i := 1; i < len(replayed); i++ {
			if replayed[i].GlobalPosition <= replayed[i-1].GlobalPosition {
				t.Fatalf("replay is not in global-position order: %v", replayed)
			}
		}
	})

	t.Run("replays only from the requested position onward", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		if _, err := store.Append(context.Background(), stream, events.NoStream,
			[]events.DomainEvent{event(stream, "First", nil), event(stream, "Second", nil)},
		); err != nil {
			t.Fatalf("append: %v", err)
		}
		recorded := mustRead(t, store, stream)

		replayed := replay(t, store, recorded[1].GlobalPosition, func(e events.CommittedEvent) bool {
			return e.StreamID == stream
		})

		if types := typesOf(replayed); len(types) != 1 || types[0] != "Second" {
			t.Fatalf("replay from a position produced %v", types)
		}
	})

	// ── The tag index, and the boundary drawn out of it ──────────────────────────────────────────
	//
	// Everything below is the Dynamic Consistency Boundary, and it runs against every adapter for
	// the same reason the rest of this file does: a fake that answers a tag query differently from
	// Postgres is a fake that proves nothing about production. The SQL adapters translate
	// TagFilter.Matches into SQL, and these are the cases that hold the translation to the
	// definition.

	t.Run("indexes every event by its own stream without being asked", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		found := mustReadTagged(t, store, tagged(events.StreamTag(stream)), 0)

		if got := typesOf(found.Events); len(got) != 1 || got[0] != "Started" {
			t.Fatalf("expected the stream's own event, got %v", got)
		}
	})

	t.Run("reports the store head with what it read", func(t *testing.T) {
		store := taggedStore(t)
		stream := newStream()
		query := tagged(events.StreamTag(stream))
		empty := mustReadTagged(t, store, query, 0)
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		after := mustReadTagged(t, store, query, 0)

		if after.Head <= empty.Head {
			t.Fatalf("expected the head to move past %d, got %d", empty.Head, after.Head)
		}
		last := after.Events[len(after.Events)-1]
		if last.GlobalPosition != after.Head {
			t.Fatalf("expected the last event at head %d, got %d", after.Head, last.GlobalPosition)
		}
	})

	// A filter is a conjunction. An "any of these tags" filter would be a much weaker guard than
	// the caller wrote, and the difference is invisible until it lets a write through.
	t.Run("matches an event only when it carries every tag in a filter", func(t *testing.T) {
		store := taggedStore(t)
		stream, subject := newStream(), newSubject()
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Subscribed", map[string]any{"courseId": subject, "studentId": subject}))

		both := mustReadTagged(t, store, tagged("course:"+subject, "student:"+subject), 0)
		oneWrong := mustReadTagged(t, store,
			tagged("course:"+subject, "student:"+subject+"-nobody"), 0)

		if len(both.Events) != 1 {
			t.Fatalf("expected the event to match both of its tags, got %d", len(both.Events))
		}
		if len(oneWrong.Events) != 0 {
			t.Fatalf("expected no match when one tag is wrong, got %d", len(oneWrong.Events))
		}
	})

	// The query is a disjunction of conjunctions, because the constraint that motivates any of
	// this spans entities: a course's events *and* a student's events, which is two filters and
	// cannot be one.
	t.Run("matches any filter in the query", func(t *testing.T) {
		store := taggedStore(t)
		courseStream, studentStream, subject := newStream(), newStream(), newSubject()
		mustAppend(t, store, courseStream, events.NoStream,
			event(courseStream, "CourseCapacitySet", map[string]any{"courseId": subject}))
		mustAppend(t, store, studentStream, events.NoStream,
			event(studentStream, "StudentSubscribed", map[string]any{"studentId": subject}))

		found := mustReadTagged(t, store, events.TagQuery{Filters: []events.TagFilter{
			{Tags: []string{"course:" + subject}},
			{Tags: []string{"student:" + subject}},
		}}, 0)

		got := typesOf(found.Events)
		if len(got) != 2 || got[0] != "CourseCapacitySet" || got[1] != "StudentSubscribed" {
			t.Fatalf("expected both entities' events in position order, got %v", got)
		}
	})

	t.Run("narrows a filter by event type", func(t *testing.T) {
		store := taggedStore(t)
		stream, subject := newStream(), newSubject()
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Subscribed", map[string]any{"courseId": subject}),
			event(stream, "Unsubscribed", map[string]any{"courseId": subject}))

		found := mustReadTagged(t, store, events.TagQuery{Filters: []events.TagFilter{
			{Tags: []string{"course:" + subject}, Types: []string{"Unsubscribed"}},
		}}, 0)

		if got := typesOf(found.Events); len(got) != 1 || got[0] != "Unsubscribed" {
			t.Fatalf("expected only the type the filter named, got %v", got)
		}
	})

	// The dangerous default, refused explicitly. A condition that matched everything would refuse
	// every concurrent append in the system, and a read that matched everything would quietly
	// become a full replay.
	t.Run("matches nothing for an empty query rather than everything", func(t *testing.T) {
		store := taggedStore(t)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		for name, query := range map[string]events.TagQuery{
			"no filters":   {},
			"empty filter": {Filters: []events.TagFilter{{}}},
		} {
			if found := mustReadTagged(t, store, query, 0); len(found.Events) != 0 {
				t.Fatalf("%s matched %d events", name, len(found.Events))
			}
		}
	})

	t.Run("appends conditionally when nothing matching arrived since the read", func(t *testing.T) {
		store := taggedStore(t)
		stream, subject := newStream(), newSubject()
		query := tagged("course:" + subject)
		decidedAt := mustReadTagged(t, store, query, 0).Head

		result := mustAppendIf(t, store, events.Condition{Query: query, After: decidedAt},
			event(stream, "Subscribed", map[string]any{"courseId": subject}))

		if result.Outcome != events.OutcomeRecorded {
			t.Fatalf("expected the append to hold, got %+v", result)
		}
		if got := typesOf(mustRead(t, store, stream)); len(got) != 1 || got[0] != "Subscribed" {
			t.Fatalf("expected the event in its own stream, got %v", got)
		}
	})

	// The guard expectedVersion cannot express: the constraint spans two entities, and what
	// invalidates the decision is an event in a stream the decision never named.
	t.Run("refuses a conditional append when a matching event arrived since", func(t *testing.T) {
		store := taggedStore(t)
		stream, other, subject := newStream(), newStream(), newSubject()
		query := tagged("course:" + subject)
		decidedAt := mustReadTagged(t, store, query, 0).Head
		mustAppend(t, store, other, events.NoStream,
			event(other, "Subscribed", map[string]any{"courseId": subject}))

		result := mustAppendIf(t, store, events.Condition{Query: query, After: decidedAt},
			event(stream, "Subscribed", map[string]any{"courseId": subject}))

		if result.Outcome != events.OutcomeConditionConflict {
			t.Fatalf("expected a condition conflict, got %+v", result)
		}
		if result.Head < decidedAt {
			t.Fatalf("expected the head at or past %d, got %d", decidedAt, result.Head)
		}
		if got := mustRead(t, store, stream); len(got) != 0 {
			t.Fatalf("expected nothing written, got %v", typesOf(got))
		}
	})

	// The compatibility that makes this additive rather than a fork. A conditional append still
	// lands at the next version of the stream it names, so every slice written against Read,
	// Append and folds goes on working unchanged.
	t.Run("leaves a conditional append readable as part of its stream", func(t *testing.T) {
		store := taggedStore(t)
		stream, subject := newStream(), newSubject()
		query := tagged("course:" + subject)
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Opened", map[string]any{"courseId": subject}))
		mustAppendIf(t, store,
			events.Condition{Query: query, After: mustReadTagged(t, store, query, 0).Head},
			event(stream, "Subscribed", map[string]any{"courseId": subject}))

		stored := mustRead(t, store, stream)

		if len(stored) != 2 || stored[0].Version != 0 || stored[1].Version != 1 {
			t.Fatalf("expected gapless versions 0 and 1, got %+v", stored)
		}
		result, err := store.Append(context.Background(), stream, events.CurrentVersion(stored), nil)
		if err != nil || result != events.Appended(1) {
			t.Fatalf("expected the stream to continue from version 1, got %+v (%v)", result, err)
		}
	})

	// What every project generated before tags existed is, and what it stays until it says
	// otherwise: the log, unchanged, with an index over nothing.
	t.Run("behaves exactly as it did before when it indexes nothing", func(t *testing.T) {
		store := newStore(t, NoTags)
		stream := newStream()

		result := mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		if result != events.Appended(0) {
			t.Fatalf("expected Appended(0), got %+v", result)
		}
		if got := typesOf(mustRead(t, store, stream)); len(got) != 1 {
			t.Fatalf("expected the event in its stream, got %v", got)
		}
		if found := mustReadTagged(t, store, tagged(events.StreamTag(stream)), 0); len(found.Events) != 0 {
			t.Fatalf("expected an index over nothing, got %d events", len(found.Events))
		}
	})

	// The adoption path, as a test rather than as a paragraph.
	//
	// A project already in production applies the migration, which creates an empty index, and
	// runs this. Nothing about the log changes — which is the only reason it is possible at all,
	// since the log refuses to be rewritten.
	//
	// Retag rebuilds the whole index rather than one stream's share of it. Against a shared
	// database that is safe here because every tagging function in this suite returns the stream
	// tag plus more, so a rebuild under one of them satisfies every other case's assumptions.
	t.Run("indexes a log it did not index when the events were written", func(t *testing.T) {
		store := newStore(t, NoTags)
		stream, subject := newStream(), newSubject()
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Enrolled", map[string]any{"courseId": subject}),
			event(stream, "Graduated", map[string]any{"courseId": subject}))
		query := tagged("course:" + subject)
		if found := mustReadTagged(t, store, query, 0); len(found.Events) != 0 {
			t.Fatalf("expected no index yet, got %d events", len(found.Events))
		}

		indexed, err := store.Retag(context.Background(), PayloadTags)
		if err != nil {
			t.Fatalf("retag: %v", err)
		}

		if indexed < 2 {
			t.Fatalf("expected at least the two events indexed, got %d", indexed)
		}
		if got := typesOf(mustReadTagged(t, store, query, 0).Events); len(got) != 2 {
			t.Fatalf("expected both events findable by tag, got %v", got)
		}
		// Idempotent: a second run indexes nothing, so a reindex that died halfway is finished by
		// running it again rather than started over.
		again, err := store.ReindexTags(context.Background(), 0)
		if err != nil || again != 0 {
			t.Fatalf("expected a second reindex to do nothing, got %d (%v)", again, err)
		}
	})

	// What "indexed" means, which the adapters have to agree on or the number the adoption run
	// reports is a different number in every store.
	//
	// An event this project's tagging function returns nothing for is never findable by tag, so a
	// reindex that counted it would report work it did not do and would never settle at zero. Both
	// halves matter: the in-memory store must not record an empty index entry (which would make the
	// event look indexed to a later run under a real tagging function), and the SQL stores must not
	// count a row they wrote no tags for.
	t.Run("counts only the events a reindex made findable by tag", func(t *testing.T) {
		store := newStore(t, NoTags)
		stream := newStream()
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Enrolled", map[string]any{"courseId": newSubject()}),
			event(stream, "Graduated", map[string]any{"courseId": newSubject()}))

		indexed, err := store.ReindexTags(context.Background(), 0)
		if err != nil {
			t.Fatalf("reindex: %v", err)
		}
		if indexed != 0 {
			t.Fatalf("expected nothing made findable by a tagging function that tags nothing, got %d", indexed)
		}
	})

	// The reason Head is a method of its own, and what stops a decision from being made against two
	// different moments.
	//
	// A command that needs two queries — a course's capacity and a student's own subscriptions —
	// reads twice. If each read hands back its own head and the caller guards with the second one,
	// an event matching the *first* query could have arrived between the two reads, before that
	// head, and the conditional append would never look for it: the guard says "nothing since here"
	// about a position the facts do not cover.
	//
	// Pinning the boundary first and passing it as until removes the gap. Both reads see the same
	// log, the head handed back is the boundary rather than whatever has happened since, and a
	// Condition built from it covers exactly the facts it was decided on.
	t.Run("reads as of a boundary and nothing after it", func(t *testing.T) {
		store := taggedStore(t)
		stream, subject := newStream(), newSubject()
		query := tagged("course:" + subject)
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Enrolled", map[string]any{"courseId": subject}))

		boundary := mustHead(t, store)
		// Somebody else's event, after the boundary this decision was drawn at.
		mustAppend(t, store, stream, 0,
			event(stream, "Graduated", map[string]any{"courseId": subject}))

		asOf := mustReadTaggedUntil(t, store, query, 0, boundary)
		if got := typesOf(asOf.Events); len(got) != 1 || got[0] != "Enrolled" {
			t.Fatalf("expected only the events up to the boundary, got %v", got)
		}
		if asOf.Head != boundary {
			t.Fatalf("expected the facts to be as of %d, got %d", boundary, asOf.Head)
		}

		// Unbounded, the same query sees both — the ceiling is the caller's decision, not a filter
		// the store applies on its own.
		current := mustReadTagged(t, store, query, 0)
		if got := typesOf(current.Events); len(got) != 2 {
			t.Fatalf("expected both events, got %v", got)
		}
		if current.Head < boundary {
			t.Fatalf("expected a head at or past the boundary, got %d", current.Head)
		}
	})

	// The one failure that would make the index worse than not having it: an event visible to
	// Read whose tags are not yet visible to ReadTagged would let the next conditional append
	// miss the very event that should have refused it.
	t.Run("makes an append and its tags arrive together or not at all", func(t *testing.T) {
		store := taggedStore(t)
		stream, subject := newStream(), newSubject()
		mustAppend(t, store, stream, events.NoStream,
			event(stream, "Subscribed", map[string]any{"courseId": subject}))

		found := mustReadTagged(t, store, tagged("course:"+subject), 0)
		if len(mustRead(t, store, stream)) != len(found.Events) {
			t.Fatal("the log and its index disagree about what was appended")
		}
	})

	// What an inline read model and an async checkpoint are both built on: a write of somebody
	// else's that fails takes the append with it.
	t.Run("leaves the log as it was when a unit of work fails", func(t *testing.T) {
		store := plainStore(t)
		stream := newStream()
		viewFailed := errors.New("the view write failed")

		err := store.InUnitOfWork(context.Background(), func(inside context.Context) error {
			batch := []events.DomainEvent{event(stream, "Started", nil)}
			if _, err := store.Append(inside, stream, events.NoStream, batch); err != nil {
				return err
			}
			return viewFailed
		})

		if !errors.Is(err, viewFailed) {
			t.Fatalf("expected the view's failure to reach the caller, got %v", err)
		}
		if got := mustRead(t, store, stream); len(got) != 0 {
			t.Fatalf("expected nothing committed, got %v", typesOf(got))
		}
	})

	t.Run("commits everything in a unit of work that completes, once", func(t *testing.T) {
		store := plainStore(t)
		one, other := newStream(), newStream()

		err := store.InUnitOfWork(context.Background(), func(inside context.Context) error {
			mine := []events.DomainEvent{event(one, "Mine", nil)}
			if _, err := store.Append(inside, one, events.NoStream, mine); err != nil {
				return err
			}
			theirs := []events.DomainEvent{event(other, "Theirs", nil)}
			_, err := store.Append(inside, other, events.NoStream, theirs)
			return err
		})
		if err != nil {
			t.Fatalf("unit of work: %v", err)
		}

		if got := typesOf(mustRead(t, store, one)); len(got) != 1 || got[0] != "Mine" {
			t.Fatalf("expected the first stream committed, got %v", got)
		}
		if got := typesOf(mustRead(t, store, other)); len(got) != 1 || got[0] != "Theirs" {
			t.Fatalf("expected the second stream committed, got %v", got)
		}
	})

	// A conflict is a value, so the caller's transaction survives it and goes on to commit what
	// else it was doing. Without a savepoint per nested block, a refused append would either
	// poison the outer transaction or leave its own half-written events inside it.
	t.Run("writes nothing and ends nothing when a nested append is refused", func(t *testing.T) {
		store := plainStore(t)
		stream, other := newStream(), newStream()
		mustAppend(t, store, stream, events.NoStream, event(stream, "Started", nil))

		var refused events.AppendResult
		err := store.InUnitOfWork(context.Background(), func(inside context.Context) error {
			rejected := []events.DomainEvent{
				event(stream, "Rejected", nil), event(stream, "AlsoRejected", nil),
			}
			var err error
			refused, err = store.Append(inside, stream, events.NoStream, rejected)
			if err != nil {
				return err
			}
			unaffected := []events.DomainEvent{event(other, "Unaffected", nil)}
			_, err = store.Append(inside, other, events.NoStream, unaffected)
			return err
		})
		if err != nil {
			t.Fatalf("unit of work: %v", err)
		}

		if refused != events.VersionConflict(0) {
			t.Fatalf("expected VersionConflict(0), got %+v", refused)
		}
		if got := typesOf(mustRead(t, store, stream)); len(got) != 1 || got[0] != "Started" {
			t.Fatalf("expected the refused events not to be there, got %v", got)
		}
		if got := typesOf(mustRead(t, store, other)); len(got) != 1 || got[0] != "Unaffected" {
			t.Fatalf("expected the rest of the transaction to commit, got %v", got)
		}
	})
}

func mustAppend(
	t *testing.T,
	store events.Store,
	streamID string,
	expectedVersion int,
	batch ...events.DomainEvent,
) events.AppendResult {
	t.Helper()
	result, err := store.Append(context.Background(), streamID, expectedVersion, batch)
	if err != nil {
		t.Fatalf("append to %s: %v", streamID, err)
	}
	if result.Outcome != events.OutcomeAppended {
		t.Fatalf("append to %s was refused: %+v", streamID, result)
	}
	return result
}

// tagged is the common shape of a query: one filter, whose tags must all be present.
func tagged(tags ...string) events.TagQuery {
	return events.TagQuery{Filters: []events.TagFilter{{Tags: tags}}}
}

func mustAppendIf(
	t *testing.T,
	store events.Store,
	condition events.Condition,
	batch ...events.DomainEvent,
) events.ConditionalAppendResult {
	t.Helper()
	result, err := store.AppendIf(context.Background(), condition, batch)
	if err != nil {
		t.Fatalf("conditional append: %v", err)
	}
	return result
}

func mustReadTagged(
	t *testing.T,
	store events.Store,
	query events.TagQuery,
	after int64,
) events.TaggedRead {
	t.Helper()
	return mustReadTaggedUntil(t, store, query, after, 0)
}

func mustReadTaggedUntil(
	t *testing.T,
	store events.Store,
	query events.TagQuery,
	after int64,
	until int64,
) events.TaggedRead {
	t.Helper()
	found, err := store.ReadTagged(context.Background(), query, after, until)
	if err != nil {
		t.Fatalf("read by tag query: %v", err)
	}
	return found
}

func mustHead(t *testing.T, store events.Store) int64 {
	t.Helper()
	head, err := store.Head(context.Background())
	if err != nil {
		t.Fatalf("read the head: %v", err)
	}
	return head
}

func mustRead(t *testing.T, store events.Store, streamID string) []events.CommittedEvent {
	t.Helper()
	stream, err := store.Read(context.Background(), streamID)
	if err != nil {
		t.Fatalf("read %s: %v", streamID, err)
	}
	return stream
}

func replay(
	t *testing.T,
	store events.Store,
	from int64,
	keep func(events.CommittedEvent) bool,
) []events.CommittedEvent {
	t.Helper()
	var replayed []events.CommittedEvent
	err := store.ReadAll(context.Background(), from, func(e events.CommittedEvent) error {
		if keep(e) {
			replayed = append(replayed, e)
		}
		return nil
	})
	if err != nil {
		t.Fatalf("replay: %v", err)
	}
	return replayed
}

func typesOf(recorded []events.CommittedEvent) []string {
	types := make([]string, 0, len(recorded))
	for _, event := range recorded {
		types = append(types, event.Type)
	}
	return types
}

// randomUUID is a version-4 UUID built from crypto/rand. Go's standard library has no UUID type,
// and this suite deliberately adds no dependency to get one — the two masked bytes below are the
// whole of what a library would do here.
func randomUUID(t *testing.T) string {
	t.Helper()
	buffer := make([]byte, 16)
	if _, err := rand.Read(buffer); err != nil {
		t.Fatalf("random uuid: %v", err)
	}
	buffer[6] = (buffer[6] & 0x0f) | 0x40 // version 4
	buffer[8] = (buffer[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf("%x-%x-%x-%x-%x",
		buffer[0:4], buffer[4:6], buffer[6:8], buffer[8:10], buffer[10:16])
}

func randomID(t *testing.T) string {
	t.Helper()
	buffer := make([]byte, 8)
	if _, err := rand.Read(buffer); err != nil {
		t.Fatalf("random id: %v", err)
	}
	return hex.EncodeToString(buffer)
}

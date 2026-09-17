//go:build integration

// The event store against real Postgres.
//
// Behind the `integration` build tag, so `make verify` never compiles it and the repository gate
// stays runnable with no infrastructure. `make test-integration` is the target that needs a
// database:
//
//	make services-up migrate test-integration
//
// It runs the same contract the infrastructure-free adapters pass, plus the four things only a
// real store can prove: that two appends at one version produce exactly one winner, that two
// conditional appends against one *boundary* do the same, that the log refuses to be rewritten, and
// that a replay never runs past a position an earlier event could still commit behind.
package eventstorepostgres_test

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"example.com/delivery-starter/adapters/driven/eventstorepostgres"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/eventstorecontract"
)

// openPool turns a refused connection or a missing table into the instruction that fixes it.
// Without this the first failure is a driver error, and the reader has to already know that the
// schema is applied by a separate target.
func openPool(t *testing.T) *pgxpool.Pool {
	t.Helper()

	url := os.Getenv("DATABASE_URL")
	if strings.TrimSpace(url) == "" {
		t.Fatal("DATABASE_URL is unset, so there is no database to test against. Run " +
			"`make test-integration`, which sets it, after `make services-up migrate`.")
	}
	pool, err := pgxpool.New(context.Background(), url)
	if err != nil {
		t.Fatalf("cannot reach the database at %s: %v\nStart it first:  make services-up migrate",
			url, err)
	}
	if _, err := pool.Exec(context.Background(), "SELECT 1 FROM events LIMIT 1"); err != nil {
		pool.Close()
		t.Fatalf("cannot read the events table: %v\nApply the schema first:  "+
			"make services-up migrate", err)
	}
	t.Cleanup(pool.Close)
	return pool
}

func TestPostgresEventStoreSatisfiesThePort(t *testing.T) {
	pool := openPool(t)
	eventstorecontract.Run(t, func(_ *testing.T, tagsOf events.TagsOf) events.Store {
		return eventstorepostgres.NewTagged(pool, tagsOf)
	})
}

// randomStream keeps each run in streams of its own. The log is append-only, so a database
// shared with a previous run cannot be cleaned — a fresh name is the only way to assert about
// only this run's events.
func randomStream(t *testing.T, prefix string) string {
	t.Helper()
	buffer := make([]byte, 8)
	if _, err := rand.Read(buffer); err != nil {
		t.Fatalf("random id: %v", err)
	}
	return fmt.Sprintf("%s-%s", prefix, hex.EncodeToString(buffer))
}

// One id for the whole file: these appends race each other inside one business transaction.
var correlationID = mustCorrelationID("018f3a2b-6c41-7c9d-9f0e-2a5b7c1d4e84")

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
	return eventWith(streamID, eventType, map[string]any{})
}

func eventWith(streamID, eventType string, payload map[string]any) events.DomainEvent {
	return events.DomainEvent{
		Type:          eventType,
		SchemaVersion: 1,
		StreamID:      streamID,
		Payload:       payload,
		OccurredAt:    "2024-01-01T00:00:00.000000+00:00",
		Actor:         events.Actor{Kind: "test", ID: "contention"},
		CorrelationID: correlationID,
	}
}

// seatTags tags an event by the seat it is claiming, which is what the boundary below is drawn out
// of. A real project's tagging function is this shape: the identifying attributes, derived.
func seatTags(event events.DomainEvent) []string {
	if seat, ok := event.Payload["seatId"].(string); ok {
		return []string{"seat:" + seat}
	}
	return nil
}

// claiming is an event that seatTags will tag: the payload and the tag in one place.
func claiming(streamID, seat string) events.DomainEvent {
	claim := event(streamID, "SeatClaimed")
	claim.Payload = map[string]any{"seatId": seat}
	return claim
}

// The Dynamic Consistency Boundary, raced for real — and the case expectedVersion cannot express,
// because each attempt writes to a *different* stream and the thing they contend for is a tag they
// share.
//
// The boundary is read once, and all eight attempts are guarded by that one position: eight workers
// who each decided, from the same facts, that the seat was free. Exactly one may record it. Some
// lose because the winner's event is already there when they check; the rest lose to SERIALIZABLE
// at commit, which is reported as the same conflict and needs the same next move from the caller.
// No single-writer store can produce this situation at all, which is why the guarantee is proved
// here and nowhere else.
//
// Reading the head inside each worker would test something else entirely — whichever worker
// happened to read after the winner committed would be guarded from a position past the winner's
// event, and would rightly be allowed to write. A caller that re-reads has re-decided, and this
// test is about callers that have not.
//
// What this asserts is the guarantee, not the mechanism. How far the eight transactions actually
// overlap is the scheduler's to decide, and a run where each check happened to see the previous
// winner already committed would pass on the condition alone, without SERIALIZABLE ever being
// asked to refuse anything. To see the isolation level doing work, change it in the adapter to the
// default and run this: what it costs when the overlap is real is what the setting buys.
func TestExactlyOneOfManySimultaneousConditionalAppendsWins(t *testing.T) {
	pool := openPool(t)
	store := eventstorepostgres.NewTagged(pool, seatTags)
	seat := randomStream(t, "seat")
	query := events.TagQuery{Filters: []events.TagFilter{{Tags: []string{"seat:" + seat}}}}

	decided, err := store.ReadTagged(context.Background(), query, 0, 0)
	if err != nil {
		t.Fatalf("read the boundary: %v", err)
	}

	const attempts = 8
	results := make([]events.ConditionalAppendResult, attempts)
	var group sync.WaitGroup
	var start sync.WaitGroup
	start.Add(1)
	for i := 0; i < attempts; i++ {
		group.Add(1)
		go func(index int) {
			defer group.Done()
			// Every goroutine waits on the same gate, so they contend rather than queue.
			start.Wait()
			claim := fmt.Sprintf("claim-%s-%d", seat, index)
			result, err := store.AppendIf(context.Background(),
				events.Condition{Query: query, After: decided.Head},
				[]events.DomainEvent{eventWith(claim, "SeatClaimed", map[string]any{"seatId": seat})},
			)
			if err != nil {
				t.Errorf("conditional append %d: %v", index, err)
				return
			}
			results[index] = result
		}(i)
	}
	start.Done()
	group.Wait()

	winners := 0
	for _, result := range results {
		switch result.Outcome {
		case events.OutcomeRecorded:
			winners++
		case events.OutcomeConditionConflict:
		default:
			t.Fatalf("unexpected outcome %q", result.Outcome)
		}
	}
	if winners != 1 {
		t.Fatalf("expected exactly one winner, got %d", winners)
	}

	found, err := store.ReadTagged(context.Background(), query, 0, 0)
	if err != nil {
		t.Fatalf("read by tag query: %v", err)
	}
	if len(found.Events) != 1 {
		t.Fatalf("the boundary holds %d events", len(found.Events))
	}
}

// The assertion no infrastructure-free store can make.
//
// The in-memory adapter serialises every call behind a mutex and can never produce two winners,
// so it would pass this test while proving nothing. SQLite serialises writers for the same
// reason. Only a real store genuinely races, which is why this guarantee is proved here and
// nowhere else.
func TestExactlyOneOfManySimultaneousFirstWritesWins(t *testing.T) {
	pool := openPool(t)
	store := eventstorepostgres.New(pool)
	stream := randomStream(t, "race")

	const attempts = 8
	results := make([]events.AppendResult, attempts)
	var group sync.WaitGroup
	var start sync.WaitGroup
	start.Add(1)
	for i := 0; i < attempts; i++ {
		group.Add(1)
		go func(index int) {
			defer group.Done()
			// Every goroutine waits on the same gate, so they contend rather than queue.
			start.Wait()
			result, err := store.Append(context.Background(), stream, events.NoStream,
				[]events.DomainEvent{event(stream, fmt.Sprintf("Attempt%d", index))})
			if err != nil {
				t.Errorf("append %d: %v", index, err)
				return
			}
			results[index] = result
		}(i)
	}
	start.Done()
	group.Wait()

	winners := 0
	for _, result := range results {
		switch result.Outcome {
		case events.OutcomeAppended:
			winners++
		case events.OutcomeVersionConflict:
			if result.ActualVersion != 0 {
				t.Fatalf("a loser saw actual version %d", result.ActualVersion)
			}
		default:
			t.Fatalf("unexpected outcome %q", result.Outcome)
		}
	}
	if winners != 1 {
		t.Fatalf("expected exactly one winner, got %d", winners)
	}

	recorded, err := store.Read(context.Background(), stream)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(recorded) != 1 {
		t.Fatalf("the stream holds %d events", len(recorded))
	}
}

// The guarantee a projection's single-number checkpoint rests on, and the one bug in this design
// that leaves no trace.
//
// A position is assigned when a row is inserted and becomes visible when its transaction commits,
// and those are two different moments: two appends overlapping take 5 and 6, and 6 can commit first.
// A replay that hands out 6 while 5 is still in flight makes the projection record "next is 7", and
// 5 then arrives behind a checkpoint that has already passed it — a view missing a row, permanently,
// with a log that is perfectly correct and nothing anywhere complaining.
//
// So ReadAll waits for the appends in flight and stops at the last settled position. The replay
// below finishes only after the slow append commits, and then it holds both events in order.
// Without the protocol it would finish at once, holding the second event and not the first.
//
// Only a real store can produce this at all: the in-memory adapter is one lock and SQLite serialises
// its writers, so in neither can a position be taken and committed out of order.
func TestAReplayStopsShortOfAPositionAnEarlierEventCouldStillArriveBehind(t *testing.T) {
	// A pool per store, because these three have to be three connections: the slow append holds its
	// transaction open while the others work.
	slow := eventstorepostgres.New(openPool(t))
	fast := eventstorepostgres.New(openPool(t))
	reader := eventstorepostgres.New(openPool(t))
	first, second := randomStream(t, "slow"), randomStream(t, "fast")

	// Where this case's own events begin: the log is shared with every other case and every previous
	// run, so a replay from zero would read all of them.
	found, err := reader.ReadTagged(context.Background(), events.TagQuery{}, 0, 0)
	if err != nil {
		t.Fatalf("read the head: %v", err)
	}
	start := found.Head + 1

	var replayed []string
	finished := make(chan error, 1)
	err = slow.InUnitOfWork(context.Background(), func(inside context.Context) error {
		if _, err := slow.Append(inside, first, events.NoStream,
			[]events.DomainEvent{event(first, "Slow")}); err != nil {
			return err
		}
		// Its position is taken; its commit is not. This one takes the next position and commits.
		if _, err := fast.Append(context.Background(), second, events.NoStream,
			[]events.DomainEvent{event(second, "Fast")}); err != nil {
			return err
		}

		// Started here, with one event visible and an earlier one still in flight — the moment the
		// protocol exists for.
		go func() {
			finished <- reader.ReadAll(context.Background(), start,
				func(replayedEvent events.CommittedEvent) error {
					replayed = append(replayed, replayedEvent.Type)
					return nil
				})
		}()

		select {
		case <-finished:
			t.Errorf("a replay finished while an append was in flight, and read %v", replayed)
		case <-time.After(time.Second):
		}
		return nil
	})
	if err != nil {
		t.Fatalf("the slow append: %v", err)
	}

	select {
	case err := <-finished:
		if err != nil {
			t.Fatalf("replay: %v", err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("a replay never finished after the append committed")
	}
	if len(replayed) != 2 || replayed[0] != "Slow" || replayed[1] != "Fast" {
		t.Fatalf("expected both events in order, got %v", replayed)
	}
}

// The same gap as the replay's, on the write path, where it breaks the constraint instead of a view
// — and this is the case the whole tag boundary rests on.
//
// Two appends take 5 and 6; 6 commits first. A decision reading a head of 6 while 5 is still
// invisible would be guarded from *after* 6 — and 5, the very event that should refuse it, sits below
// its own boundary where the guard never looks. The append is allowed, the seat is claimed twice, and
// the log looks perfectly correct afterwards.
//
// So a boundary is only ever a settled position: Head waits for the appends in flight, which makes
// the read that follows see the event as well. The claim below is therefore refused, and it is
// refused by the *condition* rather than by chance.
func TestRefusesAConditionalAppendAgainstAnEventInFlightWhenTheBoundaryWasRead(t *testing.T) {
	slow := eventstorepostgres.NewTagged(openPool(t), seatTags)
	fast := eventstorepostgres.NewTagged(openPool(t), seatTags)
	decider := eventstorepostgres.NewTagged(openPool(t), seatTags)
	seat := randomStream(t, "seat")
	query := events.TagQuery{Filters: []events.TagFilter{{Tags: []string{"seat:" + seat}}}}

	type decision struct {
		boundary int64
		types    []string
	}
	drawn := make(chan decision, 1)

	err := slow.InUnitOfWork(context.Background(), func(inside context.Context) error {
		claim := "claim-" + seat + "-1"
		if _, err := slow.Append(inside, claim, events.NoStream, []events.DomainEvent{
			claiming(claim, seat),
		}); err != nil {
			return err
		}
		// Its position is taken; its commit is not. This one takes the next position and commits.
		other := randomStream(t, "other")
		if _, err := fast.Append(context.Background(), other, events.NoStream,
			[]events.DomainEvent{event(other, "Unrelated")}); err != nil {
			return err
		}

		// A decision, drawn the way every DCB caller draws one: pin the boundary, then read it.
		go func() {
			boundary, err := decider.Head(context.Background())
			if err != nil {
				t.Errorf("head: %v", err)
				return
			}
			found, err := decider.ReadTagged(context.Background(), query, 0, boundary)
			if err != nil {
				t.Errorf("read tagged: %v", err)
				return
			}
			types := make([]string, 0, len(found.Events))
			for _, one := range found.Events {
				types = append(types, one.Type)
			}
			drawn <- decision{boundary: boundary, types: types}
		}()

		select {
		case made := <-drawn:
			t.Errorf("a boundary was drawn at %d while an append was in flight, and read %v",
				made.boundary, made.types)
		case <-time.After(time.Second):
		}
		return nil
	})
	if err != nil {
		t.Fatalf("the slow append: %v", err)
	}

	select {
	case made := <-drawn:
		// The decision now knows about the claim, which is the whole point of waiting.
		if len(made.types) != 1 || made.types[0] != "SeatClaimed" {
			t.Fatalf("expected the decision to see the claim, got %v", made.types)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("a boundary was never drawn after the append committed")
	}

	// And a caller that decided anyway is refused by the condition rather than by luck.
	refused, err := decider.AppendIf(context.Background(),
		events.Condition{Query: query, After: 0},
		[]events.DomainEvent{claiming("claim-"+seat+"-2", seat)})
	if err != nil {
		t.Fatalf("conditional append: %v", err)
	}
	if refused.Outcome != events.OutcomeConditionConflict {
		t.Fatalf("expected the claim refused, got %q", refused.Outcome)
	}
}

func TestRefusesToLetACommittedEventBeRewrittenOrRemoved(t *testing.T) {
	pool := openPool(t)
	store := eventstorepostgres.New(pool)
	stream := randomStream(t, "append-only")

	if _, err := store.Append(context.Background(), stream, events.NoStream,
		[]events.DomainEvent{event(stream, "Recorded")}); err != nil {
		t.Fatalf("append: %v", err)
	}

	statements := []string{
		"UPDATE events SET event_type = 'Rewritten' WHERE stream_id = $1",
		"DELETE FROM events WHERE stream_id = $1",
	}
	for _, statement := range statements {
		_, err := pool.Exec(context.Background(), statement, stream)
		if err == nil {
			t.Fatalf("%q was permitted", statement)
		}
		if !strings.Contains(err.Error(), "append-only") {
			t.Fatalf("%q failed for the wrong reason: %v", statement, err)
		}
	}

	recorded, err := store.Read(context.Background(), stream)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if len(recorded) != 1 || recorded[0].Type != "Recorded" {
		t.Fatalf("the log was altered: %+v", recorded)
	}
}

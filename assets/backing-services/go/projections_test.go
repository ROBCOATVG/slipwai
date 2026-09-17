// The catch-up runner.
//
// Against the in-memory pair, and only that pair, because the runner has no I/O of its own: it is
// two ports and a loop, and what these cases are about is the loop. That is also why it is here
// rather than beside an adapter — a project that chose the in-memory store still gets every one of
// these.
//
// The guarantee the runner *rests* on — that a checkpoint recorded in a failed unit of work does
// not move — is proved in checkpointstorecontract, which runs against every store adapter this
// project has, where a rollback is the database's own rather than a restored copy. Split that way deliberately: the
// transaction is the adapters' promise, and the loop is what this file holds to it.
package projections_test

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"testing"
	"time"

	"example.com/delivery-starter/adapters/driven/checkpointstorememory"
	"example.com/delivery-starter/adapters/driven/eventstorememory"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
	"example.com/delivery-starter/projections"
)

var now = time.Date(2026, 9, 10, 12, 0, 0, 0, time.UTC)

func clockAt(instant time.Time) func() time.Time {
	return func() time.Time { return instant }
}

func runner(owner string, instant time.Time) projections.Runner {
	return projections.Runner{Owner: owner, Clock: clockAt(instant)}
}

// titles is a read model with somewhere to put the result, which is all a projection is.
//
// Its rows are derived: every one of them comes from an event, so Reset plus a replay reproduces it
// exactly. A field this type alone knew — a flag it set when it processed a row — could not survive
// Reset, and finding that out during an incident is how a rebuild becomes data loss.
type titles struct {
	name    string
	rows    []string
	batches int
	fail    error
}

func (v *titles) Name() string { return v.name }

func (v *titles) Apply(_ context.Context, batch []events.CommittedEvent) error {
	v.batches++
	for _, event := range batch {
		v.rows = append(v.rows, event.Type)
	}
	return v.fail
}

func (v *titles) Reset(context.Context) error {
	v.rows = nil
	return nil
}

func pair(t *testing.T) (*eventstorememory.Store, readmodels.Store) {
	t.Helper()
	store := eventstorememory.New()
	return store, checkpointstorememory.New(store)
}

func givenALogOf(t *testing.T, store events.Store, types ...string) {
	t.Helper()
	stream := "projection-" + randomID(t)
	correlationID, err := events.NewCorrelationID("018f3a2b-6c41-7c9d-9f0e-2a5b7c1d4e84")
	if err != nil {
		t.Fatalf("correlation id: %v", err)
	}
	batch := make([]events.DomainEvent, 0, len(types))
	for _, eventType := range types {
		batch = append(batch, events.DomainEvent{
			Type:          eventType,
			SchemaVersion: 1,
			StreamID:      stream,
			Payload:       map[string]any{},
			OccurredAt:    "2024-01-01T00:00:00.000000+00:00",
			Actor:         events.Actor{Kind: "test", ID: "projections"},
			CorrelationID: correlationID,
		})
	}
	if _, err := store.Append(context.Background(), stream, events.NoStream, batch); err != nil {
		t.Fatalf("append: %v", err)
	}
}

func TestAppliesTheWholeLogAndLeavesTheCheckpointPastIt(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed", "Paid")
	view := &titles{name: "titles"}

	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view, runner("worker-1", now))
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if advance != (projections.Advance{Applied: 2, Leased: true}) {
		t.Fatalf("expected two events applied under a lease, got %+v", advance)
	}
	if len(view.rows) != 2 || view.rows[0] != "Placed" || view.rows[1] != "Paid" {
		t.Fatalf("expected the log folded in order, got %v", view.rows)
	}
	position, err := checkpoints.PositionOf(context.Background(), "titles")
	if err != nil || position != 3 {
		t.Fatalf("expected the checkpoint past the log, got %d (%v)", position, err)
	}
}

func TestResumesFromTheCheckpointAndAppliesNothingTwice(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	view := &titles{name: "titles"}
	if _, err := projections.CatchUp(context.Background(), store, checkpoints, view, runner("worker-1", now)); err != nil {
		t.Fatalf("first pass: %v", err)
	}

	givenALogOf(t, store, "Paid")
	again, err := projections.CatchUp(context.Background(), store, checkpoints, view, runner("worker-1", now))
	if err != nil {
		t.Fatalf("second pass: %v", err)
	}

	if again.Applied != 1 {
		t.Fatalf("expected only the new event applied, got %d", again.Applied)
	}
	if len(view.rows) != 2 {
		t.Fatalf("expected two rows in all, got %v", view.rows)
	}
}

func TestSaysAPassHadNothingToDoWithoutTouchingTheView(t *testing.T) {
	store, checkpoints := pair(t)
	view := &titles{name: "titles"}

	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view, runner("worker-1", now))
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if advance != (projections.Advance{Applied: 0, Leased: true}) {
		t.Fatalf("expected a leased pass with nothing to do, got %+v", advance)
	}
	if view.batches != 0 {
		t.Fatalf("expected the view untouched, got %d batches", view.batches)
	}
}

// Each batch is one transaction, so the size trades how much work a crash repeats against how long
// one transaction holds its locks. That it batches at all is what keeps a rebuild over a long log
// from materialising the whole thing.
func TestAppliesALongLogInBatchesOfTheSizeItWasGiven(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "One", "Two", "Three", "Four", "Five")
	view := &titles{name: "titles"}

	pass := runner("worker-1", now)
	pass.BatchSize = 2
	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view, pass)
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if advance.Applied != 5 {
		t.Fatalf("expected five events applied, got %d", advance.Applied)
	}
	if view.batches != 3 {
		t.Fatalf("expected three batches, got %d", view.batches)
	}
}

// The ordinary case for every replica but one, and not a failure — which is why Leased is reported
// separately from Applied.
func TestDoesNothingInASecondWorkerWhileTheFirstHoldsTheLease(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	if _, _, err := checkpoints.Claim(context.Background(), "titles", "worker-1", now, 30*time.Second); err != nil {
		t.Fatalf("claim: %v", err)
	}
	view := &titles{name: "titles"}

	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view,
		runner("worker-2", now.Add(time.Second)))
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if advance != (projections.Advance{}) {
		t.Fatalf("expected a pass that did nothing and held no lease, got %+v", advance)
	}
	if len(view.rows) != 0 {
		t.Fatalf("expected the view untouched, got %v", view.rows)
	}
}

func TestTakesOverInAnotherWorkerOnceTheLeaseHasLapsed(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	if _, _, err := checkpoints.Claim(context.Background(), "titles", "worker-1", now, 30*time.Second); err != nil {
		t.Fatalf("claim: %v", err)
	}
	view := &titles{name: "titles"}

	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view,
		runner("worker-2", now.Add(5*time.Minute)))
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if advance != (projections.Advance{Applied: 1, Leased: true}) {
		t.Fatalf("expected the lapsed lease taken over, got %+v", advance)
	}
}

func TestReleasesTheLeaseWhenThePassIsDone(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")

	if _, err := projections.CatchUp(context.Background(), store, checkpoints,
		&titles{name: "titles"}, runner("worker-1", now)); err != nil {
		t.Fatalf("catch up: %v", err)
	}

	_, ok, err := checkpoints.Claim(context.Background(), "titles", "worker-2", now, 30*time.Second)
	if err != nil || !ok {
		t.Fatalf("expected the lease released, got ok=%v (%v)", ok, err)
	}
}

// Exactly-once, and there is no idempotency key in it: the checkpoint moves in the same transaction
// as the rows, so a crash before the commit leaves both untouched and the next pass reads the same
// batch again.
func TestMovesNeitherTheViewNorTheCheckpointWhenABatchFails(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	viewFailed := errors.New("the view write failed")
	broken := &titles{name: "broken", fail: viewFailed}

	_, err := projections.CatchUp(context.Background(), store, checkpoints, broken, runner("worker-1", now))

	if !errors.Is(err, viewFailed) {
		t.Fatalf("expected the view's failure to reach the caller, got %v", err)
	}
	position, err := checkpoints.PositionOf(context.Background(), "broken")
	if err != nil || position != readmodels.FromTheBeginning {
		t.Fatalf("expected the checkpoint not to move, got %d (%v)", position, err)
	}
}

// Otherwise one bad batch costs a whole lease before anything tries again — every time.
func TestReleasesTheLeaseEvenWhenThePassFails(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	broken := &titles{name: "broken", fail: errors.New("the view write failed")}

	if _, err := projections.CatchUp(context.Background(), store, checkpoints, broken, runner("worker-1", now)); err == nil {
		t.Fatal("expected the pass to fail")
	}

	_, ok, err := checkpoints.Claim(context.Background(), "broken", "worker-2", now, 30*time.Second)
	if err != nil || !ok {
		t.Fatalf("expected the lease released anyway, got ok=%v (%v)", ok, err)
	}
}

// What makes a read model disposable, and therefore what makes a projection bug fixable by changing
// the fold rather than by patching rows.
func TestARebuildEmptiesTheViewAndFoldsTheWholeLogIntoItAgain(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed", "Paid")
	view := &titles{name: "titles"}
	if _, err := projections.CatchUp(context.Background(), store, checkpoints, view, runner("worker-1", now)); err != nil {
		t.Fatalf("catch up: %v", err)
	}
	view.rows = append(view.rows, "something nothing derived")

	advance, err := projections.Rebuild(context.Background(), store, checkpoints, view, runner("worker-1", now))
	if err != nil {
		t.Fatalf("rebuild: %v", err)
	}

	if advance != (projections.Advance{Applied: 2, Leased: true}) {
		t.Fatalf("expected the whole log folded again, got %+v", advance)
	}
	if len(view.rows) != 2 || view.rows[0] != "Placed" {
		t.Fatalf("expected only derived rows, got %v", view.rows)
	}
}

// A rebuild is destructive, so "somebody else is advancing this" has to be distinguishable from
// "there was nothing to apply". Leased is that distinction.
func TestARebuildThatCannotTakeTheLeaseLeavesTheViewAlone(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	view := &titles{name: "titles"}
	if _, err := projections.CatchUp(context.Background(), store, checkpoints, view, runner("worker-1", now)); err != nil {
		t.Fatalf("catch up: %v", err)
	}
	if _, _, err := checkpoints.Claim(context.Background(), "titles", "worker-1", now, 30*time.Second); err != nil {
		t.Fatalf("claim: %v", err)
	}

	advance, err := projections.Rebuild(context.Background(), store, checkpoints, view,
		runner("worker-2", now.Add(time.Second)))
	if err != nil {
		t.Fatalf("rebuild: %v", err)
	}

	if advance != (projections.Advance{}) {
		t.Fatalf("expected the rebuild to refuse, got %+v", advance)
	}
	if len(view.rows) != 1 {
		t.Fatalf("expected the view left alone, got %v", view.rows)
	}
}

func randomID(t *testing.T) string {
	t.Helper()
	buffer := make([]byte, 8)
	if _, err := rand.Read(buffer); err != nil {
		t.Fatalf("random id: %v", err)
	}
	return hex.EncodeToString(buffer)
}

// A pass claims its lease for the term the runner was given, and for DefaultLease when it was
// given none.
//
// The view is where that can be observed, because it is the only code the runner calls while the
// lease is held: Apply runs inside the pass. A pass that claimed for no time at all would let a
// second worker take over the batch it is halfway through applying, and both would write the same
// rows — which is the failure the lease exists to prevent, so the default term is load-bearing and
// not a convenience.
type contendedTitles struct {
	*titles
	checkpoints readmodels.Store
	rivalAt     time.Time
	stolen      bool
}

func (v *contendedTitles) Apply(ctx context.Context, batch []events.CommittedEvent) error {
	_, ok, err := v.checkpoints.Claim(ctx, v.Name(), "worker-2", v.rivalAt, 30*time.Second)
	if err != nil {
		return err
	}
	v.stolen = v.stolen || ok
	return v.titles.Apply(ctx, batch)
}

func TestKeepsItsLeaseThroughAPassWhenItWasGivenNoTerm(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	view := &contendedTitles{
		titles:      &titles{name: "titles"},
		checkpoints: checkpoints,
		rivalAt:     now.Add(time.Second),
	}

	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view,
		runner("worker-1", now))
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if view.stolen {
		t.Fatal("a second worker took the lease from a pass that was still applying a batch")
	}
	if advance != (projections.Advance{Applied: 1, Leased: true}) {
		t.Fatalf("expected the pass to finish under its own lease, got %+v", advance)
	}
}

func TestKeepsItsLeaseForTheTermItWasGiven(t *testing.T) {
	store, checkpoints := pair(t)
	givenALogOf(t, store, "Placed")
	view := &contendedTitles{
		titles:      &titles{name: "titles"},
		checkpoints: checkpoints,
		rivalAt:     now.Add(2 * time.Minute),
	}

	// Longer than DefaultLease, so a runner that quietly ignored the term it was given would lose
	// the lease two minutes in — which is what a projection whose batches are slow asks for.
	advance, err := projections.CatchUp(context.Background(), store, checkpoints, view,
		projections.Runner{Owner: "worker-1", Clock: clockAt(now), TTL: 5 * time.Minute})
	if err != nil {
		t.Fatalf("catch up: %v", err)
	}

	if view.stolen {
		t.Fatal("a second worker took a lease the runner asked to hold for five minutes")
	}
	if advance != (projections.Advance{Applied: 1, Leased: true}) {
		t.Fatalf("expected the pass to finish under its own lease, got %+v", advance)
	}
}

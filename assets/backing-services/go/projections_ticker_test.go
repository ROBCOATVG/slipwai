package projections_test

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"example.com/delivery-starter/adapters/driven/eventstorememory"
	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
	"example.com/delivery-starter/projections"
)

// The ticker — the loop, not the pass.
//
// What is worth asserting here is exactly what Ticker contributes: that a pass happens without anybody
// calling it, that cancelling the context stops it cleanly, and that a broken projection does not end
// the subscription. The pass itself is the rest of this file's suite.

// A view that reports what it applied as it happens, because these assertions race the loop rather
// than following it. Buffered and non-blocking: a test that has stopped reading is the shutdown case
// below, and a projection must not stall a pass because nobody is listening.
type watched struct {
	name string
	rows chan string
	fail error
}

func (v *watched) Name() string { return v.name }

func (v *watched) Apply(_ context.Context, batch []events.CommittedEvent) error {
	for _, event := range batch {
		select {
		case v.rows <- event.Type:
		default:
		}
	}
	return v.fail
}

func (v *watched) Reset(context.Context) error { return nil }

func TestATickerCatchesAProjectionUpWithoutAnybodyCallingIt(t *testing.T) {
	store, checkpoints := pair(t)
	view := &watched{name: "titles", rows: make(chan string, 4)}
	givenALogOf(t, store, "Placed")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	stopped := make(chan error, 1)
	ticker := projections.Ticker{Every: time.Millisecond}
	go func() {
		stopped <- ticker.Run(ctx, store, checkpoints, []readmodels.Projection{view})
	}()

	select {
	case row := <-view.rows:
		if row != "Placed" {
			t.Fatalf("expected the event applied, got %q", row)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("expected a pass to happen with nothing calling it")
	}

	// Cancelling is what stops it, and Run reports a cancellation as no error: a ticker stopped on
	// purpose has not failed, and a `serve` that treated it as a failure would exit non-zero on Ctrl-C.
	cancel()
	select {
	case err := <-stopped:
		if err != nil {
			t.Fatalf("expected a clean stop, got %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("expected the ticker to stop when its context was cancelled")
	}
}

func TestATickerKeepsGoingAndReportsWhenAProjectionFails(t *testing.T) {
	store, checkpoints := pair(t)
	broken := &watched{name: "broken", rows: make(chan string, 4), fail: errors.New("the view write failed")}
	givenALogOf(t, store, "Placed")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	failures := make(chan error, 8)
	ticker := projections.Ticker{
		Every: time.Millisecond,
		OnFailure: func(err error) {
			select {
			case failures <- err:
			default:
			}
		},
	}
	go func() {
		_ = ticker.Run(ctx, store, checkpoints, []readmodels.Projection{broken})
	}()

	// Twice, which is the point: a broken fold is reported and then tried again, rather than ending the
	// subscription and leaving the view stale with nothing running to notice.
	for attempt := 1; attempt <= 2; attempt++ {
		select {
		case err := <-failures:
			if err == nil {
				t.Fatal("expected the failure to be reported")
			}
		case <-time.After(2 * time.Second):
			t.Fatalf("expected pass %d to report its failure", attempt)
		}
	}
}

// A view that reports the lease as it stood while its own batch was being applied — the only moment
// the ticker's identity and its clock are observable, because the pass releases the lease when it
// ends.
type leaseWatcher struct {
	database *eventstorememory.Database
	name     string
	seen     chan eventstorememory.LeaseRow
}

func (v *leaseWatcher) Name() string { return v.name }

func (v *leaseWatcher) Apply(context.Context, []events.CommittedEvent) error {
	if held, ok := v.database.Lease(v.name); ok {
		select {
		case v.seen <- held:
		default:
		}
	}
	return nil
}

func (v *leaseWatcher) Reset(context.Context) error { return nil }

// The identity and the clock a ticker claims under, which is what a second replica is refused by.
//
// Both are options because a test has to be able to choose them; the assertions here are what would
// otherwise be a comment saying so.
func TestATickerClaimsUnderTheOwnerAndClockItWasGiven(t *testing.T) {
	store, checkpoints := pair(t)
	view := &leaseWatcher{database: store.Database(), name: "titles", seen: make(chan eventstorememory.LeaseRow, 4)}
	givenALogOf(t, store, "Placed")
	at := time.Date(2026, 9, 10, 12, 0, 0, 0, time.UTC)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	ticker := projections.Ticker{
		Every: time.Millisecond,
		Owner: "worker-of-my-choosing",
		Clock: func() time.Time { return at },
	}
	go func() {
		_ = ticker.Run(ctx, store, checkpoints, []readmodels.Projection{view})
	}()

	select {
	case held := <-view.seen:
		if held.Owner != "worker-of-my-choosing" {
			t.Fatalf("expected the lease held by the owner the ticker was given, got %q", held.Owner)
		}
		// The clock is what the expiry is measured from, so a fixed one fixes the expiry exactly.
		if want := at.Add(projections.DefaultLease); !held.ExpiresAt.Equal(want) {
			t.Fatalf("expected the lease to expire at %s, got %s", want, held.ExpiresAt)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("expected a pass to happen and hold a lease")
	}
}

// With no owner given, the ticker still has to be identifiable — an empty name is one every replica
// shares, and the holder of a lease may always renew it, so two workers called "" would both be
// certain they held it.
func TestATickerNamesAnOwnerOfItsOwnWhenGivenNone(t *testing.T) {
	store, checkpoints := pair(t)
	view := &leaseWatcher{database: store.Database(), name: "titles", seen: make(chan eventstorememory.LeaseRow, 4)}
	givenALogOf(t, store, "Placed")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() {
		_ = (projections.Ticker{Every: time.Millisecond}).Run(
			ctx, store, checkpoints, []readmodels.Projection{view})
	}()

	select {
	case held := <-view.seen:
		if !strings.HasPrefix(held.Owner, fmt.Sprintf("worker-%d-", os.Getpid())) {
			t.Fatalf("expected an owner naming this process, got %q", held.Owner)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("expected a pass to happen and hold a lease")
	}
}

// A checkpoint store that reports every claim, which is one per pass.
type countedClaims struct {
	readmodels.Store
	claims chan struct{}
}

func (s *countedClaims) Claim(
	ctx context.Context,
	projection string,
	owner string,
	now time.Time,
	ttl time.Duration,
) (readmodels.Lease, bool, error) {
	select {
	case s.claims <- struct{}{}:
	default:
	}
	return s.Store.Claim(ctx, projection, owner, now, ttl)
}

// A pass count over a window: what an interval is observable as.
func passesWithin(
	t *testing.T,
	ticker projections.Ticker,
	window time.Duration,
) int {
	t.Helper()
	store, checkpoints := pair(t)
	counted := &countedClaims{Store: checkpoints, claims: make(chan struct{}, 4096)}
	givenALogOf(t, store, "Placed")

	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		_ = ticker.Run(ctx, store, counted, []readmodels.Projection{&titles{name: "titles"}})
	}()
	time.Sleep(window)
	cancel()
	return len(counted.claims)
}

// An interval of zero is not an interval: with no `Every` and nothing in the environment, the pause
// is DefaultEvery — a second — so a window far shorter than that sees exactly one pass. Spinning
// instead would burn a database connection per millisecond for a subscription nobody asked to be
// that fresh.
func TestATickerPausesForADefaultSecondWhenNothingNamesAnInterval(t *testing.T) {
	t.Setenv("PROJECTIONS_EVERY_MS", "")
	if passes := passesWithin(t, projections.Ticker{}, 150*time.Millisecond); passes != 1 {
		t.Fatalf("expected one pass in 150ms at the default interval, got %d", passes)
	}
}

// The environment names it, so a deployment can slow a subscription down without a rebuild.
func TestATickerPausesForTheIntervalTheEnvironmentNames(t *testing.T) {
	t.Setenv("PROJECTIONS_EVERY_MS", "20")
	if passes := passesWithin(t, projections.Ticker{}, 200*time.Millisecond); passes < 3 {
		t.Fatalf("expected several passes in 200ms at a 20ms interval, got %d", passes)
	}
}

// And a long one is honoured as written — the case that catches an interval computed in the wrong
// unit, which would look like a healthy subscription and hammer the database.
func TestATickerHonoursALongIntervalFromTheEnvironment(t *testing.T) {
	t.Setenv("PROJECTIONS_EVERY_MS", "100000")
	if passes := passesWithin(t, projections.Ticker{}, 150*time.Millisecond); passes != 1 {
		t.Fatalf("expected one pass in 150ms at a 100s interval, got %d", passes)
	}
}

// Nonsense in the environment falls back rather than spinning: an unparseable value and a zero are
// both "nothing said", and a pause of zero is the one answer that must never be reached by accident.
func TestATickerFallsBackWhenTheEnvironmentNamesNoUsableInterval(t *testing.T) {
	for _, value := range []string{"0", "-5", "soon"} {
		t.Setenv("PROJECTIONS_EVERY_MS", value)
		if passes := passesWithin(t, projections.Ticker{}, 150*time.Millisecond); passes != 1 {
			t.Fatalf("expected one pass in 150ms with PROJECTIONS_EVERY_MS=%q, got %d", value, passes)
		}
	}
}

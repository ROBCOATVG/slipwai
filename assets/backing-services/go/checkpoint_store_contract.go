// Package checkpointstorecontract holds one contract, run against every checkpoint adapter.
//
// The infrastructure-free adapters run it in `make test`; Postgres runs it in
// `make test-integration`. Two adapters that pass different tests are two different ports wearing
// one name, and with a checkpoint the day they diverge is the day a projection silently applies an
// event twice.
//
// NewStores returns the pair, not the checkpoint store alone: every adapter is built from the event
// store it follows, because Record has to land in the same transaction as the view write it
// accounts for. A contract that let an adapter be constructed on its own would be a contract that
// permitted the one mistake this port exists to prevent.
//
// Every case works in a freshly named projection, because the table is shared with everything else
// in the database and a DELETE between cases would only prove that deletes work.
package checkpointstorecontract

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"testing"
	"time"

	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
)

// Now is a fixed instant, so expiry is tested by choosing the time rather than by sleeping through
// it.
var Now = time.Date(2026, 9, 10, 12, 0, 0, 0, time.UTC)

const aWhile = 30 * time.Second

// NewStores builds the pair under test.
type NewStores func(t *testing.T) (events.Store, readmodels.Store)

// Run holds an adapter to the port's contract.
func Run(t *testing.T, newStores NewStores) {
	t.Helper()

	correlationID, err := events.NewCorrelationID(randomUUID(t))
	if err != nil {
		t.Fatalf("correlation id: %v", err)
	}
	event := func(streamID string) events.DomainEvent {
		return events.DomainEvent{
			Type:          "Started",
			SchemaVersion: 1,
			StreamID:      streamID,
			Payload:       map[string]any{},
			OccurredAt:    "2024-01-01T00:00:00.000000+00:00",
			Actor:         events.Actor{Kind: "test", ID: "checkpoints"},
			CorrelationID: correlationID,
		}
	}
	newProjection := func() string { return "contract-" + randomID(t) }

	// An unknown projection has consumed nothing, which is not an error — a rebuild has to be
	// expressible without a special case.
	t.Run("starts a projection nothing has recorded at the beginning", func(t *testing.T) {
		_, checkpoints := newStores(t)

		if position := mustPosition(t, checkpoints, newProjection()); position != readmodels.FromTheBeginning {
			t.Fatalf("expected to start at the beginning, got %d", position)
		}
	})

	t.Run("records a position and reads it back", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()

		mustRecord(t, checkpoints, projection, 42)

		if position := mustPosition(t, checkpoints, projection); position != 42 {
			t.Fatalf("expected 42, got %d", position)
		}
	})

	t.Run("records the same projection twice without a second row", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()

		mustRecord(t, checkpoints, projection, 7)
		mustRecord(t, checkpoints, projection, 9)

		if position := mustPosition(t, checkpoints, projection); position != 9 {
			t.Fatalf("expected the second write to win, got %d", position)
		}
	})

	t.Run("puts a position back to the beginning for a rebuild", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		mustRecord(t, checkpoints, projection, 99)

		mustRecord(t, checkpoints, projection, readmodels.FromTheBeginning)

		if position := mustPosition(t, checkpoints, projection); position != readmodels.FromTheBeginning {
			t.Fatalf("expected the beginning, got %d", position)
		}
	})

	// The whole reason this port exists, and the reason its adapters are built from the event
	// store: the checkpoint moves in the same transaction as the rows it accounts for, so a crash
	// before the commit leaves both untouched and the next pass reads the same batch again. That is
	// exactly-once, and there is no idempotency key in it.
	t.Run("does not record a position written in a unit of work that fails", func(t *testing.T) {
		store, checkpoints := newStores(t)
		projection := newProjection()
		stream := "checkpoint-" + randomID(t)
		viewFailed := errors.New("the view write failed")

		err := store.InUnitOfWork(context.Background(), func(inside context.Context) error {
			batch := []events.DomainEvent{event(stream)}
			if _, err := store.Append(inside, stream, events.NoStream, batch); err != nil {
				return err
			}
			if err := checkpoints.Record(inside, projection, 5); err != nil {
				return err
			}
			return viewFailed
		})

		if !errors.Is(err, viewFailed) {
			t.Fatalf("expected the view's failure to reach the caller, got %v", err)
		}
		if position := mustPosition(t, checkpoints, projection); position != readmodels.FromTheBeginning {
			t.Fatalf("expected the checkpoint not to move, got %d", position)
		}
		stored, err := store.Read(context.Background(), stream)
		if err != nil {
			t.Fatalf("read: %v", err)
		}
		if len(stored) != 0 {
			t.Fatalf("expected the append to roll back with it, got %d events", len(stored))
		}
	})

	t.Run("claims a projection for one owner", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()

		lease, ok := mustClaim(t, checkpoints, projection, "worker-1", Now)

		if !ok || lease.Owner != "worker-1" || !lease.ExpiresAt.Equal(Now.Add(aWhile)) {
			t.Fatalf("expected a lease until %v, got %+v (ok=%v)", Now.Add(aWhile), lease, ok)
		}
	})

	t.Run("refuses a claim while somebody else holds an unexpired lease", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		mustClaim(t, checkpoints, projection, "worker-1", Now)

		if _, ok := mustClaim(t, checkpoints, projection, "worker-2", Now.Add(time.Second)); ok {
			t.Fatal("expected the second worker to be refused")
		}
	})

	// How a pass long enough to outlive its lease keeps it: the holder always succeeds.
	t.Run("lets the owner renew its own lease", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		mustClaim(t, checkpoints, projection, "worker-1", Now)

		renewed, ok := mustClaim(t, checkpoints, projection, "worker-1", Now.Add(10*time.Second))

		if !ok || !renewed.ExpiresAt.Equal(Now.Add(10*time.Second).Add(aWhile)) {
			t.Fatalf("expected the lease renewed, got %+v (ok=%v)", renewed, ok)
		}
	})

	// An expiry rather than a lock, because the failure to survive is a worker that dies holding
	// it. A lock nothing releases is a projection that never advances again, and the first anybody
	// hears of it is a stale view.
	t.Run("lets another owner claim a lapsed lease", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		mustClaim(t, checkpoints, projection, "worker-1", Now)

		taken, ok := mustClaim(t, checkpoints, projection, "worker-2", Now.Add(aWhile+time.Second))

		if !ok || taken.Owner != "worker-2" {
			t.Fatalf("expected worker-2 to take the lapsed lease, got %+v (ok=%v)", taken, ok)
		}
	})

	t.Run("makes a released lease claimable at once", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		lease, ok := mustClaim(t, checkpoints, projection, "worker-1", Now)
		if !ok {
			t.Fatal("expected the first claim to be granted")
		}

		if err := checkpoints.Release(context.Background(), lease); err != nil {
			t.Fatalf("release: %v", err)
		}

		if _, ok := mustClaim(t, checkpoints, projection, "worker-2", Now); !ok {
			t.Fatal("expected the released lease to be claimable")
		}
	})

	t.Run("does nothing when releasing a lease somebody else holds", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		mustClaim(t, checkpoints, projection, "worker-1", Now)

		notTheirs := readmodels.Lease{Projection: projection, Owner: "worker-2", ExpiresAt: Now}
		if err := checkpoints.Release(context.Background(), notTheirs); err != nil {
			t.Fatalf("release: %v", err)
		}

		if _, ok := mustClaim(t, checkpoints, projection, "worker-3", Now); ok {
			t.Fatal("expected the lease still to be held by worker-1")
		}
	})

	// The two live in one row, and moving one must not move the other: a claim that reset the
	// position would rebuild a projection every time a worker restarted.
	t.Run("does not disturb the position when the lease moves", func(t *testing.T) {
		_, checkpoints := newStores(t)
		projection := newProjection()
		mustRecord(t, checkpoints, projection, 12)

		lease, ok := mustClaim(t, checkpoints, projection, "worker-1", Now)
		if !ok {
			t.Fatal("expected the claim to be granted")
		}
		if err := checkpoints.Release(context.Background(), lease); err != nil {
			t.Fatalf("release: %v", err)
		}

		if position := mustPosition(t, checkpoints, projection); position != 12 {
			t.Fatalf("expected the position untouched, got %d", position)
		}
	})
}

func mustPosition(t *testing.T, checkpoints readmodels.Store, projection string) int64 {
	t.Helper()
	position, err := checkpoints.PositionOf(context.Background(), projection)
	if err != nil {
		t.Fatalf("read the position of %s: %v", projection, err)
	}
	return position
}

func mustRecord(t *testing.T, checkpoints readmodels.Store, projection string, position int64) {
	t.Helper()
	if err := checkpoints.Record(context.Background(), projection, position); err != nil {
		t.Fatalf("record the position of %s: %v", projection, err)
	}
}

func mustClaim(
	t *testing.T,
	checkpoints readmodels.Store,
	projection string,
	owner string,
	now time.Time,
) (readmodels.Lease, bool) {
	t.Helper()
	lease, ok, err := checkpoints.Claim(context.Background(), projection, owner, now, aWhile)
	if err != nil {
		t.Fatalf("claim %s as %s: %v", projection, owner, err)
	}
	return lease, ok
}

// randomUUID is a version-4 UUID built from crypto/rand, for the same reason the event-store
// contract builds its own: Go has no UUID in its standard library and this suite adds no
// dependency to get one.
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

```go
package eventsourcing

import (
	"context"
	"errors"
	"reflect"
	"sync"
	"testing"
)

// InMemoryEventStore is a real implementation of EventStore backed by a
// map — not a mock. Because it satisfies the same EventStore interface a
// production adapter would, tests built on it exercise the real
// command-handling path with no casts or special-cased test doubles
// anywhere. It is guarded by a mutex so concurrent test goroutines can
// share one instance safely; single-goroutine use needs no locking at all.
type InMemoryEventStore struct {
	mu      sync.Mutex
	streams map[StreamID][]AccountEvent
}

// NewInMemoryEventStore returns an empty store.
func NewInMemoryEventStore() *InMemoryEventStore {
	return &InMemoryEventStore{streams: make(map[StreamID][]AccountEvent)}
}

func (s *InMemoryEventStore) Read(ctx context.Context, streamID StreamID) ([]AccountEvent, int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	events := s.streams[streamID]
	return events, len(events), nil
}

func (s *InMemoryEventStore) Append(ctx context.Context, streamID StreamID, events []AccountEvent, expectedVersion int) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	current := s.streams[streamID]
	if len(current) != expectedVersion {
		return ErrVersionConflict
	}
	s.streams[streamID] = append(append([]AccountEvent{}, current...), events...)
	return nil
}

// accountDecider adapts the concrete Decide/Evolve pair into the generic
// Decider bundle so it can be driven through MakeCommandHandler.
var accountDecider = Decider[AccountState, AccountCommand, AccountEvent]{
	InitialState: InitialState,
	Decide: func(cmd AccountCommand, state AccountState) Outcome[AccountEvent, string] {
		d := Decide(cmd, state)
		return Outcome[AccountEvent, string]{Accepted: d.Accepted, Events: d.Events, Reason: string(d.Reason)}
	},
	Evolve: Evolve,
}

func TestInMemoryEventStore(t *testing.T) {
	t.Run("persists a deposit so a later withdrawal sees the funds", func(t *testing.T) {
		store := NewInMemoryEventStore()
		handle := MakeCommandHandler(accountDecider, store, 3)
		streamID := StreamID("acc-1")
		ctx := context.Background()

		if _, err := handle(ctx, streamID, OpenAccount{Currency: "GBP"}); err != nil {
			t.Fatalf("Open: %v", err)
		}
		if _, err := handle(ctx, streamID, DepositMoney{Amount: money(10_000, "")}); err != nil {
			t.Fatalf("Deposit: %v", err)
		}

		result, err := handle(ctx, streamID, WithdrawMoney{Amount: money(6_000, "")})
		if err != nil {
			t.Fatalf("Withdraw: %v", err)
		}

		want := CommandResult[AccountEvent]{
			Success: true,
			Events:  []AccountEvent{MoneyWithdrawn{Amount: money(6_000, "")}},
		}
		if !reflect.DeepEqual(result, want) {
			t.Errorf("Withdraw result = %+v, want %+v", result, want)
		}
	})

	t.Run("rejects a concurrent append made against a stale expected version", func(t *testing.T) {
		store := NewInMemoryEventStore()
		ctx := context.Background()
		streamID := StreamID("acc-1")

		if err := store.Append(ctx, streamID, []AccountEvent{opened("")}, 0); err != nil {
			t.Fatalf("first append: %v", err)
		}

		err := store.Append(ctx, streamID, []AccountEvent{deposited(10_000)}, 0) // stale

		if !errors.Is(err, ErrVersionConflict) {
			t.Errorf("Append() error = %v, want ErrVersionConflict", err)
		}
	})
}
```

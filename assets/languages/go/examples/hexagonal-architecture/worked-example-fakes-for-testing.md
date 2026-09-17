```go
// gifting/testing/fakes/fake_pledge_persistence.go
package fakes

import (
	"context"
	"sync"

	"gifting/hexagon/application"
	"gifting/hexagon/domain"
)

// PledgePersistence is an in-memory application.PledgePersistence for
// use-case tests. It implements the real interface and exposes extra
// observation state — SavedEntities and OutboxEvents — for assertions. It
// lives outside the production hexagon, under testing/fakes/, alongside
// concrete production adapters but never among them. The mutex makes it
// safe under genuinely concurrent goroutines, which is what lets the
// optimistic-concurrency test below exercise a real race.
type PledgePersistence struct {
	mu            sync.Mutex
	store         map[domain.OccasionID]application.StoredOccasion
	SavedEntities []domain.Occasion
	OutboxEvents  []domain.PledgeRecorded
}

var _ application.PledgePersistence = (*PledgePersistence)(nil)

func NewPledgePersistence(initial ...domain.Occasion) *PledgePersistence {
	store := make(map[domain.OccasionID]application.StoredOccasion, len(initial))
	for _, occasion := range initial {
		store[occasion.ID] = application.StoredOccasion{Value: occasion, Version: 0}
	}
	return &PledgePersistence{store: store}
}

func (f *PledgePersistence) FindOccasionByID(ctx context.Context, id domain.OccasionID) (application.StoredOccasion, bool, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	stored, ok := f.store[id]
	return stored, ok, nil
}

func (f *PledgePersistence) SaveWithOutbox(ctx context.Context, occasion domain.Occasion, events []domain.PledgeRecorded, expectedVersion int) (application.SaveOutcome, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	current, ok := f.store[occasion.ID]
	if !ok || current.Version != expectedVersion {
		return application.Conflict, nil
	}
	f.store[occasion.ID] = application.StoredOccasion{Value: occasion, Version: expectedVersion + 1}
	f.SavedEntities = append(f.SavedEntities, occasion)
	f.OutboxEvents = append(f.OutboxEvents, events...)
	return application.Saved, nil
}

// gifting/testing/fakes/fake_pledge_projection.go

// PledgeProjection is an in-memory application.PledgeProjection. It is
// idempotent by event ID and exposes Records() for assertions.
type PledgeProjection struct {
	mu      sync.Mutex
	records map[domain.PledgeID]domain.PledgeRecorded
	order   []domain.PledgeID
}

var _ application.PledgeProjection = (*PledgeProjection)(nil)

func NewPledgeProjection() *PledgeProjection {
	return &PledgeProjection{records: make(map[domain.PledgeID]domain.PledgeRecorded)}
}

func (f *PledgeProjection) RecordFrom(ctx context.Context, event domain.PledgeRecorded) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if _, exists := f.records[event.ID]; !exists {
		f.records[event.ID] = event
		f.order = append(f.order, event.ID)
	}
	return nil
}

func (f *PledgeProjection) Records() []domain.PledgeRecorded {
	f.mu.Lock()
	defer f.mu.Unlock()
	records := make([]domain.PledgeRecorded, len(f.order))
	for i, id := range f.order {
		records[i] = f.records[id]
	}
	return records
}
```

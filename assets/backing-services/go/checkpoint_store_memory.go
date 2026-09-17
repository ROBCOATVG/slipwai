// Package checkpointstorememory holds the in-memory checkpoint adapter, on the same "connection"
// as the in-memory event store.
//
// Built from the store rather than standing alone, which is the rule every checkpoint adapter here
// follows: Record has to land in the same transaction as the view write it accounts for, and an
// adapter that does not share the store's unit of work cannot do that however carefully it is
// called.
//
// What it can prove: that a projection resumes from where it stopped, that one worker at a time
// advances it, that a lease expires, and that a batch which fails leaves both the view and the
// checkpoint where they were. What it cannot prove is a genuine race between two workers, because
// this one serialises them — `make test-integration` is where two connections contend for one
// lease.
package checkpointstorememory

import (
	"context"
	"time"

	"example.com/delivery-starter/adapters/driven/eventstorememory"
	"example.com/delivery-starter/application/ports/readmodels"
)

// Store is an in-memory readmodels.Store.
type Store struct {
	database *eventstorememory.Database
}

// New takes the event store's own database, so both adapters are inside one unit of work.
func New(store *eventstorememory.Store) *Store {
	return &Store{database: store.Database()}
}

func (s *Store) PositionOf(_ context.Context, projection string) (int64, error) {
	return s.database.PositionOf(projection), nil
}

func (s *Store) Record(_ context.Context, projection string, position int64) error {
	s.database.RecordPosition(projection, position)
	return nil
}

func (s *Store) Claim(
	_ context.Context,
	projection string,
	owner string,
	now time.Time,
	ttl time.Duration,
) (readmodels.Lease, bool, error) {
	if held, exists := s.database.Lease(projection); exists &&
		held.Owner != owner &&
		held.ExpiresAt.After(now) {
		return readmodels.Lease{}, false, nil
	}
	expiresAt := now.Add(ttl)
	s.database.SetLease(projection, eventstorememory.LeaseRow{Owner: owner, ExpiresAt: expiresAt})
	return readmodels.Lease{Projection: projection, Owner: owner, ExpiresAt: expiresAt}, true, nil
}

func (s *Store) Release(_ context.Context, lease readmodels.Lease) error {
	s.database.DeleteLease(lease.Projection, lease.Owner)
	return nil
}

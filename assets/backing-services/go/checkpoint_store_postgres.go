// Package checkpointstorepostgres holds the Postgres checkpoint adapter, on the event store's own
// transaction.
//
// Built from the store rather than from a pool, and that is the point: Record has to commit in the
// same transaction as the view rows it accounts for, so it has to run on the same connection. A
// second pool connection is a second transaction, and a checkpoint in its own transaction is a race
// with a number in it — either the view is written and the checkpoint is lost, or the checkpoint
// moves past rows that were rolled back.
//
// The claim is one statement. An INSERT ... ON CONFLICT DO UPDATE ... WHERE decides whether the
// lease is takeable and takes it in the same breath, so there is no window between reading who
// holds it and writing that you do. `make test-integration` is where two connections race for it
// for real, which is the one thing no single-writer store — an in-memory fake, a file-backed
// one — can prove.
package checkpointstorepostgres

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"

	"example.com/delivery-starter/adapters/driven/eventstorepostgres"
	"example.com/delivery-starter/application/ports/readmodels"
)

const positionOf = `SELECT position FROM projection_checkpoints WHERE projection = $1`

// updated_at moves with the position, so "is this projection stuck" is answerable from the table
// rather than from a log somewhere.
const record = `
  INSERT INTO projection_checkpoints (projection, position)
  VALUES ($1, $2)
  ON CONFLICT (projection) DO UPDATE
    SET position = EXCLUDED.position, updated_at = now()
`

// claim takes the lease when nobody holds it, when this owner already holds it (which is how a long
// catch-up renews), or when the holder's has lapsed. It refuses otherwise — and the refusal is the
// WHERE on the update, so the whole decision is one statement and cannot be split by another worker
// doing the same thing a microsecond later.
const claim = `
  INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
  VALUES ($1, 0, $2, $3)
  ON CONFLICT (projection) DO UPDATE
    SET lease_owner = EXCLUDED.lease_owner,
        lease_expires_at = EXCLUDED.lease_expires_at
    WHERE projection_checkpoints.lease_owner IS NULL
       OR projection_checkpoints.lease_owner = EXCLUDED.lease_owner
       OR projection_checkpoints.lease_expires_at <= $4
`

const release = `
  UPDATE projection_checkpoints
  SET lease_owner = NULL, lease_expires_at = NULL
  WHERE projection = $1 AND lease_owner = $2
`

// Store is a Postgres-backed readmodels.Store.
type Store struct {
	events *eventstorepostgres.Store
}

// New takes the event store, so both adapters run on one transaction when one is open.
func New(store *eventstorepostgres.Store) *Store {
	return &Store{events: store}
}

func (s *Store) PositionOf(ctx context.Context, projection string) (int64, error) {
	var position int64
	err := s.events.Executor(ctx).QueryRow(ctx, positionOf, projection).Scan(&position)
	if errors.Is(err, pgx.ErrNoRows) {
		return readmodels.FromTheBeginning, nil
	}
	if err != nil {
		return 0, fmt.Errorf("read the position of %s: %w", projection, err)
	}
	return position, nil
}

// Record does not commit: call it inside the store's unit of work, passing that unit of work's
// context, with the writes it accounts for. Outside one it runs on a pool connection of its own and
// commits alone, which is the mistake this comment exists to name.
func (s *Store) Record(ctx context.Context, projection string, position int64) error {
	if _, err := s.events.Executor(ctx).Exec(ctx, record, projection, position); err != nil {
		return fmt.Errorf("record the position of %s: %w", projection, err)
	}
	return nil
}

func (s *Store) Claim(
	ctx context.Context,
	projection string,
	owner string,
	now time.Time,
	ttl time.Duration,
) (readmodels.Lease, bool, error) {
	expiresAt := now.Add(ttl)
	taken := false
	err := s.events.InUnitOfWork(ctx, func(inside context.Context) error {
		tag, err := s.events.Executor(inside).Exec(inside, claim, projection, owner, expiresAt, now)
		taken = err == nil && tag.RowsAffected() != 0
		return err
	})
	if err != nil {
		return readmodels.Lease{}, false, fmt.Errorf("claim %s: %w", projection, err)
	}
	if !taken {
		return readmodels.Lease{}, false, nil
	}
	return readmodels.Lease{Projection: projection, Owner: owner, ExpiresAt: expiresAt}, true, nil
}

func (s *Store) Release(ctx context.Context, lease readmodels.Lease) error {
	err := s.events.InUnitOfWork(ctx, func(inside context.Context) error {
		_, err := s.events.Executor(inside).Exec(inside, release, lease.Projection, lease.Owner)
		return err
	})
	if err != nil {
		return fmt.Errorf("release %s: %w", lease.Projection, err)
	}
	return nil
}

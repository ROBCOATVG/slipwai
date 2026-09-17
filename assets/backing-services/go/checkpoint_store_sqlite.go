// Package checkpointstoresqlite holds the SQLite checkpoint adapter, on the event store's own
// connection.
//
// Built from the store rather than from a location, and that is the point: Record has to commit in
// the same transaction as the view rows it accounts for, so it has to be the same connection. Two
// adapters opening the same file are two connections and two transactions, and a checkpoint in its
// own transaction is a race with a number in it. The event store keeps one connection on purpose,
// so a statement sent to the database while a transaction holds it would wait for a transaction
// that is waiting for it — which is why every statement here runs on the store's Executor for the
// context it was given.
//
// The lease is claimed inside a transaction, which takes SQLite's single write lock, so the
// read-then-write is atomic without anything clever. What SQLite cannot do here is prove that two
// processes contend correctly, because it serialises them; `make test-integration` proves that
// against Postgres.
package checkpointstoresqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"example.com/delivery-starter/adapters/driven/eventstoresqlite"
	"example.com/delivery-starter/application/ports/readmodels"
)

const positionOf = `SELECT position FROM projection_checkpoints WHERE projection = ?`

// updated_at moves with the position, so "is this projection stuck" is answerable from the table
// rather than from a log somewhere.
const record = `
  INSERT INTO projection_checkpoints (projection, position)
  VALUES (?, ?)
  ON CONFLICT (projection) DO UPDATE
    SET position = excluded.position,
        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
`

// claim takes the lease when nobody holds it, when this owner already holds it (which is how a long
// catch-up renews), or when the holder's lease has lapsed. It refuses otherwise — and the refusal
// is the WHERE on the update, so the whole decision is one statement and cannot be split.
const claim = `
  INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
  VALUES (?, 0, ?, ?)
  ON CONFLICT (projection) DO UPDATE
    SET lease_owner = excluded.lease_owner,
        lease_expires_at = excluded.lease_expires_at
    WHERE projection_checkpoints.lease_owner IS NULL
       OR projection_checkpoints.lease_owner = excluded.lease_owner
       OR projection_checkpoints.lease_expires_at <= ?
`

const release = `
  UPDATE projection_checkpoints
  SET lease_owner = NULL, lease_expires_at = NULL
  WHERE projection = ? AND lease_owner = ?
`

// asText is a fixed-width UTC instant, because SQLite compares these as strings.
//
// Same width, same zone, always — that is what makes `lease_expires_at <= ?` a chronological
// comparison rather than an alphabetical one that is right until an offset or a shorter fraction
// turns up. Postgres has timestamptz and needs none of this; the adapter is where the difference
// stops.
func asText(instant time.Time) string {
	return instant.UTC().Format("2006-01-02T15:04:05.000000000Z")
}

// Store is a SQLite-backed readmodels.Store.
type Store struct {
	events *eventstoresqlite.Store
}

// New takes the event store, so both adapters run on one connection and inside one unit of work.
func New(store *eventstoresqlite.Store) *Store {
	return &Store{events: store}
}

func (s *Store) PositionOf(ctx context.Context, projection string) (int64, error) {
	var position int64
	err := s.events.Executor(ctx).QueryRowContext(ctx, positionOf, projection).Scan(&position)
	if errors.Is(err, sql.ErrNoRows) {
		return readmodels.FromTheBeginning, nil
	}
	if err != nil {
		return 0, fmt.Errorf("read the position of %s: %w", projection, err)
	}
	return position, nil
}

// Record does not commit: call it inside the store's unit of work, passing that unit of work's
// context, with the writes it accounts for. Outside one it commits on its own, which is the mistake
// this comment exists to name.
func (s *Store) Record(ctx context.Context, projection string, position int64) error {
	if _, err := s.events.Executor(ctx).ExecContext(ctx, record, projection, position); err != nil {
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
		result, err := s.events.Executor(inside).ExecContext(
			inside, claim, projection, owner, asText(expiresAt), asText(now),
		)
		if err != nil {
			return err
		}
		affected, err := result.RowsAffected()
		taken = affected != 0
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
		_, err := s.events.Executor(inside).ExecContext(
			inside, release, lease.Projection, lease.Owner,
		)
		return err
	})
	if err != nil {
		return fmt.Errorf("release %s: %w", lease.Projection, err)
	}
	return nil
}

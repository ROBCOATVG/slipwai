```go
package eventsourcing

import (
	"context"
	"errors"
	"fmt"
)

// ErrProjectionGap reports that the next event to apply is not immediately
// after the checkpoint's position — some position in between is missing,
// so applying now would silently skip it.
var ErrProjectionGap = errors.New("projection gap: retry after the missing position")

// Tx is the minimal transactional context this catch-up step needs: enough
// to acquire a lease and to read and write both a checkpoint and a view,
// all atomically. A real adapter backs it with a specific store's
// transaction (SQL, etc.); this stays at the port level, the same
// abstraction the illustrative pseudocode was written at.
type Tx interface {
	AcquireExclusiveProjectionLease(ctx context.Context, projectionName string) error
	LoadCheckpoint(ctx context.Context, projectionName string) (appliedThrough int64, err error)
	SaveCheckpoint(ctx context.Context, projectionName string, position int64) error
	LoadBalanceView(ctx context.Context, streamID StreamID) (BalanceView, error)
	UpsertBalanceView(ctx context.Context, view BalanceView) error
}

// TxRunner runs fn inside one transaction, committing on a nil return and
// rolling back otherwise.
type TxRunner interface {
	WithTransaction(ctx context.Context, fn func(tx Tx) error) error
}

// ApplyCheckpointed applies one envelope and advances the projection's
// checkpoint atomically: acquire an exclusive lease so no other worker
// races this one, skip exact redelivery, fail loudly on a detected gap
// rather than silently skipping it, fold the event into the view, and
// persist the view and the checkpoint together in the same transaction.
func ApplyCheckpointed(ctx context.Context, runner TxRunner, projectionName string, envelope AccountProjectionEnvelope) error {
	return runner.WithTransaction(ctx, func(tx Tx) error {
		if err := tx.AcquireExclusiveProjectionLease(ctx, projectionName); err != nil {
			return err
		}

		appliedThrough, err := tx.LoadCheckpoint(ctx, projectionName)
		if err != nil {
			return err
		}
		if envelope.GlobalPosition <= appliedThrough {
			return nil // exact redelivery
		}
		if envelope.GlobalPosition != appliedThrough+1 {
			return fmt.Errorf("%w: at position %d, applied through %d", ErrProjectionGap, envelope.GlobalPosition, appliedThrough)
		}

		current, err := tx.LoadBalanceView(ctx, envelope.StreamID)
		if err != nil {
			return err
		}
		next, err := Apply(current, envelope)
		if err != nil {
			return err
		}
		if err := tx.UpsertBalanceView(ctx, next); err != nil {
			return err
		}
		return tx.SaveCheckpoint(ctx, projectionName, envelope.GlobalPosition) // same transaction
	})
}
```

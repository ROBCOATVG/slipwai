// Package projections holds the catch-up runner: how an async read model is maintained, and how it
// is rebuilt.
//
// Two verbs over the two ports, and no I/O of its own — which is why it is here beside the
// application rather than under adapters, and why its tests need no database.
//
//	advance, err := projections.CatchUp(ctx, store, checkpoints, view, projections.Runner{
//		Owner: "worker-1",
//		Clock: time.Now,
//	})
//
// CatchUp is one pass: it reads the log from the projection's checkpoint, applies it in batches,
// and advances the checkpoint inside the same transaction as the rows it derived. CatchUpEach is that
// pass over every projection at once, and Ticker in this package is what loops over it —
// blocking like everything long-running in the standard library, ended by the context `cmd/serve`
// cancels. A project with only live and inline read models starts nothing and runs nothing here.
//
// Rebuild is the same pass from zero, with the view emptied first. It is what makes a read model
// disposable: a projection with a bug is fixed by changing the fold and running this, not by
// patching rows. It holds the lease across the empty *and* the re-fold, so a worker cannot catch up
// into a half-empty view.
//
// # Why exactly-once needs nothing else here
//
// The checkpoint moves in the view's own transaction, so the pair is atomic: a crash before the
// commit leaves both untouched, and the next pass reads the same batch again. Nothing is applied
// twice and nothing is skipped, and there is no idempotency key to get wrong.
//
// That guarantee is the transaction's, not this file's, and it is worth knowing exactly where it
// stops. A projection whose rows are not in the same database as the checkpoint — an HTTP search
// index, a cache, a file — cannot join that transaction, and for those the fold has to be
// idempotent on GlobalPosition instead: record the position with the row and ignore an event at or
// below what the row already holds. The lease reduces how often that matters; it never removes the
// need.
//
// # Why a lease and not a lock
//
// Exactly one worker should advance a projection, and a lease with an expiry is how that survives
// the worker dying. What it is not is the thing that makes the work happen once — the transaction
// above is. A projection is a fold and folds are cheap; the lease is there to stop every replica
// burning the same log, not to hold the system together.
package projections

import (
	"context"
	"errors"
	"fmt"
	"time"

	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
)

// DefaultLease is how long a claim is good for. Long enough that a slow batch does not lose it,
// short enough that a dead worker's projection resumes within a stand-up rather than a support
// call.
const DefaultLease = 30 * time.Second

// DefaultBatchSize is how many events one transaction applies. A batch is one transaction, so this
// trades how much work a crash repeats against how long a single transaction holds its locks.
const DefaultBatchSize = 500

// Runner is what one pass needs to know beyond the ports themselves.
//
// Clock is a function, because a pass long enough to need its lease renewed needs the time again —
// which an instant passed in cannot give it. Everywhere else in this project an instant is a typed
// input; here the input is the clock itself, and a test hands over a fixed one.
type Runner struct {
	Owner     string
	Clock     func() time.Time
	TTL       time.Duration
	BatchSize int
}

func (r Runner) ttl() time.Duration {
	if r.TTL == 0 {
		return DefaultLease
	}
	return r.TTL
}

func (r Runner) batchSize() int {
	if r.BatchSize == 0 {
		return DefaultBatchSize
	}
	return r.BatchSize
}

// Advance is what one pass did.
//
// Leased is separate from Applied on purpose: "nothing to apply" and "somebody else is already
// applying it" are both a quiet zero, and a caller that cannot tell them apart will read the first
// as an empty log and the second as a finished rebuild.
type Advance struct {
	Applied int
	Leased  bool
}

// CatchUp applies everything the log has that this projection has not, once.
//
// It returns without doing anything if another worker holds the lease — that is the ordinary case
// for every replica but one, and not a failure.
func CatchUp(
	ctx context.Context,
	store events.Store,
	checkpoints readmodels.Store,
	projection readmodels.Projection,
	runner Runner,
) (Advance, error) {
	lease, ok, err := checkpoints.Claim(
		ctx, projection.Name(), runner.Owner, runner.Clock(), runner.ttl(),
	)
	if err != nil || !ok {
		return Advance{}, err
	}
	defer func() { _ = checkpoints.Release(ctx, lease) }()

	applied, err := applyFromTheCheckpoint(ctx, store, checkpoints, projection, lease, runner)
	return Advance{Applied: applied, Leased: true}, err
}

// CatchUpEach applies everything the log has to every projection given, which is what a ticker
// calls.
//
// No projection's failure hides another's. Each is attempted, the advances come back by name, and a
// pass with failures returns one error joining all of them — so whoever logs it sees every one, the
// next pass tries again, and a projection whose fold is broken does not quietly starve every
// projection after it in the slice.
func CatchUpEach(
	ctx context.Context,
	store events.Store,
	checkpoints readmodels.Store,
	projections []readmodels.Projection,
	runner Runner,
) (map[string]Advance, error) {
	advances := make(map[string]Advance, len(projections))
	var failures []error
	for _, projection := range projections {
		advance, err := CatchUp(ctx, store, checkpoints, projection, runner)
		if err != nil {
			failures = append(failures, fmt.Errorf("%s: %w", projection.Name(), err))
			continue
		}
		advances[projection.Name()] = advance
	}
	return advances, errors.Join(failures...)
}

// Rebuild empties the view, puts its checkpoint back to zero, and folds the whole log into it
// again.
//
// The reset and the checkpoint go back together, in one transaction, because a view emptied without
// its checkpoint is a permanently empty view and a checkpoint reset without its view is a doubled
// one.
func Rebuild(
	ctx context.Context,
	store events.Store,
	checkpoints readmodels.Store,
	projection readmodels.Projection,
	runner Runner,
) (Advance, error) {
	lease, ok, err := checkpoints.Claim(
		ctx, projection.Name(), runner.Owner, runner.Clock(), runner.ttl(),
	)
	if err != nil || !ok {
		return Advance{}, err
	}
	defer func() { _ = checkpoints.Release(ctx, lease) }()

	err = store.InUnitOfWork(ctx, func(inside context.Context) error {
		if err := projection.Reset(inside); err != nil {
			return err
		}
		return checkpoints.Record(inside, projection.Name(), readmodels.FromTheBeginning)
	})
	if err != nil {
		return Advance{Leased: true}, err
	}

	applied, err := applyFromTheCheckpoint(ctx, store, checkpoints, projection, lease, runner)
	return Advance{Applied: applied, Leased: true}, err
}

// applyFromTheCheckpoint applies batch after batch until the log runs out, holding lease
// throughout.
//
// The checkpoint is re-read each time round rather than tracked in a local, so a batch that rolled
// back is read again instead of being skipped by a variable the database never agreed with.
func applyFromTheCheckpoint(
	ctx context.Context,
	store events.Store,
	checkpoints readmodels.Store,
	projection readmodels.Projection,
	lease readmodels.Lease,
	runner Runner,
) (int, error) {
	applied := 0
	for {
		position, err := checkpoints.PositionOf(ctx, projection.Name())
		if err != nil {
			return applied, err
		}

		batch, err := take(ctx, store, position, runner.batchSize())
		if err != nil || len(batch) == 0 {
			return applied, err
		}

		err = store.InUnitOfWork(ctx, func(inside context.Context) error {
			if err := projection.Apply(inside, batch); err != nil {
				return err
			}
			// The next position, not the last one applied: what PositionOf promises is where to
			// resume, and an off-by-one here re-applies one event forever.
			last := batch[len(batch)-1].GlobalPosition
			return checkpoints.Record(inside, projection.Name(), last+1)
		})
		if err != nil {
			return applied, err
		}
		applied += len(batch)

		if len(batch) < runner.batchSize() {
			return applied, nil
		}
		_, held, err := checkpoints.Claim(
			ctx, lease.Projection, lease.Owner, runner.Clock(), runner.ttl(),
		)
		if err != nil || !held {
			// The lease lapsed mid-pass and somebody else took it: stop where the checkpoint is,
			// which the new owner will read. Losing a lease is not an error — it is a slow pass.
			return applied, err
		}
	}
}

// errEnough stops a replay once a batch is full. ReadAll takes a visitor rather than returning a
// slice, so "enough" has to travel as an error and be swallowed here.
var errEnough = errStop{}

type errStop struct{}

func (errStop) Error() string { return "enough" }

// take is the first count events of a replay, and no more of the log read than that.
func take(
	ctx context.Context,
	store events.Store,
	fromPosition int64,
	count int,
) ([]events.CommittedEvent, error) {
	batch := make([]events.CommittedEvent, 0, count)
	err := store.ReadAll(ctx, fromPosition, func(event events.CommittedEvent) error {
		batch = append(batch, event)
		if len(batch) == count {
			return errEnough
		}
		return nil
	})
	if err != nil && err != errEnough {
		return nil, err
	}
	return batch, nil
}

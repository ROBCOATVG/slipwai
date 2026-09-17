// Package readmodels holds the read-side port: where a projection has got to, and who is allowed
// to advance it.
//
// The write side of this project arrives finished — a port, its adapters, one contract suite.
// This is the other half, and it exists because the half that was missing is the half that gets
// invented badly: a read model folded in the request because that was the only read path already
// built.
//
// Two ports, and they are deliberately separate:
//
//   - Store — how far a named projection has consumed the log, and an exclusive lease so exactly
//     one worker advances it. This is infrastructure, and it ships with adapters.
//   - Projection — what a project's own view *is*: a fold with somewhere to put the result. This
//     ships as an interface only, because the rows are the project's.
//
// A checkpoint is only a checkpoint if it commits with the rows it describes. Everything here is
// shaped by that one sentence: Record never commits on its own, and the runner in the projections
// package calls it inside events.Store.InUnitOfWork, so the position and the view move together or
// neither moves. Record it separately and you have chosen, without noticing, between losing
// updates and applying them twice.
//
// docs/event-model/README.md says which of the three lifecycles — live, inline, async — a slice's
// read model uses, and `make check-model` makes a slice say so before it can be planned. This file
// is what async is built from, and InUnitOfWork is what inline is built from.
package readmodels

import (
	"context"
	"time"

	"example.com/delivery-starter/application/ports/events"
)

// FromTheBeginning is where a projection that has never run starts. The position is the *next*
// global position to apply, so zero means "the whole log", and a rebuild is a Record of zero
// followed by a catch-up.
const FromTheBeginning int64 = 0

// Lease is the right to advance one projection, held by one worker until it expires.
//
// An expiry rather than a lock, because the failure to survive is a worker that dies holding it: a
// lock nothing releases is a projection that never advances again, and the first anybody hears of
// it is a stale view. A lease that lapses is a projection that resumes on its own.
//
// The lease is an efficiency measure, not a correctness one. Two workers holding it at once would
// each apply events inside InUnitOfWork, and the checkpoint moving in the same transaction is what
// makes the loser's work a no-op rather than a duplicate. The lease is what stops that being the
// normal case — see the projections package.
type Lease struct {
	Projection string
	Owner      string
	ExpiresAt  time.Time
}

// Store is where each projection has got to, and who currently owns advancing it.
//
// Every adapter is built from the event store it follows, deliberately: Record has to land in the
// same transaction as the view write, and two adapters on two connections cannot do that however
// carefully they are called.
type Store interface {
	// PositionOf is the next global position this projection has not yet applied.
	//
	// FromTheBeginning for a projection nothing has recorded — an unknown projection is one that
	// has consumed nothing, not an error, because a rebuild has to be expressible without a
	// special case.
	PositionOf(ctx context.Context, projection string) (int64, error)

	// Record moves the checkpoint. It does not commit — the caller's InUnitOfWork does.
	//
	// Call it inside the same unit of work as the writes it accounts for, always, passing that
	// unit of work's context. It is safe to call outside one, and then it commits on its own,
	// which is exactly the mistake this comment exists to name.
	Record(ctx context.Context, projection string, position int64) error

	// Claim takes or renews the lease, and reports ok=false if somebody else holds an unexpired
	// one.
	//
	// now is passed in rather than read from a clock, for the reason every instant in this
	// project is: a test that cannot choose the time cannot test expiry without sleeping. The
	// owner already holding the lease always succeeds, which is how a long catch-up renews.
	Claim(
		ctx context.Context,
		projection string,
		owner string,
		now time.Time,
		ttl time.Duration,
	) (lease Lease, ok bool, err error)

	// Release gives the lease up early. A lease held by somebody else is left alone. Releasing is
	// politeness, not correctness: not releasing costs the next worker one ttl.
	Release(ctx context.Context, lease Lease) error
}

// Projection is a read model that is maintained rather than folded per query — inline or async.
//
// Three requirements, and the third is the one usually missed:
//
//   - Name identifies its checkpoint. Stable for the life of the projection: renaming it silently
//     starts a second projection at position zero.
//   - Apply folds a batch into whatever the view is kept in. Under async it is called inside
//     events.Store.InUnitOfWork and given that unit of work's context, so it must write through
//     it and must not commit; under inline the append's transaction is the one it joins.
//   - Reset empties the view. Without it the projection is not disposable, and a projection that
//     cannot be rebuilt is a second source of truth — which is the whole thing an event log exists
//     to avoid.
//
// Every row a projection writes is derived: it comes from the events, and nothing else. A column
// the projection alone knows — a doneAt the worker stamps when it processes the row — cannot
// survive Reset, and finding that out during an incident is how a rebuild becomes data loss. Where
// a value like that is needed, it belongs in an event.
type Projection interface {
	Name() string
	Apply(ctx context.Context, batch []events.CommittedEvent) error
	Reset(ctx context.Context) error
}

package projections

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strconv"
	"time"

	"example.com/delivery-starter/application/ports/events"
	"example.com/delivery-starter/application/ports/readmodels"
)

// DefaultEvery is how long between passes when nothing says otherwise.
//
// This is the lag this project accepts on its async views — the whole cost of that answer, in one
// number — so it is an option rather than a constant, and PROJECTIONS_EVERY_MS is where a deployment
// turns it down.
const DefaultEvery = time.Second

// Ticker is what turns a pass into a subscription: the loop, and the context that ends it.
//
// Go has no framework to own a loop, so this is the one thing the other backends get from theirs. It
// lives in this package rather than under adapters/driving/ for the reason a Fastify plugin and a
// FastAPI lifespan do in the other backends: it ships with the read side, and a project can have a read
// side and no transport at all, while everything under adapters/driving belongs to a transport and goes
// when the transport does.
//
// Run blocks, which is the shape of every long-running thing in the standard library
// (http.Server.ListenAndServe, and so on). The composition root starts it beside the server and cancels
// the same context, so Ctrl-C and SIGTERM stop the passes:
//
//	store, err := eventstorepostgres.Open(ctx, os.Getenv("DATABASE_URL"))
//	checkpoints := checkpointstorepostgres.New(store)
//	go func() {
//		ticker := projections.Ticker{OnFailure: func(err error) {
//			slog.Error("a projection pass failed", "err", err)
//		}}
//		if err := ticker.Run(ctx, store, checkpoints, views); err != nil {
//			slog.Error("the projection ticker stopped", "err", err)
//		}
//	}()
//
// A project whose read models are all live or inline starts nothing, and nothing runs.
type Ticker struct {
	// Every is the pause between passes. Zero reads PROJECTIONS_EVERY_MS, and then DefaultEvery.
	Every time.Duration

	// Owner is this process's identity as a lease holder. Empty generates one per call: two replicas
	// sharing a name would be one owner as far as the lease is concerned, and the holder of a lease
	// may always renew it — so a shared name is two workers both certain they hold it.
	Owner string

	// Clock is what the lease's expiry is measured against. Nil is time.Now, and a test hands over
	// one it controls.
	Clock func() time.Time

	// OnFailure is told about a pass that failed. Nil ignores it, which is the right default for a
	// package that must not choose a logger for the project — but a project that starts this without
	// passing one has decided not to hear about a projection falling behind.
	OnFailure func(error)
}

// Run keeps every projection caught up until ctx is cancelled.
//
// It returns nil on cancellation, because a ticker stopped on purpose has not failed. A failed pass
// does not end the loop either: a projection whose fold is broken would otherwise take the process
// down with it, and a stale view is the lesser failure. The pass is reported through OnFailure and
// tried again on the next tick.
func (t Ticker) Run(
	ctx context.Context,
	store events.Store,
	checkpoints readmodels.Store,
	views []readmodels.Projection,
) error {
	if len(views) == 0 {
		return nil
	}
	runner := Runner{Owner: t.owner(), Clock: t.clock()}

	// A timer reset after each pass rather than a Ticker: the pause is measured from the *end* of a
	// pass, so a pass slower than the interval cannot have a second pass queue up behind it. Skipping
	// costs nothing, because the checkpoint means the next pass resumes exactly where this one
	// stopped.
	pause := t.every()
	for {
		if _, err := CatchUpEach(ctx, store, checkpoints, views, runner); err != nil {
			if errors.Is(err, context.Canceled) {
				return nil
			}
			if t.OnFailure != nil {
				t.OnFailure(err)
			}
		}
		select {
		case <-ctx.Done():
			return nil
		case <-time.After(pause):
		}
	}
}

func (t Ticker) owner() string {
	if t.Owner != "" {
		return t.Owner
	}
	// This process, for as long as it runs: the pid, and when it started. Not the hostname — two
	// replicas in one pod share it, and a pid on its own repeats across containers, so either alone
	// is a name two workers can hold at once. The holder of a lease may always renew it, so two
	// workers sharing a name are two workers each certain it is theirs.
	return fmt.Sprintf("worker-%d-%d", os.Getpid(), time.Now().UnixNano())
}

func (t Ticker) clock() func() time.Time {
	if t.Clock != nil {
		return t.Clock
	}
	return time.Now
}

func (t Ticker) every() time.Duration {
	if t.Every > 0 {
		return t.Every
	}
	if configured, err := strconv.Atoi(os.Getenv("PROJECTIONS_EVERY_MS")); err == nil && configured > 0 {
		return time.Duration(configured) * time.Millisecond
	}
	return DefaultEvery
}

```go
package eventsourcing

import (
	"context"
	"errors"
)

// EventStore is the generic storage port a Decider-based command handler
// reads from and appends to, parameterised over that Decider's event type.
type EventStore[Event any] interface {
	Read(ctx context.Context, streamID StreamID) (events []Event, version int, err error)
	Append(ctx context.Context, streamID StreamID, events []Event, expectedVersion int) error
}

// ErrVersionConflict is returned by Append when the stream has moved on
// since the caller last read it.
var ErrVersionConflict = errors.New("event store: version conflict")

// CommandResult is the outcome of handling a command: success with the
// events that were appended, or failure with a reason.
type CommandResult[Event any] struct {
	Success bool
	Events  []Event
	Reason  string
}

// MakeCommandHandler builds a command handler for the given Decider and
// EventStore. On a version conflict — the stream moved under us — it
// reloads the stream and re-decides against the fresh state, up to
// maxAttempts times (3 by default), rather than failing on the first race.
func MakeCommandHandler[State any, Command any, Event any](
	decider Decider[State, Command, Event],
	store EventStore[Event],
	maxAttempts int,
) func(ctx context.Context, streamID StreamID, cmd Command) (CommandResult[Event], error) {
	if maxAttempts <= 0 {
		maxAttempts = 3
	}

	return func(ctx context.Context, streamID StreamID, cmd Command) (CommandResult[Event], error) {
		for attempt := 0; attempt < maxAttempts; attempt++ {
			events, version, err := store.Read(ctx, streamID) // load
			if err != nil {
				return CommandResult[Event]{}, err
			}

			state, err := Rehydrate(decider, events) // rehydrate (pure)
			if err != nil {
				return CommandResult[Event]{}, err
			}

			decision := decider.Decide(cmd, state) // decide (pure)
			if !decision.Accepted {
				return CommandResult[Event]{Success: false, Reason: decision.Reason}, nil
			}

			err = store.Append(ctx, streamID, decision.Events, version)
			if err == nil {
				return CommandResult[Event]{Success: true, Events: decision.Events}, nil
			}
			if !errors.Is(err, ErrVersionConflict) {
				return CommandResult[Event]{}, err
			}
			// version conflict: the stream moved under us — loop to reload
			// and re-decide against fresh state.
		}
		return CommandResult[Event]{Success: false, Reason: "concurrent-modification"}, nil
	}
}
```

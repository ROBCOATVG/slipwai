```go
package eventsourcing

import (
	"context"
	"errors"
)

// CommandResult is the outcome of handling a command against a stream:
// success with the events that were appended, or failure with a reason.
type CommandResult struct {
	Success bool
	Events  []AccountEvent
	Reason  string
}

// HandleCommand is the bare use-case shape: load the stream, rehydrate state
// by folding, decide, then append with optimistic concurrency. It does not
// retry on a version conflict — see the retry-loop example for that.
func HandleCommand(ctx context.Context, store EventStore, streamID StreamID, cmd AccountCommand) (CommandResult, error) {
	// 1. LOAD the stream's events (and the version we read at).
	events, version, err := store.Read(ctx, streamID)
	if err != nil {
		return CommandResult{}, err
	}

	// 2. REHYDRATE current state by folding — pure.
	state := InitialState
	for _, evt := range events {
		state, err = Evolve(state, evt)
		if err != nil {
			return CommandResult{}, err
		}
	}

	// 3. DECIDE — pure business logic.
	decision := Decide(cmd, state)
	if !decision.Accepted {
		return CommandResult{Success: false, Reason: string(decision.Reason)}, nil
	}

	// 4. APPEND the new events, asserting the stream has not moved since we
	// read it.
	if err := store.Append(ctx, streamID, decision.Events, version); err != nil {
		if errors.Is(err, ErrVersionConflict) {
			return CommandResult{Success: false, Reason: "concurrent-modification"}, nil
		}
		return CommandResult{}, err
	}

	return CommandResult{Success: true, Events: decision.Events}, nil
}
```

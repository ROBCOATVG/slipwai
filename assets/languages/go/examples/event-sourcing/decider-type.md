```go
package eventsourcing

// Decider bundles the pieces needed to evolve and decide against one
// aggregate: its seed state, its pure decision function, its pure fold
// function, and an optional predicate for when the stream is done evolving.
// Go has no separate "type" vs "value" split the way TypeScript does here,
// so the bundle is a struct of function fields, parameterised over the
// aggregate's State, Command and Event types.
type Decider[State any, Command any, Event any] struct {
	InitialState State
	Decide       func(cmd Command, state State) Outcome[Event, string]
	// Evolve returns an error rather than a bare State when a known event
	// cannot legally follow the current state — corrupt history is a real
	// operational occurrence a caller must handle, not a value to paper
	// over.
	Evolve func(state State, event Event) (State, error)
	// IsTerminal reports whether state can accept no further commands. Nil
	// means the stream never terminates.
	IsTerminal func(state State) bool
}
```

```go
package eventsourcing

// Rehydrate rebuilds any Decider's current state by folding Evolve over
// past events, starting from InitialState. It stops and surfaces the error
// as soon as any event turns out not to be a legal transition — corrupt
// history is reported to the caller rather than silently continuing the
// fold on bad data.
func Rehydrate[State any, Command any, Event any](decider Decider[State, Command, Event], events []Event) (State, error) {
	state := decider.InitialState
	for _, event := range events {
		var err error
		state, err = decider.Evolve(state, event)
		if err != nil {
			return state, err
		}
	}
	return state, nil
}
```

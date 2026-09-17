```go
// Rehydrate rebuilds current state by folding Evolve over past events.
// Evolve returns an error when a known event cannot follow the current
// state (corrupt history) — Rehydrate stops and surfaces that error
// rather than silently returning a partially-folded state.
func Rehydrate(events []AccountEvent) (AccountState, error) {
	state := InitialState
	for _, evt := range events {
		var err error
		state, err = Evolve(state, evt)
		if err != nil {
			return AccountState{}, err
		}
	}
	return state, nil
}
```

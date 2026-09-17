```go
package ddd

// Workout keeps its child collection unexported so the aggregate root
// controls all mutation. Go has no read-only slice type, so callers only
// ever see a defensive copy through Exercises().
type Workout struct {
	ID           WorkoutID
	exercises    []Exercise
	MaxExercises int
}

// Exercises returns a copy of the child collection: callers can inspect it,
// but mutating the returned slice cannot affect the aggregate's own state.
func (w Workout) Exercises() []Exercise {
	out := make([]Exercise, len(w.exercises))
	copy(out, w.exercises)
	return out
}
```

```go
package ddd

// RemoveExercise (WRONG) leaks internals — the caller must obtain the
// Exercise object somehow.
func RemoveExercise(workout Workout, exercise Exercise) Workout {
	panic("wrong shape — see the version below")
}

type RemoveExerciseOutcome int

const (
	ExerciseRemoved RemoveExerciseOutcome = iota
	ExerciseNotFound
)

type RemoveExerciseResult struct {
	Outcome RemoveExerciseOutcome
	Workout Workout
}

// RemoveExercise (RIGHT) preserves the boundary — the caller only knows the
// ID, and the aggregate root looks the child up itself.
func RemoveExercise(workout Workout, exerciseID ExerciseID) RemoveExerciseResult {
	found := false
	remaining := make([]Exercise, 0, len(workout.Exercises))
	for _, e := range workout.Exercises {
		if e.ID == exerciseID {
			found = true
			continue
		}
		remaining = append(remaining, e)
	}
	if !found {
		return RemoveExerciseResult{Outcome: ExerciseNotFound}
	}
	workout.Exercises = remaining
	return RemoveExerciseResult{Outcome: ExerciseRemoved, Workout: workout}
}
```

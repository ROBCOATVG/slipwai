```go
package ddd

// AddExercise (WRONG) accepts an externally constructed child — the root
// can't enforce its own creation rules.
func AddExercise(workout Workout, exercise Exercise) Workout {
	panic("wrong shape — see the version below")
}

type AddExerciseOutcome int

const (
	ExerciseAdded AddExerciseOutcome = iota
	MaxExercisesReached
)

type AddExerciseResult struct {
	Outcome AddExerciseOutcome
	Workout Workout
}

// AddExercise (RIGHT) lets the root create the child itself, enforcing the
// max-exercises invariant.
func AddExercise(workout Workout, exerciseID ExerciseID, params NewExerciseParams) AddExerciseResult {
	if len(workout.Exercises) >= workout.MaxExercises {
		return AddExerciseResult{Outcome: MaxExercisesReached}
	}

	exercise := Exercise{
		ID:         exerciseID,
		WorkoutID:  workout.ID,
		Name:       params.Name,
		TargetSets: params.TargetSets,
		TargetReps: params.TargetReps,
	}

	next := make([]Exercise, len(workout.Exercises), len(workout.Exercises)+1)
	copy(next, workout.Exercises)
	next = append(next, exercise)
	workout.Exercises = next
	return AddExerciseResult{Outcome: ExerciseAdded, Workout: workout}
}
```

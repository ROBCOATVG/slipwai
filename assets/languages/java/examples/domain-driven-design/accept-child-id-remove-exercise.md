```java
// Leaks the internals: the caller has to obtain an Exercise from somewhere, which means reaching inside
// the aggregate to get it.
public Workout removeExercise(Exercise exercise) { }

// The boundary holds: the caller names the child by id, and "no such exercise" is an outcome rather than
// a null.
public RemoveExerciseResult removeExercise(ExerciseId exerciseId) {
    if (exercises.stream().noneMatch(exercise -> exercise.id().equals(exerciseId))) {
        return new RemoveExerciseResult.Refused("exercise-not-found");
    }
    List<Exercise> remaining = exercises.stream()
            .filter(exercise -> !exercise.id().equals(exerciseId))
            .toList();
    return new RemoveExerciseResult.Removed(new Workout(id, remaining, maxExercises));
}
```

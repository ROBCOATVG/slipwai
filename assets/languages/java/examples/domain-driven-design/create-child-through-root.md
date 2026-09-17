```java
// The child arrives fully formed, so the root cannot enforce anything about how it was made.
public Workout addExercise(Exercise exercise) { }

// The root creates the child from parameters, which is what lets it enforce the limit and stamp the
// relationship. A caller cannot construct an Exercise that belongs to a different workout.
public AddExerciseResult addExercise(ExerciseId exerciseId, NewExerciseParams params) {
    if (exercises.size() >= maxExercises) {
        return new AddExerciseResult.Refused("max-exercises-reached");
    }
    List<Exercise> updated = new ArrayList<>(exercises);
    updated.add(new Exercise(exerciseId, id, params.name(), params.repetitions()));
    return new AddExerciseResult.Added(new Workout(id, updated, maxExercises));
}
```

```java
/**
 * `List.copyOf` in the constructor is what makes the collection genuinely unmodifiable: the returned list
 * rejects `add`, and it is a copy, so the caller's list changing later does not change this aggregate.
 *
 * <p>A bare `List<Exercise>` field would be inspectable *and* mutable through whatever reference the
 * caller kept — which is the same as having no invariant at all.
 */
public record Workout(WorkoutId id, List<Exercise> exercises, int maxExercises) {

    public Workout {
        exercises = List.copyOf(exercises);
    }
}
```

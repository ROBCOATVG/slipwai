```typescript
// ❌ Externally constructed child — root can't enforce creation rules
const addExercise = (workout: Workout, exercise: Exercise): Workout => ...;

// ✅ Root creates the child — enforces max-exercises invariant
const addExercise = (
  workout: Workout,
  exerciseId: ExerciseId,
  params: NewExerciseParams,
): AddExerciseResult => {
  if (workout.exercises.length >= workout.maxExercises) {
    return { success: false, reason: 'max-exercises-reached' };
  }
  const exercise: Exercise = {
    id: exerciseId,
    workoutId: workout.id,
    ...params,
  };
  return { success: true, workout: { ...workout, exercises: [...workout.exercises, exercise] } };
};
```

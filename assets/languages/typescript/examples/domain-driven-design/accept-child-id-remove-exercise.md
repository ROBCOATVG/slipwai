```typescript
// ❌ Leaks internals — caller must obtain the Exercise object somehow
const removeExercise = (workout: Workout, exercise: Exercise): Workout => ...;

// ✅ Boundary preserved — caller only knows the ID
const removeExercise = (workout: Workout, exerciseId: ExerciseId): RemoveExerciseResult => {
  const exercise = workout.exercises.find(e => e.id === exerciseId);
  if (!exercise) return { success: false, reason: 'exercise-not-found' };
  return {
    success: true,
    workout: { ...workout, exercises: workout.exercises.filter(e => e.id !== exerciseId) },
  };
};
```

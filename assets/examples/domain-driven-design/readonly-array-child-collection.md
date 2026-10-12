```typescript
type Workout = {
  readonly id: WorkoutId;
  readonly exercises: ReadonlyArray<Exercise>;  // Inspect OK, mutate impossible
  readonly maxExercises: number;
};
```

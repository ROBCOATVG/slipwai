```python
from dataclasses import dataclass, replace
from typing import Literal


# WRONG — leaks internals; the caller must obtain the Exercise object
# somehow.
def remove_exercise(workout: "Workout", exercise: "Exercise") -> "Workout": ...


@dataclass(frozen=True)
class ExerciseRemoved:
    workout: "Workout"


@dataclass(frozen=True)
class ExerciseNotFound:
    reason: Literal["exercise-not-found"] = "exercise-not-found"


RemoveExerciseResult = ExerciseRemoved | ExerciseNotFound


# RIGHT — boundary preserved; the caller only knows the ID.
def remove_exercise(workout: "Workout", exercise_id: "ExerciseId") -> RemoveExerciseResult:
    exercise = next((e for e in workout.exercises if e.id == exercise_id), None)
    if exercise is None:
        return ExerciseNotFound()
    return ExerciseRemoved(
        workout=replace(
            workout,
            exercises=tuple(e for e in workout.exercises if e.id != exercise_id),
        )
    )
```

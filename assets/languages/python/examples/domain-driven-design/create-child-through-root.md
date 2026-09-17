```python
from dataclasses import dataclass, replace, asdict
from typing import Literal


# WRONG — externally constructed child; the root can't enforce its own
# creation rules.
def add_exercise(workout: "Workout", exercise: "Exercise") -> "Workout": ...


@dataclass(frozen=True)
class ExerciseAdded:
    workout: "Workout"


@dataclass(frozen=True)
class MaxExercisesReached:
    reason: Literal["max-exercises-reached"] = "max-exercises-reached"


AddExerciseResult = ExerciseAdded | MaxExercisesReached


# RIGHT — the root creates the child itself, enforcing the max-exercises
# invariant.
def add_exercise(
    workout: "Workout", exercise_id: "ExerciseId", params: "NewExerciseParams"
) -> AddExerciseResult:
    if len(workout.exercises) >= workout.max_exercises:
        return MaxExercisesReached()
    exercise = Exercise(id=exercise_id, workout_id=workout.id, **asdict(params))
    return ExerciseAdded(workout=replace(workout, exercises=workout.exercises + (exercise,)))
```

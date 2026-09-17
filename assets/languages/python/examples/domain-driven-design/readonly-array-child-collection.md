```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Workout:
    id: "WorkoutId"
    exercises: tuple["Exercise", ...]  # Inspect OK, mutate impossible
    max_exercises: int
```

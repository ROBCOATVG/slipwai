```python
from datetime import datetime

from myapp.schemas.user import UserSchema  # Import real schema


def make_user(**overrides) -> User:
    defaults = {
        "id": "user-123",
        "name": "Test User",
        "email": "test@example.com",
        "role": "user",
        "is_active": True,
        "created_at": datetime(2024, 1, 1),
    }
    return UserSchema.model_validate({**defaults, **overrides})
```

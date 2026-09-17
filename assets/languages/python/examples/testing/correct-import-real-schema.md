```python
from myapp.schemas.user import UserSchema


def make_user(**overrides) -> User:
    defaults = {"id": "user-123", "name": "Test User", "email": "test@example.com"}
    return UserSchema.model_validate({**defaults, **overrides})
```

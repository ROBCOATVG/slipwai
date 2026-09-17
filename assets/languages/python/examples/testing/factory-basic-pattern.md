```python
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    role: str


def make_user(**overrides) -> User:
    defaults = User(id="user-123", name="Test User", email="test@example.com", role="user")
    return replace(defaults, **overrides)


# Usage
def test_creates_user_with_custom_email():
    user = make_user(email="custom@example.com")
    result = create_user(user)
    assert result.success is True
```

```python
def make_user(**overrides) -> User:
    defaults = User(
        id="user-123",
        name="Test User",
        email="test@example.com",
        role="user",
    )
    return replace(defaults, **overrides)  # All required fields present
```

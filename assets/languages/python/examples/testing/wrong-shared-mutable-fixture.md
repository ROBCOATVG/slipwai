```python
# ❌ Module-level mutable fixture shared by every test
user = User(id="user-123", name="Test User", email="test@example.com", role="user")


def test_one():
    user.name = "Modified User"


def test_two():
    assert user.name == "Test User"  # Order-dependent failure
```

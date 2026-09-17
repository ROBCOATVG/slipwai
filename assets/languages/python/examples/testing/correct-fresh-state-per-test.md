```python
def test_one():
    user = make_user(name="Modified User")  # Fresh state
    ...


def test_two():
    user = make_user()  # Fresh state, not affected by test_one
    assert user.name == "Test User"  # ✅ Passes
```

```python
# ❌ Schema already defined in myapp/schemas/user.py!
class UserSchema(BaseModel):
    id: str
    name: str
    email: str


def make_user():
    return UserSchema(id="user-123", name="Test User", email="test@example.com")
```

```python
from dataclasses import dataclass
from typing import Protocol
from unittest.mock import AsyncMock, patch


@dataclass(frozen=True)
class UserId:
    value: str


@dataclass(frozen=True)
class User:
    id: UserId
    email: str


class UserRepository(Protocol):
    async def find_by_id(self, user_id: UserId) -> User | None: ...
    async def save(self, user: User) -> None: ...


# Good: a fake — maintains real state, implements the real interface
# (Protocol). Behavior is exercised through the same contract production
# code uses, so a test built on it proves the use case actually works, not
# just that a call happened.
class FakeUserRepository:
    def __init__(self, initial: list[User] | None = None) -> None:
        self._store: dict[UserId, User] = {user.id: user for user in (initial or [])}

    async def find_by_id(self, user_id: UserId) -> User | None:
        return self._store.get(user_id)

    async def save(self, user: User) -> None:
        self._store[user.id] = user


# Bad: a mock — verifies that a call happened, not that the behavior is
# correct. It knows nothing about state, so it can't catch bugs like "saved
# the wrong user" or "saved twice." It also couples the test to
# implementation details (the exact method name and module path).
@patch("myapp.repositories.user_repository.UserRepository", autospec=True)
def test_with_a_mock_only_proves_a_method_was_called(mock_repo_cls: AsyncMock) -> None:
    mock_repo = mock_repo_cls.return_value
    mock_repo.save.assert_not_called()  # ...and that's all a mock can meaningfully assert
```

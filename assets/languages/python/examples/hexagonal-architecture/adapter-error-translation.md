```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UserCreated:
    pass


@dataclass(frozen=True)
class UserAlreadyExists:
    pass


CreateUserResult = UserCreated | UserAlreadyExists


class UserCreator(Protocol):
    async def create(self, user: "User") -> CreateUserResult: ...


class SqlAlchemyUserCreator:
    """Driven adapter — translates an expected storage condition into port vocabulary."""

    def __init__(self, session: "AsyncSession") -> None:
        self._session = session

    async def create(self, user: "User") -> CreateUserResult:
        try:
            self._session.add(to_row(user))
            await self._session.commit()
            return UserCreated()
        except IntegrityError as exc:
            await self._session.rollback()
            if is_unique_violation(exc):
                return UserAlreadyExists()
            raise  # unexpected errors (connection lost, disk full) propagate
```

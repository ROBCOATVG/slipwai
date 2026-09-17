```python
from typing import Protocol


class UserRepository(Protocol):
    async def find_by_id(self, user_id: str) -> "User | None": ...
    async def save(self, user: "User") -> None: ...


class SqlAlchemyUserRepository:
    """Driven adapter — implements the port using SQLAlchemy."""

    def __init__(self, session: "AsyncSession") -> None:
        self._session = session

    async def find_by_id(self, user_id: str) -> "User | None":
        row = await self._session.get(UserRow, user_id)
        return to_user(row) if row is not None else None

    async def save(self, user: "User") -> None:
        await self._session.merge(to_row(user))
        await self._session.commit()


class FakeUserRepository:
    """Driven adapter — implements the same port for tests."""

    def __init__(self, initial: list["User"] | None = None) -> None:
        self._store: dict[str, "User"] = {u.id: u for u in (initial or [])}

    async def find_by_id(self, user_id: str) -> "User | None":
        return self._store.get(user_id)

    async def save(self, user: "User") -> None:
        self._store[user.id] = user
```

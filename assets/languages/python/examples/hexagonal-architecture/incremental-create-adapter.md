```python
# billing/adapters/driven/postgres/sqlalchemy_user_repository.py — driven adapter
from typing import Literal


class SqlAlchemyUserRepository:
    """Driven adapter — implements UserRepository against a real DB session."""

    def __init__(self, session: "AsyncSession") -> None:
        self._session = session

    async def find_by_id(self, user_id: "UserId") -> "StoredUser | None":
        row = await self._session.get(UserRow, user_id)
        return StoredUser(value=to_user(row), version=row.version) if row is not None else None

    async def save(self, user: "User", expected_version: int) -> Literal["saved", "conflict"]:
        result = await self._session.execute(
            update(UserRow)
            .where(UserRow.id == user.id, UserRow.version == expected_version)
            .values(**to_row(user), version=expected_version + 1)
        )
        await self._session.commit()
        return "saved" if result.rowcount == 1 else "conflict"
```

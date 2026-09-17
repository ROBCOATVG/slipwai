```python
# ❌ Domain imports SQLAlchemy directly
from sqlalchemy import select


async def find_active_users(session):
    return await session.execute(select(users).where(users.c.active.is_(True)))


# ✅ Application defines the contract it consumes; an adapter implements it
from typing import Protocol


class UserRepository(Protocol):
    async def find_active(self) -> list["User"]: ...
```

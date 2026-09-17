```python
from typing import Protocol


# ❌ Technology leaks into the port
class UserRepository(Protocol):
    async def find_by_sql_query(self, sql: str) -> list["User"]: ...
    async def get_from_redis_cache(self, key: str) -> "User": ...


# ✅ Business language
class UserRepository(Protocol):
    async def find_active(self) -> list["User"]: ...
    async def find_by_id(self, user_id: str) -> "User | None": ...
```

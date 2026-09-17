```python
# billing/hexagon/application/user_repository.py — application-owned port
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class StoredUser:
    value: "User"
    version: int


class UserRepository(Protocol):
    async def find_by_id(self, user_id: "UserId") -> StoredUser | None: ...
    async def save(self, user: "User", expected_version: int) -> Literal["saved", "conflict"]: ...
```

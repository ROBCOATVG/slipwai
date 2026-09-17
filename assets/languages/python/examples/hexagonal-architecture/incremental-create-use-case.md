```python
# billing/hexagon/application/deduct_user_balance.py — driving port + use case
from dataclasses import dataclass
from typing import Literal, Protocol, Union


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Opaque proof of authentication; the request body cannot select a user."""

    user_id: "UserId"


@dataclass(frozen=True)
class DeductUserBalanceCommand:
    principal: AuthenticatedPrincipal
    amount: "Money"


DeductUserBalanceFailureReason = Union[DeductFailureReason, Literal["not-found", "concurrent-change"]]


@dataclass(frozen=True)
class DeductUserBalanceFailure:
    reason: DeductUserBalanceFailureReason


DeductUserBalanceResult = Union[DeductSuccess, DeductUserBalanceFailure]


class ForDeductingUserBalances(Protocol):
    async def deduct_user_balance(self, command: DeductUserBalanceCommand) -> DeductUserBalanceResult: ...


@dataclass(frozen=True)
class UserBalanceDeduction:
    user_repo: "UserRepository"

    async def deduct_user_balance(self, command: DeductUserBalanceCommand) -> DeductUserBalanceResult:
        stored = await self.user_repo.find_by_id(command.principal.user_id)
        if stored is None:
            return DeductUserBalanceFailure(reason="not-found")

        result = deduct_balance(stored.value, command.amount)
        if not isinstance(result, DeductSuccess):
            return result

        saved = await self.user_repo.save(result.user, stored.version)
        if saved == "conflict":
            return DeductUserBalanceFailure(reason="concurrent-change")
        return result
```

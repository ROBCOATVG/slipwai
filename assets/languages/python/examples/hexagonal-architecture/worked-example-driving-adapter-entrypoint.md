```python
# gifting/adapters/driving/http/occasions_pledge.py
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from gifting.adapters.driven.postgres.pledge_persistence import PostgresPledgePersistence
from gifting.hexagon.application.pledge_to_occasion import PledgingToOccasions
from gifting.hexagon.application.pledging import (
    AuthenticatedPledger,
    ForPledgingToOccasions,
    PledgeToOccasionCommand,
)
from gifting.hexagon.domain.types import Money, OccasionId, PledgeId


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: dict[str, Any]


class HttpRequest(Protocol):
    path_params: dict[str, str]

    async def json(self) -> Any: ...


def _parse_occasion_id(raw: str) -> OccasionId | None:
    trimmed = raw.strip()
    return OccasionId(trimmed) if trimmed else None


def _parse_pledge_body(raw: Any) -> Money | None:
    # A strict schema: only "amount" is accepted; contributor/tenant fields
    # in the body are rejected, never trusted from the request.
    if not isinstance(raw, dict) or set(raw) != {"amount"}:
        return None
    amount = raw["amount"]
    if not isinstance(amount, dict) or set(amount) != {"minor_units", "currency"}:
        return None
    minor_units, currency = amount.get("minor_units"), amount.get("currency")
    if not isinstance(minor_units, int) or isinstance(minor_units, bool) or minor_units < 0:
        return None
    if currency not in ("GBP", "USD", "EUR"):
        return None
    return Money(minor_units=minor_units, currency=currency)


async def post_pledge(
    request: HttpRequest,
    authenticate_pledger: Callable[[HttpRequest], Awaitable[AuthenticatedPledger | None]],
    persistence_for: Callable[[], PostgresPledgePersistence],
) -> HttpResponse:
    """POST /occasions/{id}/pledge — the trivial executable entrypoint: parse
    -> delegate -> translate. Combines a driving adapter with inline
    composition because this is the deployment entrypoint and its graph is
    trivial; a larger graph belongs in an explicit composition root instead.
    """

    # The authentication adapter is the only production constructor for this
    # provider-free principal; the request body cannot choose the actor.
    principal = await authenticate_pledger(request)
    if principal is None:
        return HttpResponse(status=401, body={"error": "unauthorized"})

    occasion_id = _parse_occasion_id(request.path_params.get("id", ""))
    if occasion_id is None:
        return HttpResponse(status=422, body={"error": "invalid-path"})

    try:
        raw_body = await request.json()
    except ValueError:
        return HttpResponse(status=400, body={"error": "malformed-json"})

    amount = _parse_pledge_body(raw_body)
    if amount is None:
        return HttpResponse(status=422, body={"error": "invalid-body"})

    # Inline composition: this handler is the executable entrypoint and the
    # graph is trivial.
    persistence = persistence_for()
    pledging: ForPledgingToOccasions = PledgingToOccasions(persistence=persistence)

    result = await pledging.pledge_to_occasion(
        PledgeToOccasionCommand(
            pledge_id=PledgeId(str(uuid.uuid4())),
            occasion_id=occasion_id,
            principal=principal,
            amount=amount,
        )
    )

    # Translate result to HTTP; status selection is protocol translation, not
    # business policy.
    if not result.success:
        status = {"not-found": 404, "concurrent-change": 409}.get(result.reason, 422)
        return HttpResponse(status=status, body={"error": result.reason})
    return HttpResponse(status=200, body={"pledged": result.occasion.total_pledged})
```

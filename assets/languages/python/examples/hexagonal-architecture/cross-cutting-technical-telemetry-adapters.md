```python
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)
app = FastAPI()


@app.post("/occasions/{occasion_id}/pledges")
async def pledge_to_occasion(request: Request) -> JSONResponse:
    """Driving adapter: log the request/response cycle."""
    try:
        raw_body = await request.json()
    except ValueError:
        return JSONResponse({"error": "malformed-json"}, status_code=400)

    try:
        body = PledgeBody.model_validate(raw_body)
    except ValidationError:
        return JSONResponse({"error": "invalid-body"}, status_code=422)

    pledging: "ForPledgingToOccasions" = PledgingToOccasions(pledge_persistence)
    result = await pledging.pledge_to_occasion(body.to_command())

    if not result.success:
        logger.warning(
            "Pledge rejected", extra={"reason": result.reason, "occasion_id": body.occasion_id}
        )
    return to_http_response(result)


class PostgresOccasionRepository:
    """Driven adapter: log infrastructure interactions."""

    def __init__(self, db: "Database", logger: logging.Logger) -> None:
        self._db = db
        self._logger = logger

    async def save(self, occasion: "Occasion") -> None:
        await self._db.insert("occasions", to_row(occasion))
        self._logger.debug("Occasion saved", extra={"id": occasion.id})
```

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError

app = FastAPI()


class DeductBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_minor_units: int
    currency: str


@app.post("/users/me/deduct")
async def deduct(request: Request) -> JSONResponse:
    """BEFORE — everything crammed into the route handler."""
    principal = await authenticate_request(request)
    if principal is None:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    try:
        raw_body = await request.json()
    except ValueError:
        return JSONResponse({"error": "malformed-json"}, status_code=400)

    try:
        body = DeductBody.model_validate(raw_body)
    except ValidationError:
        return JSONResponse({"error": "invalid-body"}, status_code=422)

    row = await db.get(UserRow, principal.user_id)
    if row is None:
        return JSONResponse({"error": "not found"}, status_code=404)

    if body.amount_minor_units <= 0:
        return JSONResponse({"error": "invalid amount"}, status_code=422)
    if body.currency != row.currency:
        return JSONResponse({"error": "currency mismatch"}, status_code=422)
    if row.balance_minor_units < body.amount_minor_units:
        return JSONResponse({"error": "insufficient"}, status_code=422)

    row.balance_minor_units -= body.amount_minor_units
    await db.commit()

    return JSONResponse({"balance_minor_units": row.balance_minor_units, "currency": row.currency})
```

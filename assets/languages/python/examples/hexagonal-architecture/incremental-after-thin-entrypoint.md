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
    """Serverless-style executable entrypoint = inline composition + driving adapter.

    Valid only while this object graph remains trivial and unshared.
    """
    # Authentication owns the provider-free principal; the body cannot select a user.
    principal = await authenticate_request(request)
    if principal is None:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    session = get_database_session()

    # Wire adapters.
    user_repo = SqlAlchemyUserRepository(session)
    balance_deduction: ForDeductingUserBalances = UserBalanceDeduction(user_repo=user_repo)

    # Translate transport syntax separately from request-schema validation.
    try:
        raw_body = await request.json()
    except ValueError:
        return JSONResponse({"error": "malformed-json"}, status_code=400)

    try:
        body = DeductBody.model_validate(raw_body)
    except ValidationError:
        return JSONResponse({"error": "invalid-body"}, status_code=422)

    # Call use case.
    result = await balance_deduction.deduct_user_balance(
        DeductUserBalanceCommand(
            principal=principal,
            amount=Money(minor_units=body.amount_minor_units, currency=body.currency),
        )
    )

    if isinstance(result, DeductUserBalanceFailure):
        status = {"not-found": 404, "concurrent-change": 409}.get(result.reason, 422)
        return JSONResponse({"error": result.reason}, status_code=status)

    return JSONResponse(
        {"balance": {"minor_units": result.user.balance.minor_units, "currency": result.user.balance.currency}}
    )
```

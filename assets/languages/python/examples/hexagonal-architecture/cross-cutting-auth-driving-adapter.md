```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

app = FastAPI()


@app.post("/occasions/{occasion_id}/pledges")
async def pledge_to_occasion(request: Request) -> JSONResponse:
    """Driving adapter: extract and validate auth, then delegate to the use case."""
    principal = await authenticate_request(request)  # sole production constructor
    if principal is None:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    pledging: "ForPledgingToOccasions" = PledgingToOccasions(pledge_persistence)

    try:
        raw_body = await request.json()
    except ValueError:
        return JSONResponse({"error": "malformed-json"}, status_code=400)

    try:
        body = PledgeBody.model_validate(raw_body, strict=True)
    except ValidationError:
        return JSONResponse({"error": "invalid-body"}, status_code=422)

    # Strict body has no actor/tenant fields; the principal owns attribution.
    result = await pledging.pledge_to_occasion(
        PledgeToOccasionCommand(
            pledge_id=body.pledge_id,
            occasion_id=body.occasion_id,
            amount=body.amount,
            principal=principal,
        )
    )
    return to_http_response(result)
```

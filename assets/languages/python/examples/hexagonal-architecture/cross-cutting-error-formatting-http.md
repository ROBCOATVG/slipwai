```python
from fastapi.responses import JSONResponse

# Domain returns a rejection like PledgeRejected(reason="funding-closed");
# the driving adapter translates it to a protocol-specific response.
_STATUS_BY_REASON: dict[str, int] = {
    "not-found": 404,
    "concurrent-change": 409,
    "non-positive-amount": 422,
    "currency-mismatch": 422,
    "exceeds-budget": 422,
    "funding-closed": 422,
}


def to_http_response(result: "PledgeResult") -> JSONResponse:
    if result.success:
        return JSONResponse({"pledged": result.occasion.total_pledged}, status_code=200)
    return JSONResponse({"error": result.reason}, status_code=_STATUS_BY_REASON[result.reason])
```

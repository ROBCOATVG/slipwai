```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

app = FastAPI()


class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list["OrderItem"]


@app.post("/orders")
async def create_order(request: Request) -> JSONResponse:
    """Serverless-style executable entrypoint = inline composition + driving adapter.

    Valid only while this object graph remains trivial and unshared.
    """
    db = get_database_connection()

    # Wire adapters
    repo = SqlAlchemyOrderRepository(db)
    gateway = StripePaymentGateway(settings.stripe_key)
    order_placement: ForPlacingOrders = OrderPlacement(repo, gateway)

    # Translate transport syntax separately from request-schema validation.
    try:
        raw_body = await request.json()
    except ValueError:
        return JSONResponse({"error": "malformed-json"}, status_code=400)

    try:
        command = CreateOrderRequest.model_validate(raw_body)
    except ValidationError:
        return JSONResponse({"error": "invalid-body"}, status_code=422)

    # Call use case
    result = await order_placement.place_order(command)
    return JSONResponse(to_response_body(result))
```

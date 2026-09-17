"""Edge tests: the outermost surface, exercised through the framework rather than around it.

`TestClient` runs a real request through the real router with no socket, so these stay in `make
verify` — an entry-point test that needs a listening port is an integration test wearing the wrong
name.

No ``from __future__ import annotations`` here, for the reason the adapter itself has none: FastAPI
resolves a handler's annotations at run time, and under that import a request model defined inside a
test function resolves to nothing and is silently treated as a query parameter. A test that declares
its model where the test needs it is the shape a slice will copy, so it has to be the shape that
works.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Parenthesised because this package is named after the project, and a project's name can be
# long enough to put a one-line import over the line-length gate.
from delivery_starter.adapters.driving.http.app import (
    SERVICE_NAME,
    build_app,
    readiness,
)


def test_reports_liveness() -> None:
    with TestClient(build_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class _EmptyLog:
    """A store with nothing in it, which is what a healthy new project's log is."""

    def head(self) -> int:
        return 0


class _Unreachable:
    """A store that cannot answer — written here, by hand, and that is the rule rather than an
    accident.

    A mocking framework would let this suite assert that `head` was *called*, which proves nothing
    about what the route does with the answer. What matters is the two answers the port can give
    and the two statuses they become.
    """

    def head(self) -> int:
        raise ConnectionError("connection refused")


def test_is_ready_when_the_event_store_answers() -> None:
    with TestClient(build_app([readiness(_EmptyLog())])) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_is_not_ready_and_says_no_more_than_the_category_when_the_store_does_not_answer() -> None:
    app = build_app([readiness(_Unreachable())])
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unready", "reason": "eventStore"}
    # The driver's own message — which is where a connection string ends up — stays in the log.
    assert "connection refused" not in response.text


def test_is_ready_with_nothing_to_ask_when_the_project_has_no_store() -> None:
    with TestClient(build_app([readiness()])) as client:
        assert client.get("/ready").json() == {"status": "ready"}
        # Liveness is still liveness: `/health` answers whatever the dependencies are doing.
        assert client.get("/health").json() == {"status": "ok"}


def test_does_not_echo_the_requested_path_back_on_a_404() -> None:
    """A 404 body that repeats the URL puts whatever the URL carried into every access log
    downstream.

    Asserted rather than assumed, because it is the kind of regression a framework upgrade or a
    well-meaning custom handler reintroduces silently.
    """
    with TestClient(build_app()) as client:
        response = client.get("/orders/tok-live-abc123")

    assert response.status_code == 404
    assert response.json() == {"error": "notFound"}
    assert "tok-live-abc123" not in response.text
    assert "/orders" not in response.text


def test_does_not_reveal_that_a_path_exists_under_a_different_method() -> None:
    with TestClient(build_app()) as client:
        response = client.post("/health")

    assert response.status_code in {404, 405}
    if response.status_code == 404:
        assert response.json() == {"error": "notFound"}


def test_registers_the_routes_it_is_given_and_holds_none_of_its_own() -> None:
    def register(app: FastAPI) -> None:
        @app.get("/orders/{order_id}")
        async def read_order(order_id: str) -> dict[str, str]:
            return {"id": order_id}

    with TestClient(build_app([register])) as client:
        response = client.get("/orders/order-1")

    assert response.status_code == 200
    assert response.json() == {"id": "order-1"}


class _Flags:
    """A flag source standing in for the reader's, which is what a real service hands the route."""

    def __init__(self, flags: dict[str, str]) -> None:
        self._flags = flags

    def snapshot(self) -> dict[str, str]:
        return self._flags


def test_serves_this_environments_flags_to_the_browser_app_when_given_a_source() -> None:
    # A browser cannot read this environment, so the service answers for it. `snapshot()` is the
    # reader's second question and this route is the only caller of it.
    with TestClient(build_app([], _Flags({"checkout-v2": "on"}))) as client:
        response = client.get("/api/flags")

    assert response.status_code == 200
    assert response.json() == {"checkout-v2": "on"}
    # The answer is what the environment is set to *now*: a flipped flag a cache still hides is the
    # flip looking broken.
    assert response.headers["cache-control"] == "no-store"


def test_has_no_flags_route_at_all_when_given_no_source() -> None:
    # `--target none` has nowhere to declare a flag, so this route is absent
    # rather than answering an empty object — an endpoint that always returns
    # nothing reads as a capability the project does not have.
    with TestClient(build_app()) as client:
        response = client.get("/api/flags")

    assert response.status_code == 404
    assert response.json() == {"error": "notFound"}


def test_reports_a_schema_failure_in_one_shape_without_echoing_the_input() -> None:
    class Customer(BaseModel):
        """Declared inside the test that uses it, which is the whole point of the note above."""

        email: str
        token: str

    def register(app: FastAPI) -> None:
        @app.post("/customers")
        async def create(customer: Customer) -> dict[str, str]:
            return {"email": customer.email}

    with TestClient(build_app([register])) as client:
        response = client.post("/customers", json={"token": "not-returned"})

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "schemaValidationFailed"
    assert body["field"] == "email"
    # The rejected input is not part of the reply: a validation error on a token field must not
    # quote it.
    assert "tok-live-abc123" not in response.text


class Order(BaseModel):
    """A slice's request model, at module scope because the route that reads it is."""

    sku: str


class OrderPlaced(BaseModel):
    """A slice's response model: what the route promises, and the whole of what it may answer."""

    id: str


def _orders(app: FastAPI) -> None:
    """A slice's route, declared the way every route in this service is."""

    @app.post("/orders", response_model=OrderPlaced, status_code=201)
    async def place(order: Order) -> dict[str, str]:
        # Deliberately more than the model names, to prove the response model is what decides.
        return {"id": f"order-for-{order.sku}", "internal_cost": "42"}


def test_answers_with_what_the_response_model_names_and_nothing_else() -> None:
    with TestClient(build_app([_orders])) as client:
        response = client.post("/orders", json={"sku": "sku-1"})

    assert response.status_code == 201
    assert response.json() == {"id": "order-for-sku-1"}
    assert "internal_cost" not in response.text


def test_publishes_the_document_and_it_carries_the_routes_a_slice_registered() -> None:
    """The contract is published, not described.

    A browser app builds its client from this and a test asserts against it, so `make verify` never
    has to start a browser to know the contract changed.
    """
    with TestClient(build_app([_orders], _Flags({"checkout-v2": "on"}))) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert sorted(document["paths"]) == ["/api/flags", "/health", "/orders"]
    # The title is this service's own package, so the document says which service it describes.
    assert document["info"]["title"] == SERVICE_NAME
    # `/health` is in the document with the shape it answers with, rather than as an untyped route.
    health = document["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]
    assert health["schema"]["$ref"].endswith("/Health")


def test_every_response_carries_the_security_headers() -> None:
    """Asserted through the framework, because the headers are the whole of what these buy."""
    with TestClient(build_app()) as client:
        response = client.get("/health")

    # `nosniff` is the one that matters most for a JSON API: without it a browser may decide a
    # response is HTML because of what is inside it, and run what it finds.
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_a_cross_origin_request_is_permitted_nothing_until_an_origin_is_allowed() -> None:
    # Empty is the default, and it is same-origin only: the response carries no permission at all,
    # so the browser refuses to hand it to the page that asked.
    with TestClient(build_app()) as client:
        response = client.get("/health", headers={"origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_exactly_the_origins_it_was_given_are_permitted() -> None:
    app = build_app(cors_origins=["http://localhost:5173"])
    with TestClient(app) as client:
        allowed = client.get("/health", headers={"origin": "http://localhost:5173"})
        # A near miss is a miss: one port out is a different origin, and nothing here guesses.
        refused = client.get("/health", headers={"origin": "http://localhost:5174"})

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in refused.headers

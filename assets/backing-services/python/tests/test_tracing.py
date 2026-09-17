"""What tracing answers with, and what it answers with when nobody has set an endpoint."""

from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

# Parenthesised because this package is named after the project, and a project's name can be
# long enough to put a one-line import over the line-length gate.
from delivery_starter.adapters.driving.http.app import build_app
from delivery_starter.tracing import (
    start_tracing,
    trace_context,
    trace_ids,
)

#: A `traceparent` as W3C writes one: version, trace id, span id, flags.
INCOMING = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


@pytest.fixture(scope="module", autouse=True)
def provider():
    """One provider for the whole module, with no endpoint.

    No endpoint is the state every generated project starts in, so everything below is asserted
    against the default wiring rather than against a configuration nobody runs.
    """
    tracing = start_tracing("tracing-test", None)
    assert tracing.exporting is False
    yield tracing
    tracing.shutdown()


def test_an_endpoint_is_what_decides_whether_anything_is_exported() -> None:
    # Built and immediately shut down: what is asserted is the decision, and an exporter
    # pointing at an address nothing is listening on has to be constructible without anything
    # failing — which is exactly the state a service started with a collector that is down is in.
    asked = start_tracing("tracing-test", "http://127.0.0.1:4318")
    try:
        assert asked.exporting is True
    finally:
        asked.shutdown()


def test_nothing_invents_an_id_outside_a_request() -> None:
    assert trace_ids() == (None, None)
    assert trace_context() == {}


def test_an_event_is_correlated_by_the_trace_the_caller_sent_in() -> None:
    seen: dict[str, object] = {}

    def register(app) -> None:
        @app.get("/seen")
        async def route() -> dict[str, str]:
            correlation, causation = trace_ids()
            seen.update(correlation=str(correlation), causation=str(causation), **trace_context())
            return {}

    client = TestClient(build_app([register]))
    client.get("/seen", headers={"traceparent": INCOMING})

    # The caller's trace id, read as the UUID a correlation id is. Nothing is invented: it is the
    # same 128 bits, so a log line in the other service and an event here name one transaction.
    assert seen["correlation"] == "4bf92f35-77b3-4da6-a3ce-929d0e0e4736"
    assert seen["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    # The cause is *this* service's request span, not the caller's — the event was produced by
    # handling this request, and the trace already records which span that one descends from. A
    # span id is 64 bits and a causation id is 128, so it sits in the low half.
    span_id = str(seen["span_id"])
    assert seen["causation"] == str(uuid.UUID(int=int(span_id, 16)))


def test_a_request_with_no_traceparent_starts_its_own_trace() -> None:
    seen: dict[str, str] = {}

    def register(app) -> None:
        @app.get("/fresh")
        async def route() -> dict[str, str]:
            correlation, _ = trace_ids()
            seen["correlation"] = str(correlation)
            return {}

    TestClient(build_app([register])).get("/fresh")

    # Present and well-shaped, and deliberately not asserted to be any particular value: a trace
    # nobody handed in is a new one every time, which is the behaviour being checked.
    assert re.fullmatch(r"[0-9a-f-]{36}", seen["correlation"])
    assert seen["correlation"] != "00000000-0000-0000-0000-000000000000"

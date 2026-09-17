"""This process's traces: the SDK, wired; the exporter, only when somewhere was named to send to.

── Why the SDK ships and the exporter does not ──────────────────────────────────────────────
A trace id is worth having before anything collects it. It is what ties a log line to the
request that produced it, what an incoming ``traceparent`` carries in from whoever called this
service, and — for a project that records events — what a business transaction is correlated
by. None of that needs a collector, and all of it needs the SDK.

What a collector *would* need is an address, and there is no honest default for one. A starter
pointing at ``http://localhost:4318`` either finds nothing there and retries a connection
nobody asked for, or finds something and ships a project's traffic somewhere it was never told
about. So the rule is the one the variable states: set ``OTEL_EXPORTER_OTLP_ENDPOINT`` and
spans are exported; leave it unset and they are recorded, given ids, and dropped. The service
starts and ``make verify`` passes with nothing listening either way.

── Read through the checked environment, not ``os.environ`` ─────────────────────────────────
The endpoint arrives as the ``Settings`` model ``settings.py`` declares and ``main`` has
already validated, so a value that is not a URL stops the process at start-up with the variable
named rather than being discovered as an exporter that silently never connects.

── An unreachable collector is a warning, never a crash ─────────────────────────────────────
Exporting happens on a background batch, off the request path, and a failure is reported
through OpenTelemetry's own logger — which is this process's logger, because
``logging_setup`` configured the root. Telemetry that can take the service down with it is
worse than no telemetry.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass(frozen=True)
class Tracing:
    """What ``start_tracing`` hands back: whether anything is shipped, and how to stop."""

    #: ``True`` only when an endpoint was named — the one fact a start-up line should report.
    exporting: bool
    provider: TracerProvider

    def shutdown(self) -> None:
        """Flush what is batched and release the exporter.

        A flush is a network call, and process exit is the worst moment for one to raise: a
        collector that has gone away would otherwise turn a clean shutdown into a traceback.
        Reported and swallowed here rather than at the call site, so nobody has to remember to.
        """
        try:
            self.provider.shutdown()
        except Exception as error:
            logging.getLogger(__name__).warning(
                "traces could not be flushed on shutdown: %s", error
            )


def start_tracing(service_name: str, endpoint: str | None) -> Tracing:
    """Record spans, and export them only where ``OTEL_EXPORTER_OTLP_ENDPOINT`` says to.

    ``set_tracer_provider`` is what makes this the process's provider, so anything already
    holding a tracer — the FastAPI instrumentation, which took one while the app was built —
    starts recording through it.

    :param service_name: what this service calls itself in a trace
    :param endpoint: the OTLP collector's base URL, or ``None`` for no exporter at all
    """
    resource = Resource.create({SERVICE_NAME: service_name, SERVICE_VERSION: "0.1.0"})
    provider = TracerProvider(resource=resource)
    if endpoint is not None:
        # No processor at all is the "no exporter" state, and it is not the same as a disabled
        # SDK: spans are still created, so every id below is real and every log line still
        # carries one. They are simply not kept once they end.
        exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return Tracing(exporting=endpoint is not None, provider=provider)


def trace_ids() -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """The trace and span in scope, as the ids an event carries — ``(None, None)`` outside one.

    ── Why this exists ──────────────────────────────────────────────────────────────────────
    Where this project records events, the port has required a ``correlation_id`` and an
    optional ``causation_id`` on every one of them from the first line — and until there was
    a trace to take them from, every slice had to invent both. Inventing them is how a causal
    tree ends up with everything appearing to have caused itself. The request already has an
    identity — the span the transport opened for it, continuing whatever ``traceparent`` the
    caller sent — so that is what the events it produces are correlated by, and a trace that
    crossed two services correlates the events on both sides of it.

    ── Why they are re-punctuated rather than re-encoded ────────────────────────────────────
    A correlation id is a UUID, and a W3C trace id is the same 128 bits: reading one as the
    other invents nothing. A span id is 64 bits, half of a UUID, so it goes in the low half
    with the high half left zero — reversible, and the zero prefix is what says at a glance
    that the id came from a span rather than from ``uuid4()``.

    ── How a slice uses it ──────────────────────────────────────────────────────────────────
    .. code-block:: python

        correlation, causation = trace_ids()
        event = DomainEvent(
            ...,
            correlation_id=create_correlation_id(correlation or uuid.uuid4()),
            causation_id=None if causation is None else create_causation_id(causation),
        )
    """
    span = trace.get_current_span()
    context = span.get_span_context()
    if not context.is_valid:
        return None, None
    return uuid.UUID(int=context.trace_id), uuid.UUID(int=context.span_id)


def trace_context() -> dict[str, str]:
    """``trace_id`` and ``span_id`` for a log record, or nothing outside a request.

    The spellings are OpenTelemetry's own logging conventions, so a collector correlates a log
    line with its trace without being told how. ``logging_setup`` puts them on every record.
    """
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return {}
    return {
        "trace_id": format(context.trace_id, "032x"),
        "span_id": format(context.span_id, "016x"),
    }

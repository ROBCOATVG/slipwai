/**
 * This process's traces: the SDK, wired; the exporter, only when somewhere was named to send to.
 *
 * ── Why the SDK ships and the exporter does not ───────────────────────────────────────────────────────
 * A trace id is worth having before anything collects it. It is what ties a log line to the request that
 * produced it, what an incoming `traceparent` carries in from whoever called this service, and — for a
 * project that records events — what a business transaction is correlated by. None of that needs a
 * collector, and all of it needs the SDK.
 *
 * What a collector *would* need is an address, and there is no honest default for one: a starter that
 * points at `http://localhost:4318` either finds nothing there, and then spends the first minute of every
 * run retrying a connection nobody asked for, or finds something and starts shipping a project's traffic
 * somewhere it was never told about. So the rule is the one the endpoint states: set
 * `OTEL_EXPORTER_OTLP_ENDPOINT` and spans are exported; leave it unset and they are recorded, given ids,
 * and dropped. The service starts and `make verify` passes with nothing listening either way.
 *
 * ── Read through the checked environment, not `process.env` ───────────────────────────────────────────
 * The endpoint arrives as `app.config`, which `src/config.ts` declares and `@fastify/env` has already
 * validated — so a value that is not a URL stops the process at start-up with the variable named, rather
 * than being discovered as an exporter that quietly never connects. That is also why `main.ts` starts
 * tracing *after* `app.ready()` and *before* `app.listen()`: `ready()` is where the environment is checked
 * and the instrumentation plugin is loaded, `listen()` is where the first request could arrive, and the
 * window between them is the one moment both facts are true.
 *
 * Registering the provider that late is safe because `@opentelemetry/api` hands out a proxy tracer: the
 * instrumentation asks for its tracer while the app boots, and that tracer starts delegating to this
 * provider the moment `register()` is called.
 *
 * ── An unreachable collector is a warning, never a crash ──────────────────────────────────────────────
 * Exporting happens on a background batch, off the request path, and the exporter reports a failure
 * through OpenTelemetry's own `diag` channel. That channel is wired to this service's logger below, so an
 * endpoint pointing at nothing produces warnings and a service that still answers. Telemetry that can take
 * the service down with it is worse than no telemetry.
 */
import { DiagLogLevel, diag, trace } from '@opentelemetry/api';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { BatchSpanProcessor, NodeTracerProvider } from '@opentelemetry/sdk-trace-node';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';

/** Just the two values tracing reads, so a test hands over an object rather than a whole `Config`. */
export type TracingConfig = {
  OTEL_SERVICE_NAME: string;
  /** Empty is "no exporter", which is the same answer as unset — see `src/config.ts`. */
  OTEL_EXPORTER_OTLP_ENDPOINT: string;
};

/** What `startTracing` hands back: whether anything is being shipped, and how to stop. */
export type Tracing = {
  /** `true` only when an endpoint was named — the one fact a start-up line should report. */
  readonly exporting: boolean;
  /** Flush what is batched and release the exporter. Called from the entry point's signal handler. */
  shutdown(): Promise<void>;
};

/** How a warning from inside OpenTelemetry reaches this process's log. */
export type TracingLogger = { warn(message: string): void; error(message: string): void };

/**
 * Start recording spans, and export them only where `OTEL_EXPORTER_OTLP_ENDPOINT` says to.
 *
 * `register()` is what makes the provider global: it installs the async-hooks context manager, so
 * `trace.getActiveSpan()` answers inside a handler, and the W3C propagator, so an incoming `traceparent`
 * continues the caller's trace rather than starting a new one.
 *
 * @param config the checked environment — `app.config`, or a plain object in a test
 * @param logger where OpenTelemetry's own diagnostics go; the app's logger in the entry point
 */
export function startTracing(config: TracingConfig, logger: TracingLogger): Tracing {
  diag.setLogger(
    {
      error: (m) => logger.error(m),
      warn: (m) => logger.warn(m),
      info: () => {},
      debug: () => {},
      verbose: () => {},
    },
    DiagLogLevel.WARN,
  );
  const endpoint =
    config.OTEL_EXPORTER_OTLP_ENDPOINT === '' ? undefined : config.OTEL_EXPORTER_OTLP_ENDPOINT;
  const provider = new NodeTracerProvider({
    resource: resourceFromAttributes({
      [ATTR_SERVICE_NAME]: config.OTEL_SERVICE_NAME,
      [ATTR_SERVICE_VERSION]: '0.1.0',
    }),
    // No processor at all is the "no exporter" state, and it is not the same as a disabled SDK: spans are
    // still created, so every id below is real and every log line still carries one. They are simply not
    // kept once they end.
    spanProcessors:
      endpoint === undefined
        ? []
        : [
            new BatchSpanProcessor(
              new OTLPTraceExporter({ url: `${endpoint.replace(/\/$/, '')}/v1/traces` }),
            ),
          ],
  });
  provider.register();
  return {
    exporting: endpoint !== undefined,
    // Flushing is a network call, and the last thing a process does before exiting is the worst moment
    // for one to be unhandled: a collector that has gone away would otherwise turn a clean shutdown into
    // a non-zero exit and an orchestrator's restart loop. The failure is reported and swallowed, here
    // rather than at the call site, so nobody has to remember to.
    shutdown: async () => {
      try {
        await provider.shutdown();
      } catch (error) {
        logger.warn(`traces could not be flushed on shutdown: ${String(error)}`);
      }
    },
  };
}

/**
 * The trace and span currently in scope, as the ids an event carries — or nothing outside a span.
 *
 * ── Why this exists ───────────────────────────────────────────────────────────────────────────────────
 * Where this project records events, the port has required a `correlationId` and an optional
 * `causationId` on every one of them from the first line — and until there was a trace to take them from,
 * every slice had to invent both. Inventing them is how a causal tree ends up with everything appearing to have caused
 * itself. The request already has an identity — the span the transport opened for it, continuing whatever
 * `traceparent` the caller sent — so that is what the events it produces are correlated by, and a trace
 * that crossed two services correlates the events on both sides of it.
 *
 * ── Why they are re-punctuated rather than re-encoded ─────────────────────────────────────────────────
 * A correlation id is a UUID, and a W3C trace id is the same 128 bits written without hyphens: putting
 * them back is a formatting change and nothing is invented. A span id is 64 bits, half of a UUID, so it
 * is placed in the low half with the high half left as zeroes — reversible, and the zero prefix is what
 * says at a glance that this id came from a span rather than from `randomUUID()`.
 *
 * ── How a slice uses it ───────────────────────────────────────────────────────────────────────────────
 * ```ts
 * const { correlationId, causationId } = traceIds();
 * const event: DomainEvent = {
 *   type: 'OrderPlaced', schemaVersion: 1, streamId, payload, occurredAt, actor,
 *   correlationId: createCorrelationId(correlationId ?? randomUUID()),
 *   ...(causationId === undefined ? {} : { causationId: createCausationId(causationId) }),
 * };
 * ```
 * `createCorrelationId` still parses them, because the branded types exist to be checked once at the edge
 * and this is an edge like any other.
 */
export function traceIds(): { correlationId?: string; causationId?: string } {
  const span = trace.getActiveSpan();
  if (span === undefined) {
    return {};
  }
  const { traceId, spanId } = span.spanContext();
  return { correlationId: hyphenate(traceId), causationId: hyphenate(`0000000000000000${spanId}`) };
}

/** 32 hex characters as a UUID reads them: 8-4-4-4-12. */
function hyphenate(hex: string): string {
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32),
  ].join('-');
}

/**
 * What every log record gains: the trace and span it happened inside, or nothing outside a request.
 *
 * pino calls this per record, which is the only way it can work — the logger is built before the app and
 * the span exists only while a request is being served. `trace_id` and `span_id` are the spellings
 * OpenTelemetry's own logging conventions use, so a collector correlates a log line with its trace without
 * being told how.
 */
export function traceContextMixin(): Record<string, string> {
  const span = trace.getActiveSpan();
  if (span === undefined) {
    return {};
  }
  const { traceId, spanId } = span.spanContext();
  return { trace_id: traceId, span_id: spanId };
}

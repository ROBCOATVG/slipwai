import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { buildApp } from '../../src/adapters/driving/http/app.js';
import { startTracing, traceContextMixin, traceIds } from '../../src/tracing.js';

/** Where `startTracing` sends OpenTelemetry's own diagnostics: collected, so a test can read them. */
function collecting(): { lines: string[]; warn(m: string): void; error(m: string): void } {
  const lines: string[] = [];
  return { lines, warn: (m) => lines.push(m), error: (m) => lines.push(m) };
}

const SERVICE = { OTEL_SERVICE_NAME: 'tracing-test', OTEL_EXPORTER_OTLP_ENDPOINT: '' };

// One provider for the whole file, because `register()` makes it the process's. Registered with no
// endpoint, which is the state every generated project starts in — so everything below is asserted
// against the default wiring rather than against a configuration nobody runs.
let tracing: ReturnType<typeof startTracing>;

beforeAll(() => {
  tracing = startTracing(SERVICE, collecting());
});

afterAll(async () => {
  await tracing.shutdown();
});

describe('startTracing', () => {
  it('records spans and exports nothing when no endpoint was named', () => {
    expect(tracing.exporting).toBe(false);
  });

  it('exports only where an endpoint says to', () => {
    // Built and immediately shut down: what is being asserted is the decision, and an exporter pointing
    // at an address nothing is listening on must be constructible without anything failing — which is
    // exactly the state a service started with a collector that is down is in.
    const asked = startTracing(
      { ...SERVICE, OTEL_EXPORTER_OTLP_ENDPOINT: 'http://127.0.0.1:4318' },
      collecting(),
    );

    expect(asked.exporting).toBe(true);
    return asked.shutdown();
  });
});

describe('traceIds', () => {
  it('is empty outside a request, so nothing invents an id it does not have', () => {
    expect(traceIds()).toEqual({});
  });

  it('correlates an event with the trace the caller sent in', async () => {
    // A `traceparent` as W3C writes one: version, trace id, span id, flags. The whole point of honouring
    // it is that a business transaction that began in another service keeps one correlation id across
    // both, so this asserts the id an event would carry — not merely that a span exists.
    const incoming = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
    const app = buildApp([
      (instance) => {
        instance.get('/seen', async () => ({ ...traceIds(), ...traceContextMixin() }));
      },
    ]);

    const response = await app.inject({
      method: 'GET',
      url: '/seen',
      headers: { traceparent: incoming },
    });

    const seen = response.json();

    // The caller's trace id, re-punctuated as the UUID a correlation id is. Nothing is invented: it is
    // the same 128 bits, so a log line in the other service and an event here name one transaction.
    expect(seen.correlationId).toBe('4bf92f35-77b3-4da6-a3ce-929d0e0e4736');
    expect(seen.trace_id).toBe('4bf92f3577b34da6a3ce929d0e0e4736');
    // The cause is *this* service's request span, not the caller's — the event was produced by handling
    // this request, and the trace already records which span that one descends from. It sits in the low
    // half of a UUID with the high half left zero: a span id is 64 bits and a causation id is 128, and
    // the zero prefix says "from a span" rather than "randomly generated".
    expect(seen.causationId).toBe(
      `00000000-0000-0000-${seen.span_id.slice(0, 4)}-${seen.span_id.slice(4)}`,
    );
    await app.close();
  });

  it('starts its own trace when the caller sent none', async () => {
    const app = buildApp([
      (instance) => {
        instance.get('/fresh', async () => traceIds());
      },
    ]);

    const body = await app.inject({ method: 'GET', url: '/fresh' }).then((r) => r.json());

    // Present and well-shaped, and deliberately not asserted to be any particular value: a trace nobody
    // handed in is a new one every time, which is the behaviour being checked.
    expect(body.correlationId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );
    expect(body.causationId).toMatch(/^00000000-0000-0000-[0-9a-f]{4}-[0-9a-f]{12}$/);
    await app.close();
  });
});

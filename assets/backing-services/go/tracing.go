// Package observability holds this process's traces: the SDK, wired; the exporter, only when somewhere
// was named to send to.
//
// # Why the SDK ships and the exporter does not
//
// A trace id is worth having before anything collects it. It is what ties a log line to the request that
// produced it, what an incoming traceparent carries in from whoever called this service, and — for a
// project that records events — what a business transaction is correlated by. None of that needs a
// collector, and all of it needs the SDK.
//
// What a collector would need is an address, and there is no honest default for one. A starter pointing
// at http://localhost:4318 either finds nothing there and retries a connection nobody asked for, or finds
// something and ships a project's traffic somewhere it was never told about. So the rule is the one the
// variable states: set OTEL_EXPORTER_OTLP_ENDPOINT and spans are exported; leave it unset and they are
// recorded, given ids, and dropped. The service starts and `make verify` passes with nothing listening
// either way.
//
// # Read through the checked environment, not os.Getenv
//
// The endpoint arrives as config.Config, which `config` has already checked, so a value that is not a URL
// stops the process at start-up with the variable named rather than being discovered as an exporter that
// silently never connects.
//
// # An unreachable collector is a warning, never a crash
//
// Exporting happens on a background batch, off the request path, and Shutdown reports a failure rather
// than returning it fatally. Telemetry that can take the service down with it is worse than no telemetry.
package observability

import (
	"context"
	"encoding/hex"
	"log/slog"
	"net/http"
	"strings"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
)

// Tracing is what StartTracing hands back: whether anything is shipped, and how to stop.
type Tracing struct {
	// Exporting is true only when an endpoint was named — the one fact a start-up line should report.
	Exporting bool

	// How the spans still batched are flushed and the exporter released: the provider's own Shutdown,
	// or — in this package's own tests — a function that fails on purpose. A field rather than a call
	// straight through to the provider, because "a failure here is reported and never fatal" is a rule,
	// and a rule nothing can make fail is a rule nothing proves.
	flush func(context.Context) error
}

// StartTracing records spans, and exports them only where OTEL_EXPORTER_OTLP_ENDPOINT says to.
//
// Setting the global provider and the W3C propagator is what makes the rest work: otelhttp opens a span
// per request through the provider, and the propagator is what continues a caller's trace rather than
// starting a new one.
func StartTracing(ctx context.Context, serviceName, endpoint string) (*Tracing, error) {
	options := []sdktrace.TracerProviderOption{
		sdktrace.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion("0.1.0"),
		)),
	}
	// Asked once, used twice: whether an endpoint was named decides both whether a batcher is attached
	// and what a start-up line reports, and two spellings of one question are two things that can
	// disagree.
	exporting := endpoint != ""
	if exporting {
		// No batcher at all is the "no exporter" state, and it is not the same as a disabled SDK: spans
		// are still created, so every id below is real and every log line still carries one. They are
		// simply not kept once they end.
		exporter, err := otlptracehttp.New(ctx, otlptracehttp.WithEndpointURL(strings.TrimSuffix(endpoint, "/")+"/v1/traces"))
		if err != nil {
			return nil, err
		}
		options = append(options, sdktrace.WithBatcher(exporter))
	}
	provider := sdktrace.NewTracerProvider(options...)
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{}, propagation.Baggage{},
	))
	return &Tracing{Exporting: exporting, flush: provider.Shutdown}, nil
}

// Shutdown flushes what is batched and releases the exporter.
//
// A flush is a network call, and process exit is the worst moment for one to fail: a collector that has
// gone away would otherwise turn a clean shutdown into a non-zero exit and an orchestrator's restart
// loop. Reported and swallowed here rather than at the call site, so nobody has to remember to.
func (t *Tracing) Shutdown(ctx context.Context) {
	if err := t.flush(ctx); err != nil {
		slog.Warn("traces could not be flushed on shutdown", "err", err)
	}
}

// Instrument wraps a handler so every request gets a span, continuing whatever traceparent the caller
// sent. One line rather than a middleware written here: otelhttp is the contributed instrumentation for
// net/http, and a hand-written one would be a second implementation of the same specification.
func Instrument(handler http.Handler, serviceName string) http.Handler {
	return otelhttp.NewHandler(handler, serviceName)
}

// TraceIDs is the trace and span in scope, as the ids an event carries — both empty outside a span.
//
// # Why this exists
//
// Where this project records events, the port has required a CorrelationID and an optional CausationID on
// every one of them from the first line — and until there was a trace to take them from, every slice had
// to invent both. Inventing them is how a causal tree ends up with everything appearing to have caused
// itself. The request already has an identity — the span otelhttp opened for it, continuing whatever
// traceparent the caller sent — so that is what the events it produces are correlated by, and a trace
// that crossed two services correlates the events on both sides of it.
//
// # Why they are re-punctuated rather than re-encoded
//
// A correlation id is a UUID, and a W3C trace id is the same 128 bits written without hyphens: putting
// them back invents nothing. A span id is 64 bits, half of a UUID, so it goes in the low half with the
// high half left zero — reversible, and the zero prefix is what says at a glance that the id came from a
// span rather than from a random generator.
//
//	correlation, causation := observability.TraceIDs(r.Context())
//	event := events.DomainEvent{
//		CorrelationID: events.NewCorrelationID(correlation),
//		CausationID:   events.NewCausationID(causation),
//	}
func TraceIDs(ctx context.Context) (correlation, causation string) {
	spanContext := trace.SpanContextFromContext(ctx)
	if !spanContext.IsValid() {
		return "", ""
	}
	traceID := spanContext.TraceID()
	spanID := spanContext.SpanID()
	return hyphenate(hex.EncodeToString(traceID[:])), hyphenate("0000000000000000" + hex.EncodeToString(spanID[:]))
}

// hyphenate writes 32 hex characters the way a UUID reads them: 8-4-4-4-12.
func hyphenate(hexadecimal string) string {
	return hexadecimal[0:8] + "-" + hexadecimal[8:12] + "-" + hexadecimal[12:16] + "-" +
		hexadecimal[16:20] + "-" + hexadecimal[20:32]
}

// TracingHandler puts the trace and span of the request a line was written inside onto every record.
//
// A wrapper rather than a slog.Attr somebody remembers to pass: slog.Handler is handed the context, and
// the context is where the span is — so a line written from anywhere inside a request carries the ids
// without the caller knowing they exist. A log line nobody can tie back to a request is the reason an
// incident takes an afternoon.
//
// trace_id and span_id are the spellings OpenTelemetry's own logging conventions use, so a collector
// correlates a log line with its trace without being told how.
type TracingHandler struct{ slog.Handler }

// Handle adds the trace context, where the record was written inside one.
func (h TracingHandler) Handle(ctx context.Context, record slog.Record) error {
	if spanContext := trace.SpanContextFromContext(ctx); spanContext.IsValid() {
		record.AddAttrs(
			slog.String("trace_id", spanContext.TraceID().String()),
			slog.String("span_id", spanContext.SpanID().String()),
		)
	}
	return h.Handler.Handle(ctx, record)
}

// WithAttrs keeps the wrapper in place; without it slog.With would hand back the bare handler and every
// line written through a derived logger would silently lose its trace context.
func (h TracingHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return TracingHandler{Handler: h.Handler.WithAttrs(attrs)}
}

// WithGroup keeps the wrapper in place, for the same reason WithAttrs does.
func (h TracingHandler) WithGroup(name string) slog.Handler {
	return TracingHandler{Handler: h.Handler.WithGroup(name)}
}

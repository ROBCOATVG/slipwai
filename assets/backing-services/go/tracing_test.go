package observability

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// A traceparent as W3C writes one: version, trace id, span id, flags.
const incoming = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

// start registers the process's provider with no endpoint — the state every generated project starts in,
// so everything below is asserted against the default wiring rather than a configuration nobody runs.
func start(t *testing.T) *Tracing {
	t.Helper()
	tracing, err := StartTracing(context.Background(), "tracing-test", "")
	if err != nil {
		t.Fatalf("tracing would not start: %v", err)
	}
	t.Cleanup(func() { tracing.Shutdown(context.Background()) })
	return tracing
}

func TestNoEndpointRecordsSpansAndExportsNothing(t *testing.T) {
	if start(t).Exporting {
		t.Fatal("nothing was named to export to, so nothing should be exported")
	}
}

func TestAnEndpointIsWhatDecidesWhetherAnythingIsExported(t *testing.T) {
	// Built and immediately shut down: what is asserted is the decision, and an exporter pointing at an
	// address nothing is listening on has to be constructible without anything failing — which is exactly
	// the state a service started with a collector that is down is in.
	tracing, err := StartTracing(context.Background(), "tracing-test", "http://127.0.0.1:4318")
	if err != nil {
		t.Fatalf("an exporter with nothing listening must still build: %v", err)
	}
	defer tracing.Shutdown(context.Background())
	if !tracing.Exporting {
		t.Fatal("an endpoint was named and nothing is being exported")
	}
}

func TestNothingInventsAnIDOutsideARequest(t *testing.T) {
	start(t)
	correlation, causation := TraceIDs(context.Background())
	if correlation != "" || causation != "" {
		t.Fatalf("outside a span there is nothing to correlate by, got %q and %q", correlation, causation)
	}
}

func TestAnEventIsCorrelatedByTheTraceTheCallerSentIn(t *testing.T) {
	start(t)
	var correlation, causation string
	handler := Instrument(http.HandlerFunc(func(_ http.ResponseWriter, r *http.Request) {
		correlation, causation = TraceIDs(r.Context())
	}), "tracing-test")

	request := httptest.NewRequest(http.MethodGet, "/seen", nil)
	request.Header.Set("traceparent", incoming)
	handler.ServeHTTP(httptest.NewRecorder(), request)

	// The caller's trace id, re-punctuated as the UUID a correlation id is. Nothing is invented: it is
	// the same 128 bits, so a log line in the other service and an event here name one transaction.
	if correlation != "4bf92f35-77b3-4da6-a3ce-929d0e0e4736" {
		t.Fatalf("the caller's trace was not continued: %q", correlation)
	}
	// The cause is *this* service's request span, not the caller's — the event was produced by handling
	// this request, and the trace already records which span that one descends from. A span id is 64 bits
	// and a causation id is 128, so it sits in the low half with the high half left zero.
	if len(causation) != 36 || causation[:19] != "00000000-0000-0000-" {
		t.Fatalf("a causation id is a span id in the low half of a UUID, got %q", causation)
	}
}

func TestEveryLineWrittenDuringARequestCarriesItsTrace(t *testing.T) {
	start(t)
	var written bytes.Buffer
	logger := slog.New(TracingHandler{Handler: slog.NewJSONHandler(&written, nil)})
	handler := Instrument(http.HandlerFunc(func(_ http.ResponseWriter, r *http.Request) {
		logger.InfoContext(r.Context(), "handled")
	}), "tracing-test")

	request := httptest.NewRequest(http.MethodGet, "/logged", nil)
	request.Header.Set("traceparent", incoming)
	handler.ServeHTTP(httptest.NewRecorder(), request)

	var record map[string]any
	if err := json.Unmarshal(written.Bytes(), &record); err != nil {
		t.Fatalf("the line was not JSON: %v", err)
	}
	if record["trace_id"] != "4bf92f3577b34da6a3ce929d0e0e4736" {
		t.Fatalf("a log line nobody can tie back to a request: %v", record)
	}
	if record["span_id"] == nil {
		t.Fatalf("the span the line was written inside is missing: %v", record)
	}
}

func TestALineWrittenOutsideARequestCarriesNoTrace(t *testing.T) {
	start(t)
	var written bytes.Buffer
	slog.New(TracingHandler{Handler: slog.NewJSONHandler(&written, nil)}).Info("started")

	var record map[string]any
	if err := json.Unmarshal(written.Bytes(), &record); err != nil {
		t.Fatalf("the line was not JSON: %v", err)
	}
	if _, found := record["trace_id"]; found {
		t.Fatalf("nothing was in flight, so there is no trace to name: %v", record)
	}
}

// collecting replaces the default logger for the duration of a test and hands back what it wrote.
// slog.Warn writes to the process's logger, which is the point — Shutdown reports to whatever the entry
// point installed — so a test that wants to read the line has to be the one that installed it.
func collecting(t *testing.T) *bytes.Buffer {
	t.Helper()
	var written bytes.Buffer
	before := slog.Default()
	slog.SetDefault(slog.New(slog.NewJSONHandler(&written, nil)))
	t.Cleanup(func() { slog.SetDefault(before) })
	return &written
}

func TestAFlushThatFailedIsReportedAndNeverFatal(t *testing.T) {
	// A hand-written stand-in for the provider's own Shutdown, failing the way a collector that has gone
	// away fails. Process exit is the worst moment for a network call to raise, and this is the rule that
	// says it does not — so the rule is driven rather than only described.
	written := collecting(t)
	tracing := &Tracing{flush: func(context.Context) error { return errors.New("collector gone") }}

	tracing.Shutdown(context.Background())

	if !strings.Contains(written.String(), "traces could not be flushed on shutdown") {
		t.Fatalf("a failed flush said nothing: %q", written.String())
	}
	if !strings.Contains(written.String(), "collector gone") {
		t.Fatalf("the reason it failed is missing: %q", written.String())
	}
}

func TestAFlushThatWorkedSaysNothing(t *testing.T) {
	written := collecting(t)
	tracing := &Tracing{flush: func(context.Context) error { return nil }}

	tracing.Shutdown(context.Background())

	if written.Len() != 0 {
		t.Fatalf("a clean shutdown wrote %q", written.String())
	}
}

func TestTheProviderIsWhatIsFlushed(t *testing.T) {
	// The seam above is only honest if the real one is wired to it: StartTracing hands back the
	// provider's own Shutdown, and a nil there would be a panic at exit rather than a warning.
	tracing, err := StartTracing(context.Background(), "tracing-test", "")
	if err != nil {
		t.Fatalf("tracing would not start: %v", err)
	}
	if tracing.flush == nil {
		t.Fatal("nothing would be flushed on shutdown")
	}
	tracing.Shutdown(context.Background())
}

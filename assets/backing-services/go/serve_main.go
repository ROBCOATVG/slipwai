// Command serve runs the service's HTTP entry point.
//
//	make dev
//	cd apps/service && go run ./cmd/serve
//
// This is deliberately the only package in the service with no test. Everything worth asserting about
// the routes is asserted against the handler BuildApp returns, driven by httptest with no socket at all —
// a test that needs a listening port is an integration test wearing an entry point's clothes, and it
// proves the one thing this command does rather than anything the handler decides. What is left here is
// composition: read the environment, build the handler, bind, and shut down when asked.
//
// Nothing here parses the environment either: `config` is one struct over it, checked before anything
// binds, so a variable this service cannot use stops the process with the variable named rather than
// surfacing as a 500 an hour later. HOST, PORT and PUBLIC_BASE_URL carry the defaults `.env.example`
// writes down, and that struct is where they are written.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	// Aliased because the adapter's own package is called `http` too. The alias names which one is the
	// project's, rather than leaving the reader to work out which `http.` they are looking at.
	apphttp "example.com/delivery-starter/adapters/driving/http"
	"example.com/delivery-starter/config"
__FLAGS_IMPORT__
	"example.com/delivery-starter/observability"
__STORE_IMPORT__
)

func main() {
	// Before anything else, so a refusal to start — or a failure to bind — is already in this process's
	// one shape.
	slog.SetDefault(logger())
	// The environment, checked once and before anything binds: a variable this service cannot use stops
	// the process here, with the variable named, rather than surfacing as a 500 an hour later. Nothing
	// below this line reads the environment again — logger() above is the one exception, because the
	// refusal itself has to come out in this process's shape, and it is why the two log variables are
	// deliberately not among the ones config checks.
	settings, err := config.Load()
	if err != nil {
		slog.Error("the environment this service was given cannot be used", "err", err)
		os.Exit(1)
	}
	if err := run(settings); err != nil {
		slog.Error("the service stopped", "err", err)
		os.Exit(1)
	}
}

// How this process logs, decided from the environment and nowhere else.
//
// Structured and on from the first run: a service whose only account of itself is whatever
// fmt.Print somebody reached for is a service nobody can operate, and log/slog is the standard
// library's answer, so this costs no dependency.
//
// JSON by default, because that is what a log shipper reads. LOG_FORMAT=pretty — which `make dev`
// sets — gives the same records in slog's text form, which is what a person watching a terminal
// wants. LOG_LEVEL names the level either way and defaults to info; anything unrecognised is info
// rather than a refusal to start, because a typo in a log variable must never be what stops a
// deployment.
// Wrapped in observability.TracingHandler so every line written while a request is being served carries
// the trace and span it happened inside — the ids are in the context slog is already handed, so no caller
// has to pass them and no caller can forget to.
func logger() *slog.Logger {
	level := slog.LevelInfo
	if err := level.UnmarshalText([]byte(env("LOG_LEVEL", "info"))); err != nil {
		level = slog.LevelInfo
	}
	options := &slog.HandlerOptions{Level: level}
	var handler slog.Handler = slog.NewJSONHandler(os.Stdout, options)
	if env("LOG_FORMAT", "json") == "pretty" {
		handler = slog.NewTextHandler(os.Stdout, options)
	}
	return slog.New(observability.TracingHandler{Handler: handler})
}

func run(settings config.Config) error {
	// SIGTERM is what `docker compose down` and every orchestrator send; os.Interrupt is Ctrl-C. Both
	// cancel the context, and the shutdown below lets the requests already in flight finish — without it
	// a demo's last request dies mid-response and reads as a bug in the slice.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// After the environment is checked and before anything binds: the endpoint is read off the checked
	// settings rather than the environment, and no request exists yet to miss its span. See package
	// observability for why the exporter is the part that waits to be asked for.
	tracing, err := observability.StartTracing(ctx, settings.OTelServiceName, settings.OTelExporterOTLPEndpoint)
	if err != nil {
		return err
	}
__STORE_OPEN__
	server := &http.Server{
		Addr: settings.Address(),
		// The flag source, where this project has one, and the store, where it has one, are handed in
		// here and nowhere else. apphttp.Readiness is what puts /ready in front of the port, so a
		// service whose event store has gone away stops being sent traffic; a project with no store
		// passes nil and gets a route that answers ready with no dependency to ask.
		//
		// Wrapped twice on the way out, and both wrappers are the *process*'s rather than the mux's:
		// observability.Instrument opens a span per request, continuing whatever traceparent the caller
		// sent, and apphttp.Secure carries the headers a browser is told to enforce and the answer to
		// whether this origin may ask at all. The handler a test drives with httptest is the routes and
		// nothing else — instrumentation a test has to install proves nothing — and a preflight is a
		// question no route has an answer to.
		Handler: observability.Instrument(
			apphttp.Secure(
				apphttp.BuildApp(__FLAGS_SOURCE__, apphttp.Readiness(__STORE_ARGUMENT__)),
				settings.CORSAllowedOrigins,
			),
			settings.OTelServiceName,
		),
		// A header-read deadline, so a connection that opens and then says nothing cannot hold a
		// goroutine open indefinitely. net/http has no default for this one.
		ReadHeaderTimeout: 5 * time.Second,
	}

	// Buffered and never closed: a closed channel reads as a nil error immediately, which would make the
	// select below treat a healthy server as a failed one and exit before serving anything.
	failed := make(chan error, 1)
	go func() {
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			failed <- err
		}
	}()

	// PUBLIC_BASE_URL rather than the bound address, because behind a proxy or a tunnel the two differ
	// and the address worth reporting is the one somebody can open.
	slog.Info("service listening",
		"url", settings.ReportedURL(),
		"service", settings.OTelServiceName,
		"exportingTraces", tracing.Exporting,
	)

	select {
	case err := <-failed:
		return err
	case <-ctx.Done():
	}

	shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	// The server first, then the tracer: the spans of the requests still in flight are flushed rather
	// than dropped on the way out.
	err = server.Shutdown(shutdown)
	tracing.Shutdown(shutdown)
	return err
}

func env(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

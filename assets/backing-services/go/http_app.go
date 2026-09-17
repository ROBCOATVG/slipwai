// Package http holds the inbound HTTP driving adapter.
//
// A driving adapter parses untrusted input into typed commands, calls a use case, and renders the
// outcome. It holds no business rules and makes no authorisation decision — authorisation is
// decided inside the use case, because a rule enforced in a route handler is a rule that a second
// entry point will not enforce.
//
// Status mapping belongs here precisely because the domain speaks business vocabulary:
//
//   - 400 — schema failure: the shape is wrong
//   - 422 — business rejection: the shape is fine, the rule says no
//   - 404 — not found, INCLUDING another tenant's resource, so existence is not leaked
//   - 409 — a conflict the caller may retry differently, which is where a version conflict from
//     the event store surfaces: the store returns it as a value, and this is the layer that
//     gives it a status
//
// "Parses untrusted input" is a type's job here and not a handler's. There is no framework compiling a
// schema, so the request and response structs ARE the schema: DecodeJSON refuses a body carrying a field
// the type does not name, and the contract those types make is written down in openapi.yaml beside the
// service, which a test in this package holds to the routes below.
//
// net/http's ServeMux, not a framework: routing, method matching and path parameters have been in
// the standard library since Go 1.22, and a dependency that only supplies those is a dependency
// with nothing left to buy.
package http

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
)

// RouteRegistrar mounts a slice's routes onto the mux. Slices are registered from the composition
// root, so this package never grows a list of the application's features.
type RouteRegistrar func(mux *http.ServeMux)

// FlagSnapshot is just enough of the flag reader's Source for this package to serve one.
//
// Declared here rather than imported: the reader package exists only in a project with somewhere to
// deploy, so importing it would not build in one without. Go's interfaces are satisfied implicitly, so
// this package needs no import, stays the same in every project, and is exercised by its own tests either
// way — while a project with no flags passes nil, and then has no /api/flags route rather than an inert
// one.
type FlagSnapshot interface {
	Snapshot() map[string]string
}

// Health is what GET /health answers. A named type rather than a map literal, so the probe's shape is
// declared where every other route's is and openapi.yaml has something to describe.
type Health struct {
	Status string `json:"status"`
}

// BuildApp returns the handler for the whole service. A nil flags is a project with none.
func BuildApp(flags FlagSnapshot, registrars ...RouteRegistrar) http.Handler {
	mux := http.NewServeMux()

	// Liveness: this process is up and answering. Unconditional on purpose — it asks nothing of any
	// dependency, because a liveness probe that fails when a database is unreachable gets the process
	// restarted when the only thing wrong is somewhere else. What gates traffic is /ready, which
	// Readiness below registers.
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		WriteJSON(w, http.StatusOK, Health{Status: "ok"})
	})

	// This environment's feature flags, for the browser app — which cannot read them itself.
	//
	// Under /api because that is this service's product surface and a browser calls it; /health sits
	// outside it because it is a probe. vite.config.ts forwards /api with the prefix intact and
	// CloudFront's /api/* behaviour rewrites nothing, so this is the one path in both places.
	//
	// no-store because the answer is what the environment is set to now: a flipped flag that a cache
	// still hides is the flip looking broken.
	if flags != nil {
		mux.HandleFunc("GET /api/flags", func(w http.ResponseWriter, _ *http.Request) {
			w.Header().Set("Cache-Control", "no-store")
			WriteJSON(w, http.StatusOK, flags.Snapshot())
		})
	}

	for _, register := range registrars {
		register(mux)
	}

	// Registered last and at the root, so it answers anything no other route claimed.
	//
	// net/http's own fallback is `http.NotFound`, which writes the plain text "404 page not
	// found" — safe today, but the moment somebody reaches for `http.Error(w, r.URL.Path, ...)`
	// the URL is in the response body, and from there in every proxy and access log along the
	// way. For any project whose URLs carry a credential — a no-login link, a password-reset
	// path, a signed download — the 404 is the disclosure, and it discloses to whoever probed
	// for it.
	//
	// It is also what makes the 404 above honest. That mapping already promises another tenant's
	// resource is indistinguishable from one that never existed; a handler that reflects the path
	// undercuts the promise.
	//
	// The reply says nothing the caller did not already know: no path, no method, no hint whether
	// the route exists under a different verb.
	mux.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
		WriteJSON(w, http.StatusNotFound, map[string]string{"error": "notFound"})
	})

	return mux
}

// ReadinessProbe is just enough of the event-store port for this package to probe one.
//
// Declared here rather than imported, for the reason FlagSnapshot is and a stronger one: this package is
// the HTTP adapter of any project on this transport, and a project on the standard profile has no event
// store and no port to import. Go satisfies interfaces implicitly, so every store adapter already is one.
//
// Head and nothing else. It is the cheapest honest question the port already answers — the last global
// position in the log, or zero when it is empty — so a readiness probe needs no method of its own and the
// port is not widened to carry one. A store that cannot answer it cannot serve a request either.
type ReadinessProbe interface {
	Head(ctx context.Context) (int64, error)
}

// Readiness registers /ready: whether this service should be sent traffic.
//
// A different question from whether it is running. /health above is liveness — the process is up and
// answering — and it is deliberately unconditional: a probe that goes red because a dependency is down
// gets the process killed rather than taken out of the pool. This one asks the driven port the service
// cannot work without, through the port and never through an adapter, so an event store that has gone
// away is reported as "do not send me traffic" instead of staying invisible until the first real request
// fails.
//
// A registrar rather than a route inside BuildApp, because the store is the composition root's to open
// and hand over, and BuildApp is shared with every project on this transport — including the ones with no
// store to hand it. Those pass nil and get a route that answers ready with no dependency to ask, which is
// the truth for a project whose only driven port is the clock.
//
// The failure reason is logged and not sent. A caller learns the category and no more: what is wrong with
// this service's dependencies is not something an unauthenticated prober needs, and a connection string in
// a driver's error message is exactly what would otherwise end up in one.
func Readiness(store ReadinessProbe) RouteRegistrar {
	return func(mux *http.ServeMux) {
		mux.HandleFunc("GET /ready", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Cache-Control", "no-store")
			if store != nil {
				if _, err := store.Head(r.Context()); err != nil {
					slog.Error("the event store did not answer; reporting not ready", "err", err)
					WriteJSON(w, http.StatusServiceUnavailable,
						map[string]string{"status": "unready", "reason": "eventStore"})
					return
				}
			}
			WriteJSON(w, http.StatusOK, map[string]string{"status": "ready"})
		})
	}
}

// WriteJSON renders a response body, so every route reports success and failure identically.
func WriteJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	// Encoded before the status is written, so a body that cannot be marshalled does not leave a
	// 200 header on a truncated response.
	encoded, err := json.Marshal(body)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"error":"responseEncodingFailed"}`))
		return
	}
	w.WriteHeader(status)
	_, _ = w.Write(encoded)
}

// DecodeJSON reads a request body into T, or answers 400 and reports that it did not.
//
// This is the whole of "a driving adapter parses untrusted input into typed commands" on this backend.
// There is no framework here to compile a schema, so the type IS the schema: the fields it names are the
// fields this route accepts, and DisallowUnknownFields is what makes that true rather than aspirational.
// Without it encoding/json quietly ignores anything the type does not name, so `{"discuont": 10}` reaches
// a handler as a request with no discount and the caller is told their field worked.
//
// The handler's whole obligation is the two-line opening:
//
//	order, ok := apphttp.DecodeJSON[PlaceOrder](w, r)
//	if !ok {
//		return
//	}
//
// The 400 has already been written when ok is false, so there is one 400 body in this service and no
// route has to build one. What comes back names the field and the rule and never the value: a validation
// error on a field holding a token or a password must not quote it back.
func DecodeJSON[T any](w http.ResponseWriter, r *http.Request) (T, bool) {
	var into T
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&into); err != nil {
		var zero T
		WriteJSON(w, http.StatusBadRequest, schemaFailureFor(err))
		return zero, false
	}
	// A body carrying a second JSON value after the first is not one document, and taking the first
	// and dropping the rest is the kind of silence this function exists to remove.
	if decoder.More() {
		var zero T
		WriteJSON(w, http.StatusBadRequest, SchemaFailure("", "body must hold exactly one JSON value"))
		return zero, false
	}
	return into, true
}

// schemaFailureFor turns what encoding/json refused into the field and the rule, and nothing else.
func schemaFailureFor(err error) map[string]string {
	var wrongType *json.UnmarshalTypeError
	if errors.As(err, &wrongType) {
		return SchemaFailure(wrongType.Field, fmt.Sprintf("must be %s", wrongType.Type))
	}
	// encoding/json reports this one as a message and nothing else, so the field is read back out of
	// it. The quoted part is the caller's own key, never their value.
	const unknown = `json: unknown field `
	if message := err.Error(); strings.HasPrefix(message, unknown) {
		field := strings.Trim(strings.TrimPrefix(message, unknown), `"`)
		return SchemaFailure(field, "is not a field this route accepts")
	}
	return SchemaFailure("", "invalid request body")
}

// SchemaFailure is the 400 body, so every route reports a bad shape the same way.
//
// The offending value is deliberately absent: a validation error on a field holding a token or a
// password must not quote it back.
func SchemaFailure(field, message string) map[string]string {
	if field == "" {
		field = "(root)"
	}
	if message == "" {
		message = "invalid request body"
	}
	return map[string]string{
		"error":   "schemaValidationFailed",
		"field":   field,
		"message": message,
	}
}

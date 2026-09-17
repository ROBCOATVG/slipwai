package http

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

// answering is a handler that records nothing and answers 200, so what is asserted below is the wrapper.
func answering() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) })
}

func TestEveryResponseCarriesTheSecurityHeaders(t *testing.T) {
	recorder := httptest.NewRecorder()
	Secure(answering(), nil).ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/health", nil))

	// Nosniff is the one that matters most for a JSON API: without it a browser may decide a response is
	// HTML because of what is inside it, and runs what it finds.
	if got := recorder.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Fatalf("X-Content-Type-Options was %q", got)
	}
	if got := recorder.Header().Get("X-Frame-Options"); got != "DENY" {
		t.Fatalf("X-Frame-Options was %q", got)
	}
	if recorder.Header().Get("Content-Security-Policy") == "" {
		t.Fatal("no content security policy was sent")
	}
}

func TestACrossOriginRequestIsPermittedNothingUntilAnOriginIsAllowed(t *testing.T) {
	// Empty is the default, and it is same-origin only: the response carries no permission at all, so
	// the browser refuses to hand it to the page that asked.
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	request.Header.Set("Origin", "http://evil.example")

	Secure(answering(), nil).ServeHTTP(recorder, request)

	if got := recorder.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Fatalf("an origin nobody allowed was permitted: %q", got)
	}
	// Still varies by origin: without it a shared cache can serve one origin's response to another.
	if got := recorder.Header().Get("Vary"); got != "Origin" {
		t.Fatalf("Vary was %q", got)
	}
}

func TestExactlyTheOriginsItWasGivenArePermitted(t *testing.T) {
	handler := Secure(answering(), []string{"http://localhost:5173"})

	allowed := httptest.NewRecorder()
	permitted := httptest.NewRequest(http.MethodGet, "/health", nil)
	permitted.Header.Set("Origin", "http://localhost:5173")
	handler.ServeHTTP(allowed, permitted)

	refused := httptest.NewRecorder()
	// A near miss is a miss: one port out is a different origin, and nothing here guesses.
	other := httptest.NewRequest(http.MethodGet, "/health", nil)
	other.Header.Set("Origin", "http://localhost:5174")
	handler.ServeHTTP(refused, other)

	if got := allowed.Header().Get("Access-Control-Allow-Origin"); got != "http://localhost:5173" {
		t.Fatalf("the allowed origin was not permitted: %q", got)
	}
	if got := refused.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Fatalf("an origin nobody allowed was permitted: %q", got)
	}
}

func TestAPreflightIsAnsweredBeforeAnyRouteRuns(t *testing.T) {
	reached := false
	handler := Secure(http.HandlerFunc(func(http.ResponseWriter, *http.Request) { reached = true }),
		[]string{"http://localhost:5173"})

	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodOptions, "/api/flags", nil)
	request.Header.Set("Origin", "http://localhost:5173")
	request.Header.Set("Access-Control-Request-Method", "GET")
	request.Header.Set("Access-Control-Request-Headers", "authorization")
	handler.ServeHTTP(recorder, request)

	if reached {
		t.Fatal("a preflight is a question about a request, not a request; no route should have run")
	}
	if recorder.Code != http.StatusNoContent {
		t.Fatalf("a preflight was answered %d", recorder.Code)
	}
	if got := recorder.Header().Get("Access-Control-Allow-Headers"); got != "authorization" {
		t.Fatalf("Access-Control-Allow-Headers was %q", got)
	}
}

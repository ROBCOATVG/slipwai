package http_test

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	apphttp "example.com/delivery-starter/adapters/driving/http"
)

// Edge tests: the outermost surface, exercised through the real router rather than around it.
//
// httptest.NewRecorder runs a real request through the real mux with no socket, so these stay in
// `make verify` — an entry-point test that needs a listening port is an integration test wearing
// the wrong name.
func response(t *testing.T, handler http.Handler, method, target string) *httptest.ResponseRecorder {
	t.Helper()
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, httptest.NewRequest(method, target, nil))
	return recorder
}

func TestReportsLiveness(t *testing.T) {
	recorder := response(t, apphttp.BuildApp(nil), http.MethodGet, "/health")

	if recorder.Code != http.StatusOK {
		t.Fatalf("status %d", recorder.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("body is not JSON: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("body is %v", body)
	}
}

// emptyLog is a store with nothing in it, which is what a healthy new project's log is.
type emptyLog struct{}

func (emptyLog) Head(context.Context) (int64, error) { return 0, nil }

// unreachableLog is a store that cannot answer — written here, by hand, and that is the rule rather
// than an accident. A mocking framework would let this suite assert that Head was *called*, which
// proves nothing about what the route does with the answer. What matters is the two answers the port
// can give and the two statuses they become.
type unreachableLog struct{}

func (unreachableLog) Head(context.Context) (int64, error) {
	return 0, errors.New("connection refused")
}

func TestIsReadyWhenTheEventStoreAnswers(t *testing.T) {
	handler := apphttp.BuildApp(nil, apphttp.Readiness(emptyLog{}))
	recorder := response(t, handler, http.MethodGet, "/ready")

	if recorder.Code != http.StatusOK {
		t.Fatalf("status %d", recorder.Code)
	}
	if !strings.Contains(recorder.Body.String(), `"status":"ready"`) {
		t.Fatalf("body is %s", recorder.Body.String())
	}
}

func TestIsNotReadyWhenTheEventStoreDoesNotAnswer(t *testing.T) {
	handler := apphttp.BuildApp(nil, apphttp.Readiness(unreachableLog{}))
	recorder := response(t, handler, http.MethodGet, "/ready")

	if recorder.Code != http.StatusServiceUnavailable {
		t.Fatalf("status %d", recorder.Code)
	}
	body := recorder.Body.String()
	if !strings.Contains(body, `"reason":"eventStore"`) {
		t.Fatalf("body is %s", body)
	}
	// The driver's own message — which is where a connection string ends up — stays in the log.
	if strings.Contains(body, "connection refused") {
		t.Fatalf("the reply quotes the driver: %s", body)
	}
}

func TestIsReadyWithNothingToAskWhenTheProjectHasNoStore(t *testing.T) {
	handler := apphttp.BuildApp(nil, apphttp.Readiness(nil))
	recorder := response(t, handler, http.MethodGet, "/ready")

	if recorder.Code != http.StatusOK {
		t.Fatalf("status %d", recorder.Code)
	}
	// Liveness is still liveness: /health answers whatever the dependencies are doing.
	if response(t, handler, http.MethodGet, "/health").Code != http.StatusOK {
		t.Fatal("/health did not answer")
	}
}

// A 404 body that repeats the URL puts whatever the URL carried into every access log
// downstream. Asserted rather than assumed, because it is the kind of regression a
// well-meaning custom handler reintroduces silently.
func TestDoesNotEchoTheRequestedPathBackOnA404(t *testing.T) {
	recorder := response(t, apphttp.BuildApp(nil), http.MethodGet, "/orders/tok-live-abc123")

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status %d", recorder.Code)
	}
	body := recorder.Body.String()
	if !strings.Contains(body, `"error":"notFound"`) {
		t.Fatalf("body is %q", body)
	}
	if strings.Contains(body, "tok-live-abc123") || strings.Contains(body, "/orders") {
		t.Fatalf("the 404 echoed the request: %q", body)
	}
}

func TestDoesNotRevealThatAPathExistsUnderADifferentMethod(t *testing.T) {
	recorder := response(t, apphttp.BuildApp(nil), http.MethodPost, "/health")

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status %d", recorder.Code)
	}
	if !strings.Contains(recorder.Body.String(), `"error":"notFound"`) {
		t.Fatalf("body is %q", recorder.Body.String())
	}
}

func TestRegistersTheRoutesItIsGivenAndHoldsNoneOfItsOwn(t *testing.T) {
	handler := apphttp.BuildApp(nil, func(mux *http.ServeMux) {
		mux.HandleFunc("GET /orders/{id}", func(w http.ResponseWriter, r *http.Request) {
			apphttp.WriteJSON(w, http.StatusOK, map[string]string{"id": r.PathValue("id")})
		})
	})

	recorder := response(t, handler, http.MethodGet, "/orders/order-1")

	if recorder.Code != http.StatusOK {
		t.Fatalf("status %d", recorder.Code)
	}
	if !strings.Contains(recorder.Body.String(), `"id":"order-1"`) {
		t.Fatalf("body is %q", recorder.Body.String())
	}
}

func TestReportsASchemaFailureInOneShape(t *testing.T) {
	failure := apphttp.SchemaFailure("customer.email", "must be an email")
	if failure["error"] != "schemaValidationFailed" || failure["field"] != "customer.email" {
		t.Fatalf("failure is %v", failure)
	}

	blank := apphttp.SchemaFailure("", "")
	if blank["field"] != "(root)" || blank["message"] != "invalid request body" {
		t.Fatalf("blank failure is %v", blank)
	}
}

// A slice's request type. The fields it names are the fields the route accepts, which is the whole of
// the schema on this backend.
type placeOrder struct {
	SKU string `json:"sku"`
}

// decoded drives DecodeJSON the way a route does, and reports what the caller would have seen.
func decoded(t *testing.T, body string) (placeOrder, *httptest.ResponseRecorder, bool) {
	t.Helper()
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/orders", strings.NewReader(body))
	order, ok := apphttp.DecodeJSON[placeOrder](recorder, request)
	return order, recorder, ok
}

func TestDecodeJSONReadsABodyTheTypeNames(t *testing.T) {
	order, _, ok := decoded(t, `{"sku":"sku-1"}`)

	if !ok {
		t.Fatalf("a body the type names was refused")
	}
	if order.SKU != "sku-1" {
		t.Fatalf("order is %+v", order)
	}
}

// encoding/json ignores an unknown field unless it is told not to, so `{"discuont": 10}` would reach a
// handler as a request with no discount and the caller would be told their field worked.
func TestDecodeJSONRefusesAFieldTheTypeDoesNotName(t *testing.T) {
	_, recorder, ok := decoded(t, `{"sku":"sku-1","discuont":10}`)

	if ok {
		t.Fatalf("a field the type does not name was accepted")
	}
	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status %d", recorder.Code)
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("body is not JSON: %v", err)
	}
	if body["error"] != "schemaValidationFailed" || body["field"] != "discuont" {
		t.Fatalf("body is %v", body)
	}
}

func TestDecodeJSONRefusesAFieldOfTheWrongTypeWithoutQuotingIt(t *testing.T) {
	_, recorder, ok := decoded(t, `{"sku":{"secret":"not-returned"}}`)

	if ok {
		t.Fatalf("an object where a string belongs was accepted")
	}
	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status %d", recorder.Code)
	}
	// The rejected input is not part of the reply: a validation error on a field holding a token must
	// not quote it.
	if strings.Contains(recorder.Body.String(), "tok-live-abc123") {
		t.Fatalf("the reply quoted the input: %q", recorder.Body.String())
	}
	if !strings.Contains(recorder.Body.String(), `"field":"sku"`) {
		t.Fatalf("body is %q", recorder.Body.String())
	}
}

func TestDecodeJSONRefusesABodyThatIsNotOneDocument(t *testing.T) {
	_, recorder, ok := decoded(t, `{"sku":"sku-1"}{"sku":"sku-2"}`)

	if ok || recorder.Code != http.StatusBadRequest {
		t.Fatalf("ok=%v status=%d", ok, recorder.Code)
	}
}

type stubFlags struct {
	flags map[string]string
}

func (s stubFlags) Snapshot() map[string]string { return s.flags }

func TestBuildAppServesThisEnvironmentsFlagsWhenGivenASource(t *testing.T) {
	// A browser cannot read this environment, so the service answers for it. Snapshot is the reader's
	// second question and this route is the only caller of it.
	handler := apphttp.BuildApp(stubFlags{flags: map[string]string{"checkout-v2": "on"}})

	recorder := response(t, handler, http.MethodGet, "/api/flags")

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusOK)
	}
	// The answer is what the environment is set to now: a flipped flag a cache still hides is the flip
	// looking broken.
	if got := recorder.Header().Get("Cache-Control"); got != "no-store" {
		t.Fatalf("Cache-Control = %q, want %q", got, "no-store")
	}
	var body map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("decoding the body: %v", err)
	}
	if body["checkout-v2"] != "on" {
		t.Fatalf("body = %v, want checkout-v2=on", body)
	}
}

func TestBuildAppHasNoFlagsRouteWhenGivenNoSource(t *testing.T) {
	// --target none has nowhere to declare a flag, so this route is absent rather than answering an empty
	// object: an endpoint that always returns nothing reads as a capability the project does not have.
	recorder := response(t, apphttp.BuildApp(nil), http.MethodGet, "/api/flags")

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusNotFound)
	}
}

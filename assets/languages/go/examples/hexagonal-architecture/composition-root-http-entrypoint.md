```go
package httpapi

import (
	"encoding/json"
	"net/http"
	"os"
)

// CreateOrder is a serverless-style executable entrypoint: inline
// composition + driving adapter. Valid only while this object graph remains
// trivial and unshared.
func CreateOrder(w http.ResponseWriter, r *http.Request) {
	db := openDB()

	// Wire adapters.
	repo := NewPostgresOrderRepository(db)
	gateway := NewStripeGateway(os.Getenv("STRIPE_KEY"))
	orderPlacement := NewOrderPlacement(repo, gateway)

	// Translate transport syntax separately from request-schema validation.
	var raw json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		writeJSONError(w, http.StatusBadRequest, "malformed-json")
		return
	}

	var cmd CreateOrderCommand
	if err := json.Unmarshal(raw, &cmd); err != nil || !cmd.Valid() {
		writeJSONError(w, http.StatusUnprocessableEntity, "invalid-body")
		return
	}

	// Call use case.
	result, err := orderPlacement.PlaceOrder(r.Context(), cmd.ToNewOrder())
	if err != nil {
		writeJSONError(w, http.StatusInternalServerError, "internal-error")
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func writeJSONError(w http.ResponseWriter, status int, reason string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"error": reason})
}
```

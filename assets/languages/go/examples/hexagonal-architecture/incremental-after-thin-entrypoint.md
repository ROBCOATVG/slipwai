```go
package httpapi

import (
	"encoding/json"
	"net/http"
)

// Deduct is a serverless-style executable entrypoint: inline composition +
// driving adapter. Valid only while this object graph remains trivial and
// unshared.
func Deduct(w http.ResponseWriter, r *http.Request) {
	// Authentication owns the provider-free principal; the body cannot select a user.
	principal, ok := authenticateRequest(r)
	if !ok {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	db := openDB()

	// Wire adapters.
	userRepo := NewPostgresUserRepository(db)
	var balanceDeduction ForDeductingUserBalances = &UserBalanceDeduction{UserRepo: userRepo}

	// Translate transport syntax separately from request-schema validation.
	var body struct {
		AmountMinorUnits int64  `json:"amountMinorUnits"`
		Currency         string `json:"currency"`
	}
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&body); err != nil {
		writeJSONError(w, http.StatusBadRequest, "malformed-json")
		return
	}

	// Call use case.
	result, err := balanceDeduction.DeductUserBalance(r.Context(), DeductUserBalanceCommand{
		Principal: principal,
		Amount:    Money{MinorUnits: body.AmountMinorUnits, Currency: body.Currency},
	})
	if err != nil {
		writeJSONError(w, http.StatusInternalServerError, "internal-error")
		return
	}

	if status, reason, isFailure := deductFailureStatus(result.Outcome); isFailure {
		writeJSONError(w, status, reason)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"balance": result.User.Balance})
}

func deductFailureStatus(outcome DeductUserBalanceOutcome) (status int, reason string, isFailure bool) {
	switch outcome {
	case DeductUserBalanceNotFound:
		return http.StatusNotFound, "not-found", true
	case DeductUserBalanceConcurrentChange:
		return http.StatusConflict, "concurrent-change", true
	case DeductUserBalanceNonPositiveAmount:
		return http.StatusUnprocessableEntity, "non-positive-amount", true
	case DeductUserBalanceCurrencyMismatch:
		return http.StatusUnprocessableEntity, "currency-mismatch", true
	case DeductUserBalanceInsufficientBalance:
		return http.StatusUnprocessableEntity, "insufficient-balance", true
	default:
		return 0, "", false
	}
}

func writeJSONError(w http.ResponseWriter, status int, reason string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"error": reason})
}
```

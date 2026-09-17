```go
package httpapi

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
)

// Deduct is the BEFORE state — everything crammed into the route handler.
func Deduct(w http.ResponseWriter, r *http.Request) {
	principal, ok := authenticateRequest(r)
	if !ok {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

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

	var balanceMinorUnits int64
	var currency string
	err := db.QueryRowContext(r.Context(),
		`SELECT balance_minor_units, currency FROM users WHERE id = $1`, principal.UserID,
	).Scan(&balanceMinorUnits, &currency)
	if errors.Is(err, sql.ErrNoRows) {
		writeJSONError(w, http.StatusNotFound, "not found")
		return
	}
	if err != nil {
		writeJSONError(w, http.StatusInternalServerError, "internal-error")
		return
	}

	if body.AmountMinorUnits <= 0 {
		writeJSONError(w, http.StatusUnprocessableEntity, "invalid amount")
		return
	}
	if body.Currency != currency {
		writeJSONError(w, http.StatusUnprocessableEntity, "currency mismatch")
		return
	}
	if balanceMinorUnits < body.AmountMinorUnits {
		writeJSONError(w, http.StatusUnprocessableEntity, "insufficient")
		return
	}

	newBalance := balanceMinorUnits - body.AmountMinorUnits
	if _, err := db.ExecContext(r.Context(),
		`UPDATE users SET balance_minor_units = $1 WHERE id = $2`, newBalance, principal.UserID,
	); err != nil {
		writeJSONError(w, http.StatusInternalServerError, "internal-error")
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"balanceMinorUnits": newBalance,
		"currency":          currency,
	})
}

func writeJSONError(w http.ResponseWriter, status int, reason string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]string{"error": reason})
}
```

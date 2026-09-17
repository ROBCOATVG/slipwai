```go
// Package httpadapter is the driving adapter at the serverless HTTP entry
// point: gifting/adapters/driving/http/occasions_pledge.go
package httpadapter

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"strings"

	"gifting/adapters/driven/postgres"
	"gifting/hexagon/application"
	"gifting/hexagon/domain"
)

// Authenticator authenticates an inbound request and returns the pledger
// principal. The production implementation is the only constructor of
// application.AuthenticatedPledger; the request body cannot forge one.
type Authenticator func(*http.Request) (application.AuthenticatedPledger, bool)

// NewPostPledgeHandler is the trivial executable entrypoint for
// POST /occasions/{id}/pledge. It combines a driving adapter with inline
// composition because this is the deployment entrypoint and its graph is
// trivial; a larger graph belongs in an explicit composition root instead.
func NewPostPledgeHandler(db *sql.DB, authenticate Authenticator) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// The authentication adapter is the only production constructor for
		// this provider-free principal; the request body cannot choose the actor.
		principal, ok := authenticate(r)
		if !ok {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
			return
		}

		occasionID, ok := parseOccasionID(r.PathValue("id"))
		if !ok {
			writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"error": "invalid-path"})
			return
		}

		raw, err := io.ReadAll(r.Body)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "malformed-json"})
			return
		}
		var parsed map[string]any
		// The narrowly scoped JSON parse maps malformed transport syntax to 400;
		// parsePledgeBody maps syntactically valid but invalid request data to 422.
		if err := json.Unmarshal(raw, &parsed); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "malformed-json"})
			return
		}

		amount, ok := parsePledgeBody(parsed)
		if !ok {
			writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"error": "invalid-body"})
			return
		}

		// Inline composition: this handler is the executable entrypoint and
		// the graph is trivial.
		persistence := postgres.PledgePersistence{DB: db}
		pledging := application.PledgingToOccasions{Persistence: persistence}

		result, err := pledging.PledgeToOccasion(r.Context(), application.PledgeToOccasionCommand{
			PledgeID:   newPledgeID(),
			OccasionID: occasionID,
			Principal:  principal,
			Amount:     amount,
		})
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal-error"})
			return
		}

		// Translate result to HTTP; status selection is protocol translation,
		// not business policy.
		if !result.Ok {
			status := http.StatusUnprocessableEntity
			switch result.Reason {
			case application.ReasonNotFound:
				status = http.StatusNotFound
			case application.ReasonConcurrentChange:
				status = http.StatusConflict
			}
			writeJSON(w, status, map[string]string{"error": string(result.Reason)})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"pledged": result.Occasion.TotalPledged})
	}
}

func parseOccasionID(raw string) (domain.OccasionID, bool) {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return "", false
	}
	return domain.OccasionID(trimmed), true
}

// parsePledgeBody is a strict schema: only "amount" is accepted; contributor
// or tenant fields in the body are rejected, never trusted from the request.
func parsePledgeBody(raw map[string]any) (domain.Money, bool) {
	if len(raw) != 1 {
		return domain.Money{}, false
	}
	amountRaw, ok := raw["amount"].(map[string]any)
	if !ok || len(amountRaw) != 2 {
		return domain.Money{}, false
	}
	minorUnits, ok := amountRaw["minor_units"].(float64)
	if !ok || minorUnits < 0 || minorUnits != float64(int64(minorUnits)) {
		return domain.Money{}, false
	}
	currencyRaw, ok := amountRaw["currency"].(string)
	if !ok {
		return domain.Money{}, false
	}
	currency := domain.Currency(currencyRaw)
	switch currency {
	case domain.GBP, domain.USD, domain.EUR:
	default:
		return domain.Money{}, false
	}
	return domain.Money{MinorUnits: int64(minorUnits), Currency: currency}, true
}

func newPledgeID() domain.PledgeID {
	buf := make([]byte, 16)
	_, _ = rand.Read(buf)
	return domain.PledgeID(hex.EncodeToString(buf))
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
```

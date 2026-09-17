```go
package httpapi

import (
	"encoding/json"
	"net/http"
)

// PledgeToOccasion is a driving adapter: extract and validate auth, then
// delegate to the use case.
func (h *Handler) PledgeToOccasion(w http.ResponseWriter, r *http.Request) {
	principal, ok := h.Authenticator.Authenticate(r) // sole production constructor
	if !ok {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	pledging := h.Pledging // application.ForPledgingToOccasions

	var raw json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		writeJSONError(w, http.StatusBadRequest, "malformed-json")
		return
	}

	var body PledgeBody
	if err := json.Unmarshal(raw, &body); err != nil || !body.Valid() {
		writeJSONError(w, http.StatusUnprocessableEntity, "invalid-body")
		return
	}

	// Strict body has no actor/tenant fields; the principal owns attribution.
	result, err := pledging.PledgeToOccasion(r.Context(), body.ToCommand(principal))
	if err != nil {
		writeJSONError(w, http.StatusInternalServerError, "internal-error")
		return
	}
	WriteResult(w, result)
}
```

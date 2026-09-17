```go
package httpapi

import (
	"context"
	"database/sql"
	"encoding/json"
	"log/slog"
	"net/http"

	"gifting/hexagon/domain"
)

// PledgeToOccasion is a driving adapter: log the request/response cycle.
func (h *Handler) PledgeToOccasion(w http.ResponseWriter, r *http.Request) {
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

	result, err := h.Pledging.PledgeToOccasion(r.Context(), body.ToCommand())
	if err != nil {
		writeJSONError(w, http.StatusInternalServerError, "internal-error")
		return
	}
	if !result.Ok {
		h.Logger.Warn("pledge rejected", "reason", result.Reason, "occasion_id", body.OccasionID)
	}
	WriteResult(w, result)
}

// OccasionRepository is a driven adapter: log infrastructure interactions.
type OccasionRepository struct {
	DB     *sql.DB
	Logger *slog.Logger
}

func (r OccasionRepository) Save(ctx context.Context, occasion domain.Occasion) error {
	if _, err := r.DB.ExecContext(ctx, insertOccasionSQL, toRow(occasion)); err != nil {
		return err
	}
	r.Logger.Debug("occasion saved", "id", occasion.ID)
	return nil
}
```

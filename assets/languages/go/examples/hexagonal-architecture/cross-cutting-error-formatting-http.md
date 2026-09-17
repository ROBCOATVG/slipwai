```go
package httpapi

import (
	"encoding/json"
	"net/http"

	"gifting/hexagon/application"
	"gifting/hexagon/domain"
)

// statusByReason maps domain/application rejection reasons to HTTP status
// codes via an explicit table, not ad hoc if/else.
var statusByReason = map[domain.RejectionReason]int{
	application.ReasonNotFound:         http.StatusNotFound,
	application.ReasonConcurrentChange: http.StatusConflict,
	domain.ReasonNonPositiveAmount:     http.StatusUnprocessableEntity,
	domain.ReasonCurrencyMismatch:      http.StatusUnprocessableEntity,
	domain.ReasonExceedsBudget:         http.StatusUnprocessableEntity,
	domain.ReasonFundingClosed:         http.StatusUnprocessableEntity,
}

// WriteResult is the driving adapter: it translates a domain/application
// result into an HTTP-shaped response, never the other way around.
func WriteResult(w http.ResponseWriter, result application.PledgeResult) {
	w.Header().Set("Content-Type", "application/json")
	if result.Ok {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]domain.Money{"pledged": result.Occasion.TotalPledged})
		return
	}
	w.WriteHeader(statusByReason[result.Reason])
	json.NewEncoder(w).Encode(map[string]domain.RejectionReason{"error": result.Reason})
}
```

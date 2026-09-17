```go
package application

import (
	"context"
	"log/slog"

	"gifting/hexagon/domain"
)

// PledgeInstrumentation is a driven port, application-owned because the use
// case consumes it. Probe methods take domain types only, return nothing
// callers branch on, and never influence control flow. No log levels, no
// metric names, no framework types.
type PledgeInstrumentation interface {
	PledgeRejected(reason domain.RejectionReason, occasionID domain.OccasionID)
	PledgeAccepted(amount domain.Money, occasionID domain.OccasionID)
}

// PledgingToOccasions announces domain facts through the probe; the adapter
// decides severity.
type PledgingToOccasions struct {
	Persistence     PledgePersistence
	Instrumentation PledgeInstrumentation
}

func (uc PledgingToOccasions) PledgeToOccasion(ctx context.Context, cmd PledgeToOccasionCommand) (PledgeResult, error) {
	// ... calls uc.Instrumentation.PledgeRejected/PledgeAccepted as outcomes occur
	return PledgeResult{}, nil
}

// TelemetryPledgeInstrumentation is the adapter: it decides severity, metric
// names, and span attributes — swappable without touching a use case.
type TelemetryPledgeInstrumentation struct {
	Logger *slog.Logger
}

var _ PledgeInstrumentation = TelemetryPledgeInstrumentation{}

func (a TelemetryPledgeInstrumentation) PledgeRejected(reason domain.RejectionReason, occasionID domain.OccasionID) {
	a.Logger.Warn("pledge rejected", "reason", reason, "occasion_id", occasionID)
}

func (a TelemetryPledgeInstrumentation) PledgeAccepted(amount domain.Money, occasionID domain.OccasionID) {
	a.Logger.Info("pledge accepted",
		"minor_units", amount.MinorUnits,
		"currency", amount.Currency,
		"occasion_id", occasionID,
	)
}
```

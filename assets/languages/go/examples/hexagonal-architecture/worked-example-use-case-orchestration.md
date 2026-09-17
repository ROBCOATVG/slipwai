```go
// gifting/hexagon/application/pledge_to_occasion.go — use case
package application

import (
	"context"

	"gifting/hexagon/domain"
)

// PledgingToOccasions implements ForPledgingToOccasions. It holds its driven
// port as a plain field and returns (PledgeResult, error): error is reserved
// for unexpected infrastructure failure, never for an expected business
// outcome such as funding-closed or concurrent-change.
type PledgingToOccasions struct {
	Persistence PledgePersistence
}

var _ ForPledgingToOccasions = PledgingToOccasions{}

func (uc PledgingToOccasions) PledgeToOccasion(ctx context.Context, cmd PledgeToOccasionCommand) (PledgeResult, error) {
	stored, found, err := uc.Persistence.FindOccasionByID(ctx, cmd.OccasionID)
	if err != nil {
		return PledgeResult{}, err
	}
	if !found {
		return PledgeResult{Reason: ReasonNotFound}, nil
	}

	decision := domain.RecordPledge(stored.Value, cmd.PledgeID, cmd.Principal.ContributorID, cmd.Amount)
	if !decision.Ok {
		return decision, nil
	}

	outcome, err := uc.Persistence.SaveWithOutbox(ctx, decision.Occasion, decision.Events, stored.Version)
	if err != nil {
		return PledgeResult{}, err
	}
	if outcome == Conflict {
		return PledgeResult{Reason: ReasonConcurrentChange}, nil
	}
	return decision, nil
}

// HandlePledgeRecorded records a PledgeRecorded event into the projection.
// The outbox worker retries delivery, so this must stay safe even if the
// same event arrives twice — that guarantee lives in the PledgeProjection
// implementation, not here.
func HandlePledgeRecorded(ctx context.Context, projection PledgeProjection, event domain.PledgeRecorded) error {
	return projection.RecordFrom(ctx, event)
}
```

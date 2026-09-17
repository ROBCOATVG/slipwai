```go
package ddd

import "context"

type PledgeOutcome int

const (
	PledgeRecorded PledgeOutcome = iota
	PledgeRejected
	PledgeNotFound
	PledgeConflict
)

type PledgeResult struct {
	Outcome  PledgeOutcome
	Occasion Occasion
	Events   []PledgeRecordedEvent
	Reason   string
}

type OccasionRepository interface {
	FindByID(ctx context.Context, id OccasionID) (StoredOccasion, bool, error)
	SaveWithOutbox(ctx context.Context, occasion Occasion, events []PledgeRecordedEvent, expectedVersion int) (SaveOutcome, error)
}

type ContributorRepository interface {
	ApplyPledgeOnce(ctx context.Context, pledgeID PledgeID, contributorID ContributorID, amount Money) error
}

// HandlePledge is one transaction: it saves one aggregate and its outbox
// event together.
func HandlePledge(ctx context.Context, occasions OccasionRepository, dto PledgeDTO) (PledgeResult, error) {
	stored, found, err := occasions.FindByID(ctx, dto.OccasionID)
	if err != nil {
		return PledgeResult{}, err
	}
	if !found {
		return PledgeResult{Outcome: PledgeNotFound}, nil
	}

	result := RecordPledge(stored.Value, dto)
	if result.Outcome != PledgeRecorded {
		return result, nil
	}

	saved, err := occasions.SaveWithOutbox(ctx, result.Occasion, result.Events, stored.Version)
	if err != nil {
		return PledgeResult{}, err
	}
	if saved == SaveConflict {
		return PledgeResult{Outcome: PledgeConflict}, nil
	}

	return result, nil
}

// HandlePledgeRecorded is a separate, idempotent handler that converges the
// other aggregate.
func HandlePledgeRecorded(ctx context.Context, contributors ContributorRepository, event PledgeRecordedEvent) error {
	return contributors.ApplyPledgeOnce(ctx, event.PledgeID, event.ContributorID, event.Amount)
}
```

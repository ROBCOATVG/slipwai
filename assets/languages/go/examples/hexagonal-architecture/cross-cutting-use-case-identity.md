```go
package application

import "context"

// PledgingToOccasions is the application/use case: it receives identity and
// coordinates domain behaviour. Application code doesn't check JWT tokens or
// session cookies — it authorizes an already-authenticated, provider-free
// principal and invokes domain rules.
type PledgingToOccasions struct {
	Persistence PledgePersistence
}

func (uc PledgingToOccasions) PledgeToOccasion(ctx context.Context, cmd PledgeToOccasionCommand) (PledgeResult, error) {
	stored, found, err := uc.Persistence.FindOccasionByID(ctx, cmd.OccasionID)
	if err != nil {
		return PledgeResult{}, err
	}
	if !found {
		return PledgeResult{Reason: ReasonNotFound}, nil
	}
	// ... delegate to the domain function and save the outcome
	return PledgeResult{}, nil
}
```

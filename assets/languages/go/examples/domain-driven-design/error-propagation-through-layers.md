```go
package ddd

import (
	"context"
	"net/http"
)

type PledgeDecisionOutcome int

const (
	PledgeAccepted PledgeDecisionOutcome = iota
	PledgeRejected
)

// PledgeDecision is the domain result: it carries the business reason.
type PledgeDecision struct {
	Outcome  PledgeDecisionOutcome
	Occasion Occasion
	Events   []PledgeRecorded
	Reason   string
}

// PledgeContribution is the domain function.
func PledgeContribution(occasion Occasion, eligibility Eligibility, pledge NewPledge) PledgeDecision {
	if occasion.IsFundingClosed {
		return PledgeDecision{Outcome: PledgeRejected, Reason: "funding-closed"}
	}
	// ...
	return PledgeDecision{Outcome: PledgeAccepted, Occasion: occasion}
}

type PledgeResultKind int

const (
	PledgeResultDecision PledgeResultKind = iota
	PledgeResultNotFound
	PledgeResultConcurrentChange
)

type PledgeResult struct {
	Kind     PledgeResultKind
	Decision PledgeDecision
}

// HandlePledge is the use-case function: it propagates the domain result
// and adds the application-level not-found/concurrent-change outcomes while
// orchestrating persistence.
func HandlePledge(ctx context.Context, repos Repos, dto PledgeDTO) (PledgeResult, error) {
	stored, found, err := repos.Occasion.FindByID(ctx, dto.OccasionID)
	if err != nil {
		return PledgeResult{}, err
	}
	eligibility, elFound, err := repos.Eligibility.FindFor(ctx, dto.ContributorID)
	if err != nil {
		return PledgeResult{}, err
	}
	if !found || !elFound {
		return PledgeResult{Kind: PledgeResultNotFound}, nil
	}

	decision := PledgeContribution(stored.Value, eligibility, NewPledge{ID: dto.PledgeID, Amount: dto.Amount})
	if decision.Outcome == PledgeAccepted {
		saved, err := repos.Occasion.SaveWithOutbox(ctx, decision.Occasion, decision.Events, stored.Version)
		if err != nil {
			return PledgeResult{}, err
		}
		if saved == SaveConflict {
			return PledgeResult{Kind: PledgeResultConcurrentChange}, nil
		}
	}
	return PledgeResult{Kind: PledgeResultDecision, Decision: decision}, nil
}

// ToHTTPStatus is the delivery-layer translator: it maps the result to an
// HTTP-style status code.
func ToHTTPStatus(result PledgeResult) int {
	switch result.Kind {
	case PledgeResultNotFound:
		return http.StatusNotFound
	case PledgeResultConcurrentChange:
		return http.StatusConflict
	case PledgeResultDecision:
		if result.Decision.Outcome == PledgeAccepted {
			return http.StatusOK
		}
		return http.StatusUnprocessableEntity
	default:
		return http.StatusInternalServerError
	}
}
```

```go
package ddd

import "errors"

// NewMoney raises for an invariant violation — this would be a bug, not a
// business outcome.
func NewMoney(minorUnits int, currency string) (Money, error) {
	if minorUnits < 0 {
		return Money{}, errors.New("money cannot be negative")
	}
	return Money{MinorUnits: minorUnits, Currency: currency}, nil
}

type PledgeDecisionOutcome int

const (
	PledgeAccepted PledgeDecisionOutcome = iota
	PledgeRejected
)

type PledgeDecision struct {
	Outcome  PledgeDecisionOutcome
	Occasion Occasion
	Reason   string
}

// PledgeContribution returns a result type — an expected business outcome,
// not a bug.
func PledgeContribution(occasion Occasion, eligibility Eligibility, pledge NewPledge) PledgeDecision {
	if !eligibility.MayPledge {
		return PledgeDecision{Outcome: PledgeRejected, Reason: "contributor-ineligible"}
	}
	// ...
	return PledgeDecision{Outcome: PledgeAccepted, Occasion: occasion}
}
```

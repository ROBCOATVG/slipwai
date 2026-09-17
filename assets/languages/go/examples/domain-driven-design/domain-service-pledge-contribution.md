```go
package ddd

import "fmt"

type Currency string

type Money struct {
	MinorUnits int64
	Currency   Currency
}

func NewMoney(minorUnits int64, currency Currency) (Money, error) {
	if minorUnits < 0 {
		return Money{}, fmt.Errorf("money cannot be negative")
	}
	return Money{MinorUnits: minorUnits, Currency: currency}, nil
}

const maxSafeInteger = 1<<53 - 1

type OccasionID string
type PledgeID string
type ContributorID string

type Occasion struct {
	ID              OccasionID
	Budget          Money
	TotalPledged    Money
	IsFundingClosed bool
}

type ContributorEligibility struct {
	ContributorID ContributorID
	MayPledge     bool
}

type Pledge struct {
	ID     PledgeID
	Amount Money
}

type PledgeRecorded struct {
	ID            PledgeID
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

// PledgeRejectionReason enumerates the domain-level reasons a pledge can
// be refused.
type PledgeRejectionReason string

const (
	ReasonContributorIneligible PledgeRejectionReason = "contributor-ineligible"
	ReasonNonPositiveAmount     PledgeRejectionReason = "non-positive-amount"
	ReasonCurrencyMismatch      PledgeRejectionReason = "currency-mismatch"
	ReasonExceedsBudget         PledgeRejectionReason = "exceeds-budget"
	ReasonFundingClosed         PledgeRejectionReason = "funding-closed"
)

// PledgeDecision is the outcome of attempting to pledge a contribution.
// Go has no sum types, so Success discriminates which fields are
// meaningful: on success, Occasion and Events; on failure, Reason.
type PledgeDecision struct {
	Success  bool
	Occasion Occasion
	Events   []PledgeRecorded
	Reason   PledgeRejectionReason
}

func accepted(occasion Occasion, events []PledgeRecorded) PledgeDecision {
	return PledgeDecision{Success: true, Occasion: occasion, Events: events}
}

func rejected(reason PledgeRejectionReason) PledgeDecision {
	return PledgeDecision{Success: false, Reason: reason}
}

// AddContributionWrong is WRONG -- cramming an external eligibility policy
// into one entity. An entity method has no access to eligibility, so it
// can never make this decision correctly; it exists here only to be
// contrasted with PledgeContribution below.
func AddContributionWrong(occasion Occasion, pledge Pledge) Occasion {
	panic("an entity method has no access to eligibility")
}

// PledgeContribution is CORRECT: a pure domain service that consumes a
// read-only policy fact (eligibility) supplied by the caller, rather than
// trying to know it itself.
func PledgeContribution(occasion Occasion, eligibility ContributorEligibility, pledge Pledge) PledgeDecision {
	if !eligibility.MayPledge {
		return rejected(ReasonContributorIneligible)
	}
	if occasion.IsFundingClosed {
		return rejected(ReasonFundingClosed)
	}
	if pledge.Amount.Currency != occasion.TotalPledged.Currency ||
		occasion.TotalPledged.Currency != occasion.Budget.Currency {
		return rejected(ReasonCurrencyMismatch)
	}

	values := []int64{occasion.TotalPledged.MinorUnits, occasion.Budget.MinorUnits, pledge.Amount.MinorUnits}
	for _, v := range values {
		if v > maxSafeInteger || v < -maxSafeInteger {
			panic("invalid money invariant")
		}
	}

	if pledge.Amount.MinorUnits <= 0 {
		return rejected(ReasonNonPositiveAmount)
	}
	if occasion.TotalPledged.MinorUnits > occasion.Budget.MinorUnits {
		panic("invalid occasion funding invariant")
	}
	if pledge.Amount.MinorUnits > occasion.Budget.MinorUnits-occasion.TotalPledged.MinorUnits {
		return rejected(ReasonExceedsBudget)
	}

	totalPledged := occasion.TotalPledged.MinorUnits + pledge.Amount.MinorUnits
	if totalPledged > maxSafeInteger {
		panic("money addition overflowed")
	}

	newTotal, err := NewMoney(totalPledged, pledge.Amount.Currency)
	if err != nil {
		panic(fmt.Sprintf("invalid money invariant: %v", err))
	}
	updated := occasion
	updated.TotalPledged = newTotal

	return accepted(updated, []PledgeRecorded{{
		ID:            pledge.ID,
		OccasionID:    occasion.ID,
		ContributorID: eligibility.ContributorID,
		Amount:        pledge.Amount,
	}})
}
```

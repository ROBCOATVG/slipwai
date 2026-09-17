```go
package pledging

const maxSafeInteger = 1<<53 - 1

type Money struct {
	MinorUnits int64
	Currency   string
}

func NewMoney(minorUnits int64, currency string) Money {
	return Money{MinorUnits: minorUnits, Currency: currency}
}

type OccasionID string

type Occasion struct {
	ID              OccasionID
	IsFundingClosed bool
	TotalPledged    Money
	Budget          Money
}

type ContributorEligibility struct {
	MayPledge bool
}

type Pledge struct {
	Amount Money
}

// PledgeDecision is the outcome of attempting a pledge — no events, just an
// explicit accept/reject plus, on acceptance, the updated Occasion.
type PledgeDecision struct {
	Accepted bool
	Occasion Occasion
	Reason   string
}

// PledgeContribution returns its result directly — simpler than the Decider
// pattern for domains that don't need cross-aggregate coordination.
func PledgeContribution(occasion Occasion, eligibility ContributorEligibility, pledge Pledge) PledgeDecision {
	if !eligibility.MayPledge {
		return PledgeDecision{Reason: "contributor-ineligible"}
	}
	if occasion.IsFundingClosed {
		return PledgeDecision{Reason: "funding-closed"}
	}
	if pledge.Amount.Currency != occasion.TotalPledged.Currency ||
		occasion.TotalPledged.Currency != occasion.Budget.Currency {
		return PledgeDecision{Reason: "currency-mismatch"}
	}

	for _, v := range []int64{occasion.TotalPledged.MinorUnits, occasion.Budget.MinorUnits, pledge.Amount.MinorUnits} {
		if abs64(v) > maxSafeInteger {
			panic("invalid Money invariant")
		}
	}
	if pledge.Amount.MinorUnits <= 0 {
		return PledgeDecision{Reason: "non-positive-amount"}
	}
	if occasion.TotalPledged.MinorUnits > occasion.Budget.MinorUnits {
		panic("invalid Occasion funding invariant")
	}
	if pledge.Amount.MinorUnits > occasion.Budget.MinorUnits-occasion.TotalPledged.MinorUnits {
		return PledgeDecision{Reason: "exceeds-budget"}
	}

	totalPledged := occasion.TotalPledged.MinorUnits + pledge.Amount.MinorUnits
	if abs64(totalPledged) > maxSafeInteger {
		panic("money addition overflowed")
	}

	newOccasion := occasion
	newOccasion.TotalPledged = NewMoney(totalPledged, pledge.Amount.Currency)
	return PledgeDecision{Accepted: true, Occasion: newOccasion}
}

func abs64(v int64) int64 {
	if v < 0 {
		return -v
	}
	return v
}
```

```go
package pledging

import "testing"

type OccasionID string
type PledgeID string
type ContributorID string

type Money struct {
	MinorUnits int64
	Currency   string
}

func NewMoney(minorUnits int64, currency string) Money {
	return Money{MinorUnits: minorUnits, Currency: currency}
}

type Occasion struct {
	ID              OccasionID
	IsFundingClosed bool
	TotalPledged    Money
	Budget          Money
}

type ContributorEligibility struct {
	ContributorID ContributorID
	MayPledge     bool
}

type PledgeDecision struct {
	Accepted bool
	Occasion Occasion
	Reason   string
}

type Pledge struct {
	ID     PledgeID
	Amount Money
}

func PledgeContribution(occasion Occasion, eligibility ContributorEligibility, pledge Pledge) PledgeDecision {
	if !eligibility.MayPledge {
		return PledgeDecision{Reason: "contributor-ineligible"}
	}
	if occasion.IsFundingClosed {
		return PledgeDecision{Reason: "funding-closed"}
	}
	if pledge.Amount.MinorUnits > occasion.Budget.MinorUnits-occasion.TotalPledged.MinorUnits {
		return PledgeDecision{Reason: "exceeds-budget"}
	}
	newOccasion := occasion
	newOccasion.TotalPledged = NewMoney(occasion.TotalPledged.MinorUnits+pledge.Amount.MinorUnits, pledge.Amount.Currency)
	return PledgeDecision{Accepted: true, Occasion: newOccasion}
}

func testOccasion() Occasion {
	return Occasion{
		ID:              OccasionID("occasion-1"),
		IsFundingClosed: false,
		TotalPledged:    NewMoney(0, "GBP"),
		Budget:          NewMoney(50_000, "GBP"),
	}
}

func testContributorEligibility(mayPledge bool) ContributorEligibility {
	return ContributorEligibility{ContributorID: ContributorID("contributor-1"), MayPledge: mayPledge}
}

func TestPledgeContribution_RejectsIneligibleContributor(t *testing.T) {
	occasion := testOccasion()
	eligibility := testContributorEligibility(false)

	decision := PledgeContribution(occasion, eligibility, Pledge{
		ID:     PledgeID("pledge-1"),
		Amount: NewMoney(5_000, "GBP"),
	})

	if decision.Accepted {
		t.Fatalf("expected pledge to be rejected, got accepted decision: %+v", decision)
	}
	if decision.Reason != "contributor-ineligible" {
		t.Errorf("reason = %q, want %q", decision.Reason, "contributor-ineligible")
	}
}
```

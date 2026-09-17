```go
package pledging

const maxSafeInteger = 1<<53 - 1

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

type PledgeRecorded struct {
	ID            PledgeID
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

// PledgeDecision is the outcome of attempting a pledge: either it was
// accepted (carrying the updated Occasion and events to publish) or
// rejected (carrying a specific, named reason).
type PledgeDecision struct {
	Accepted bool
	Occasion Occasion
	Events   []PledgeRecorded
	Reason   string
}

type Pledge struct {
	ID     PledgeID
	Amount Money
}

// PledgeContribution is the DOMAIN SERVICE — it contains business logic and
// operates only on domain types. Colocate it with the domain concepts it
// serves under the chosen physical structure.
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

	return PledgeDecision{
		Accepted: true,
		Occasion: newOccasion,
		Events: []PledgeRecorded{{
			ID:            pledge.ID,
			OccasionID:    occasion.ID,
			ContributorID: eligibility.ContributorID,
			Amount:        pledge.Amount,
		}},
	}
}

func abs64(v int64) int64 {
	if v < 0 {
		return -v
	}
	return v
}

type StoredOccasion struct {
	Value   Occasion
	Version int
}

// PledgePersistence is the application-owned persistence port.
type PledgePersistence interface {
	FindOccasionByID(occasionID OccasionID) (StoredOccasion, bool, error)
	SaveWithOutbox(occasion Occasion, events []PledgeRecorded, expectedVersion int) (string, error) // "saved" | "conflict"
}

// ContributorEligibilityGateway is the application-owned collaborator for
// checking contributor eligibility, typically served by another bounded context.
type ContributorEligibilityGateway interface {
	FindFor(contributorID ContributorID) (ContributorEligibility, bool, error)
}

type PledgeDto struct {
	PledgeID      PledgeID
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

// HandlePledge is the USE CASE — application orchestration only, no business
// rules. Place it as application policy; never assume it belongs in a
// domain package.
func HandlePledge(persistence PledgePersistence, eligibilityGateway ContributorEligibilityGateway, dto PledgeDto) (PledgeDecision, error) {
	stored, found, err := persistence.FindOccasionByID(dto.OccasionID)
	if err != nil {
		return PledgeDecision{}, err
	}
	eligibility, eligibilityFound, err := eligibilityGateway.FindFor(dto.ContributorID)
	if err != nil {
		return PledgeDecision{}, err
	}
	if !found || !eligibilityFound {
		return PledgeDecision{Reason: "not-found"}, nil
	}

	result := PledgeContribution(stored.Value, eligibility, Pledge{ID: dto.PledgeID, Amount: dto.Amount})
	if result.Accepted {
		saved, err := persistence.SaveWithOutbox(result.Occasion, result.Events, stored.Version)
		if err != nil {
			return PledgeDecision{}, err
		}
		if saved == "conflict" {
			return PledgeDecision{Reason: "concurrent-change"}, nil
		}
	}
	return result, nil
}
```

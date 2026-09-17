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

type PledgeRecorded struct {
	ID            PledgeID
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

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

type StoredOccasion struct {
	Value   Occasion
	Version int
}

type PledgePersistence interface {
	FindOccasionByID(occasionID OccasionID) (StoredOccasion, bool, error)
	SaveWithOutbox(occasion Occasion, events []PledgeRecorded, expectedVersion int) (string, error)
}

type ContributorEligibilityGateway interface {
	FindFor(contributorID ContributorID) (ContributorEligibility, bool, error)
}

type PledgeDto struct {
	PledgeID      PledgeID
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

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

// --- in-memory fakes for the use-case test ---

type fakePledgePersistence struct {
	occasions     map[OccasionID]Occasion
	SavedEntities []Occasion
	OutboxEvents  []PledgeRecorded
}

func newFakePledgePersistence(occasions []Occasion) *fakePledgePersistence {
	byID := make(map[OccasionID]Occasion, len(occasions))
	for _, occasion := range occasions {
		byID[occasion.ID] = occasion
	}
	return &fakePledgePersistence{occasions: byID}
}

func (f *fakePledgePersistence) FindOccasionByID(id OccasionID) (StoredOccasion, bool, error) {
	occasion, ok := f.occasions[id]
	if !ok {
		return StoredOccasion{}, false, nil
	}
	return StoredOccasion{Value: occasion, Version: 1}, true, nil
}

func (f *fakePledgePersistence) SaveWithOutbox(occasion Occasion, events []PledgeRecorded, expectedVersion int) (string, error) {
	f.occasions[occasion.ID] = occasion
	f.SavedEntities = append(f.SavedEntities, occasion)
	f.OutboxEvents = append(f.OutboxEvents, events...)
	return "saved", nil
}

type fakeContributorEligibilityGateway struct {
	entries map[ContributorID]ContributorEligibility
}

func newFakeContributorEligibilityGateway(entries []ContributorEligibility) *fakeContributorEligibilityGateway {
	byID := make(map[ContributorID]ContributorEligibility, len(entries))
	for _, entry := range entries {
		byID[entry.ContributorID] = entry
	}
	return &fakeContributorEligibilityGateway{entries: byID}
}

func (f *fakeContributorEligibilityGateway) FindFor(contributorID ContributorID) (ContributorEligibility, bool, error) {
	entry, ok := f.entries[contributorID]
	return entry, ok, nil
}

func TestHandlePledge_RejectsIneligibleContributor(t *testing.T) {
	testOccasion := Occasion{
		ID:              OccasionID("occasion-1"),
		IsFundingClosed: false,
		TotalPledged:    NewMoney(0, "GBP"),
		Budget:          NewMoney(50_000, "GBP"),
	}
	testContributor := ContributorID("contributor-1")

	persistence := newFakePledgePersistence([]Occasion{testOccasion})
	eligibilityGateway := newFakeContributorEligibilityGateway([]ContributorEligibility{
		{ContributorID: testContributor, MayPledge: false},
	})

	result, err := HandlePledge(persistence, eligibilityGateway, PledgeDto{
		PledgeID:      PledgeID("pledge-1"),
		OccasionID:    testOccasion.ID,
		ContributorID: testContributor,
		Amount:        NewMoney(5_000, "GBP"),
	})
	if err != nil {
		t.Fatalf("HandlePledge returned unexpected error: %v", err)
	}

	if result.Accepted {
		t.Fatalf("expected pledge to be rejected, got: %+v", result)
	}
	if result.Reason != "contributor-ineligible" {
		t.Errorf("reason = %q, want %q", result.Reason, "contributor-ineligible")
	}
	if len(persistence.SavedEntities) != 0 {
		t.Errorf("expected no saved entities, got %d", len(persistence.SavedEntities))
	}
	if len(persistence.OutboxEvents) != 0 {
		t.Errorf("expected no outbox events, got %d", len(persistence.OutboxEvents))
	}
}
```

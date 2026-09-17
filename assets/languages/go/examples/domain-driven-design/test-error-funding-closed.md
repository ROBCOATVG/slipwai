```go
package ddd_test

import (
	"context"
	"testing"
)

func TestHandlePledge(t *testing.T) {
	tests := []struct {
		name          string
		fundingClosed bool
		wantOutcome   PledgeDecisionOutcome
		wantReason    string
	}{
		{
			name:          "rejects pledge when funding is closed",
			fundingClosed: true,
			wantOutcome:   PledgeRejected,
			wantReason:    "funding-closed",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			closedOccasion := getTestOccasion(withFundingClosed(tt.fundingClosed))
			occasionRepo := newFakeOccasionRepository(closedOccasion)
			contributorRepo := newFakeContributorRepository(testContributor)

			result, err := HandlePledge(context.Background(), Repos{
				Occasion:    occasionRepo,
				Contributor: contributorRepo,
			}, PledgeDTO{
				OccasionID:    closedOccasion.ID,
				ContributorID: testContributor.ID,
				Amount:        Money{MinorUnits: 2_500, Currency: "GBP"},
			})

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if result.Decision.Outcome != tt.wantOutcome {
				t.Errorf("outcome = %v, want %v", result.Decision.Outcome, tt.wantOutcome)
			}
			if result.Decision.Reason != tt.wantReason {
				t.Errorf("reason = %q, want %q", result.Decision.Reason, tt.wantReason)
			}
			if len(occasionRepo.SavedEntities) != 0 {
				t.Errorf("saved entities = %d, want 0 (nothing should be saved when funding is closed)", len(occasionRepo.SavedEntities))
			}
		})
	}
}
```

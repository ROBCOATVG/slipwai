```go
// gifting/hexagon/application/pledge_to_occasion_test.go
package application_test

import (
	"context"
	"testing"

	"gifting/hexagon/application"
	"gifting/hexagon/domain"
	"gifting/testing/fakes"
)

func testOccasion(budgetMinorUnits, totalPledgedMinorUnits int64, isFundingClosed bool) domain.Occasion {
	return domain.Occasion{
		ID:              domain.OccasionID("occasion-1"),
		Name:            "Alex's birthday",
		Budget:          domain.Money{MinorUnits: budgetMinorUnits, Currency: domain.GBP},
		TotalPledged:    domain.Money{MinorUnits: totalPledgedMinorUnits, Currency: domain.GBP},
		IsFundingClosed: isFundingClosed,
	}
}

var testPrincipal = application.AuthenticatedPledger{ContributorID: domain.ContributorID("contributor-1")}

func TestPledgingToOccasions_UpdatesOneAggregateAndRecordsItsOutboxEvent(t *testing.T) {
	occasion := testOccasion(10_000, 0, false)
	persistence := fakes.NewPledgePersistence(occasion)
	pledging := application.PledgingToOccasions{Persistence: persistence}

	result, err := pledging.PledgeToOccasion(context.Background(), application.PledgeToOccasionCommand{
		PledgeID:   domain.PledgeID("pledge-1"),
		OccasionID: occasion.ID,
		Principal:  testPrincipal,
		Amount:     domain.Money{MinorUnits: 2_500, Currency: domain.GBP},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !result.Ok {
		t.Fatalf("expected success, got rejection reason %q", result.Reason)
	}
	want := domain.Money{MinorUnits: 2_500, Currency: domain.GBP}
	if result.Occasion.TotalPledged != want {
		t.Errorf("total pledged = %+v, want %+v", result.Occasion.TotalPledged, want)
	}
	if len(persistence.SavedEntities) != 1 {
		t.Fatalf("len(SavedEntities) = %d, want 1", len(persistence.SavedEntities))
	}
	if len(persistence.OutboxEvents) != 1 || persistence.OutboxEvents[0].Amount != want {
		t.Errorf("outbox events = %+v, want one event of %+v", persistence.OutboxEvents, want)
	}
}

func TestPledgingToOccasions_RejectsAnInvalidPledge(t *testing.T) {
	cases := []struct {
		name         string
		occasion     domain.Occasion
		amount       domain.Money
		wantReason   domain.RejectionReason
	}{
		{
			name:       "exceeds budget",
			occasion:   testOccasion(10_000, 9_000, false),
			amount:     domain.Money{MinorUnits: 2_500, Currency: domain.GBP},
			wantReason: domain.ReasonExceedsBudget,
		},
		{
			name:       "currency mismatch",
			occasion:   testOccasion(10_000, 0, false),
			amount:     domain.Money{MinorUnits: 2_500, Currency: domain.USD},
			wantReason: domain.ReasonCurrencyMismatch,
		},
		{
			name:       "funding closed",
			occasion:   testOccasion(10_000, 0, true),
			amount:     domain.Money{MinorUnits: 2_500, Currency: domain.GBP},
			wantReason: domain.ReasonFundingClosed,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			persistence := fakes.NewPledgePersistence(tc.occasion)
			pledging := application.PledgingToOccasions{Persistence: persistence}

			result, err := pledging.PledgeToOccasion(context.Background(), application.PledgeToOccasionCommand{
				PledgeID:   domain.PledgeID("pledge-1"),
				OccasionID: tc.occasion.ID,
				Principal:  testPrincipal,
				Amount:     tc.amount,
			})
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if result.Ok {
				t.Fatalf("expected rejection %q, got success", tc.wantReason)
			}
			if result.Reason != tc.wantReason {
				t.Errorf("reason = %q, want %q", result.Reason, tc.wantReason)
			}
			if len(persistence.SavedEntities) != 0 || len(persistence.OutboxEvents) != 0 {
				t.Errorf("expected nothing saved on rejection, got %d entities, %d events",
					len(persistence.SavedEntities), len(persistence.OutboxEvents))
			}
		})
	}
}

// Not a table case: this exercises a real race between two goroutines
// sharing one starting version, so it earns its own dedicated test function.
func TestPledgingToOccasions_RejectsOneOfTwoConcurrentWritesFromTheSameVersion(t *testing.T) {
	occasion := testOccasion(10_000, 0, false)
	persistence := fakes.NewPledgePersistence(occasion)
	pledging := application.PledgingToOccasions{Persistence: persistence}

	type outcome struct {
		result application.PledgeResult
		err    error
	}
	results := make(chan outcome, 2)

	go func() {
		result, err := pledging.PledgeToOccasion(context.Background(), application.PledgeToOccasionCommand{
			PledgeID:   domain.PledgeID("pledge-1"),
			OccasionID: occasion.ID,
			Principal:  testPrincipal,
			Amount:     domain.Money{MinorUnits: 2_500, Currency: domain.GBP},
		})
		results <- outcome{result, err}
	}()
	go func() {
		result, err := pledging.PledgeToOccasion(context.Background(), application.PledgeToOccasionCommand{
			PledgeID:   domain.PledgeID("pledge-2"),
			OccasionID: occasion.ID,
			Principal:  testPrincipal,
			Amount:     domain.Money{MinorUnits: 3_000, Currency: domain.GBP},
		})
		results <- outcome{result, err}
	}()

	var successes, failures int
	for i := 0; i < 2; i++ {
		out := <-results
		if out.err != nil {
			t.Fatalf("unexpected error: %v", out.err)
		}
		if out.result.Ok {
			successes++
		} else if out.result.Reason == domain.ReasonConcurrentChange {
			failures++
		} else {
			t.Errorf("unexpected rejection reason: %q", out.result.Reason)
		}
	}

	if successes != 1 || failures != 1 {
		t.Errorf("got %d successes and %d concurrent-change failures, want 1 and 1", successes, failures)
	}
	if len(persistence.SavedEntities) != 1 || len(persistence.OutboxEvents) != 1 {
		t.Errorf("expected exactly one save and one outbox event, got %d and %d",
			len(persistence.SavedEntities), len(persistence.OutboxEvents))
	}
}

func TestHandlePledgeRecorded_HandlesARedeliveredEventOnce(t *testing.T) {
	projection := fakes.NewPledgeProjection()
	event := domain.PledgeRecorded{
		ID:            domain.PledgeID("pledge-1"),
		OccasionID:    domain.OccasionID("occasion-1"),
		ContributorID: domain.ContributorID("contributor-1"),
		Amount:        domain.Money{MinorUnits: 2_500, Currency: domain.GBP},
	}

	if err := application.HandlePledgeRecorded(context.Background(), projection, event); err != nil {
		t.Fatalf("unexpected error on first delivery: %v", err)
	}
	if err := application.HandlePledgeRecorded(context.Background(), projection, event); err != nil {
		t.Fatalf("unexpected error on redelivery: %v", err)
	}

	records := projection.Records()
	if len(records) != 1 || records[0] != event {
		t.Errorf("records = %+v, want exactly one copy of %+v", records, event)
	}
}
```

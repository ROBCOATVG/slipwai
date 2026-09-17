```go
// gifting/hexagon/domain/pledge_test.go
package domain_test

import (
	"testing"

	"gifting/hexagon/domain"
)

func testOccasion(totalPledgedMinorUnits int64) domain.Occasion {
	return domain.Occasion{
		ID:              domain.OccasionID("occasion-1"),
		Name:            "Alex's birthday",
		Budget:          domain.Money{MinorUnits: 10_000, Currency: domain.GBP},
		TotalPledged:    domain.Money{MinorUnits: totalPledgedMinorUnits, Currency: domain.GBP},
		IsFundingClosed: false,
	}
}

// This is a pure function: values in, a decision out. No fakes, no ports —
// a complement to the use-case-level tests for the rules with many edge cases.
func TestRecordPledge_AddsTheExactAmountAndRecordsWhatHappened(t *testing.T) {
	occasion := testOccasion(5_000)

	decision := domain.RecordPledge(
		occasion,
		domain.PledgeID("pledge-1"),
		domain.ContributorID("contributor-1"),
		domain.Money{MinorUnits: 3_000, Currency: domain.GBP},
	)

	if !decision.Ok {
		t.Fatalf("expected pledge to be recorded, got rejection reason %q", decision.Reason)
	}
	want := domain.Money{MinorUnits: 8_000, Currency: domain.GBP}
	if decision.Occasion.TotalPledged != want {
		t.Errorf("total pledged = %+v, want %+v", decision.Occasion.TotalPledged, want)
	}
	if len(decision.Events) != 1 {
		t.Fatalf("len(events) = %d, want 1", len(decision.Events))
	}
	if decision.Events[0].Amount != (domain.Money{MinorUnits: 3_000, Currency: domain.GBP}) {
		t.Errorf("event amount = %+v, want 3000 GBP", decision.Events[0].Amount)
	}
}
```

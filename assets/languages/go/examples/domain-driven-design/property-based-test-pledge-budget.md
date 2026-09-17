```go
// FuzzPledgeNeverExceedsBudget uses Go's native fuzz testing — the closest
// idiomatic stdlib equivalent to a property-based test in this ecosystem.
// `go test -fuzz=FuzzPledgeNeverExceedsBudget` explores the input space
// beyond the two seed corpus entries below.
func FuzzPledgeNeverExceedsBudget(f *testing.F) {
	f.Add(0, 5000)
	f.Add(9000, 500)

	f.Fuzz(func(t *testing.T, alreadyPledged, pledge int) {
		if alreadyPledged < 0 || alreadyPledged > 10_000 || pledge < 1 || pledge > 10_000 {
			t.Skip("outside the domain this property is defined over")
		}

		occasion := newTestOccasion(
			NewMoney(10_000, "GBP"),
			NewMoney(alreadyPledged, "GBP"),
		)
		eligibility := ContributorEligibility{MayPledge: true}

		result := PledgeContribution(occasion, eligibility, PledgeRequest{
			ID:     PledgeID("pledge-1"),
			Amount: NewMoney(pledge, "GBP"),
		})

		if !result.Success {
			return // rejected pledges are always valid
		}
		if result.Occasion.TotalPledged.MinorUnits > result.Occasion.Budget.MinorUnits {
			t.Fatalf("pledge accepted but total %d exceeds budget %d",
				result.Occasion.TotalPledged.MinorUnits, result.Occasion.Budget.MinorUnits)
		}
	})
}
```

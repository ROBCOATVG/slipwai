```go
func TestIsPastEvent(t *testing.T) {
	now := time.Date(2026, 3, 20, 12, 0, 0, 0, time.UTC)

	tests := []struct {
		name      string
		eventDate time.Time
		want      bool
	}{
		{"date before now is past", time.Date(2026, 3, 19, 12, 0, 0, 0, time.UTC), true},
		{"date after now is not past", time.Date(2026, 3, 21, 12, 0, 0, 0, time.UTC), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := IsPastEvent(tt.eventDate, now); got != tt.want {
				t.Errorf("IsPastEvent(%v, %v) = %v, want %v", tt.eventDate, now, got, tt.want)
			}
		})
	}
}

func TestCalculateCommittedTotal_IncludesOnlyNonIdeaItems(t *testing.T) {
	items := []GiftItem{
		newTestItem("committed", 5000),
		newTestItem("idea", 3000),
	}

	got := CalculateCommittedTotal(items)

	if want := 5000; got != want {
		t.Errorf("CalculateCommittedTotal() = %d, want %d", got, want)
	}
}

// newTestItem is a local test-data helper mirroring the sibling GiftItem type.
func newTestItem(status string, pricePence int) GiftItem {
	return GiftItem{Status: status, PricePence: pricePence}
}
```

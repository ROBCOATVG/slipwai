```go
package taxation

import "testing"

// ForCalculatingTaxes is the driving port — exposed by the application,
// called by driving adapters — for calculating tax on an amount.
type ForCalculatingTaxes interface {
	TaxOn(amount Money) Money
}

// TestTaxCalculation_TaxOn is the TDD "fake it" step: NewTaxCalculation
// (defined elsewhere) returns a trivial implementation that answers with a
// hardcoded placeholder tax value.
func TestTaxCalculation_TaxOn(t *testing.T) {
	tests := []struct {
		name     string
		amount   Money
		expected Money
	}{
		{
			name:     "returns the flat placeholder tax",
			amount:   NewMoney(100, "GBP"),
			expected: NewMoney(0, "GBP"),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calculator := NewTaxCalculation()

			if got := calculator.TaxOn(tt.amount); got != tt.expected {
				t.Errorf("TaxOn(%v) = %v, want %v", tt.amount, got, tt.expected)
			}
		})
	}
}
```

```go
// Tests covering validation WITHOUT testing the validator directly.
func TestProcessPayment_Validation(t *testing.T) {
	cases := []struct {
		name        string
		overrides   []func(*Payment)
		wantSuccess bool
	}{
		{
			name:      "rejects negative amounts",
			overrides: []func(*Payment){func(p *Payment) { p.AmountMinorUnits = -100; p.Currency = "GBP" }},
		},
		{
			name:      "rejects amounts over 10000",
			overrides: []func(*Payment){func(p *Payment) { p.AmountMinorUnits = 1_500_000; p.Currency = "GBP" }},
		},
		{
			name:      "rejects invalid CVV",
			overrides: []func(*Payment){func(p *Payment) { p.CVV = "12" }},
		},
		{
			name: "processes valid payments",
			overrides: []func(*Payment){func(p *Payment) {
				p.AmountMinorUnits = 10_000
				p.Currency = "GBP"
				p.CVV = "123"
			}},
			wantSuccess: true,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			payment := newTestPayment(t, tc.overrides...)

			result := ProcessPayment(payment)

			if result.Success != tc.wantSuccess {
				t.Fatalf("Success = %v, want %v (error: %q)", result.Success, tc.wantSuccess, result.Error)
			}
		})
	}
}

// Result: validation branches are exercised through the public behavior.
```

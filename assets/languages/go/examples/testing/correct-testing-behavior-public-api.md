```go
func TestProcessPayment(t *testing.T) {
	cases := []struct {
		name        string
		overrides   []func(*Payment)
		wantSuccess bool
		wantErr     string
	}{
		{
			name:      "rejects negative amounts",
			overrides: []func(*Payment){func(p *Payment) { p.AmountMinorUnits = -100; p.Currency = "GBP" }},
			wantErr:   "amount must be positive",
		},
		{
			name:      "rejects invalid CVV",
			overrides: []func(*Payment){func(p *Payment) { p.CVV = "12" }}, // only 2 digits
			wantErr:   "invalid CVV",
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
				t.Fatalf("Success = %v, want %v", result.Success, tc.wantSuccess)
			}
			if tc.wantErr != "" && !strings.Contains(result.Error, tc.wantErr) {
				t.Fatalf("Error = %q, want to contain %q", result.Error, tc.wantErr)
			}
			if tc.wantSuccess && result.TransactionID == "" {
				t.Fatal("expected a transaction ID")
			}
		})
	}
}
```

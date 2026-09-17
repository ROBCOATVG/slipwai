```go
func TestValidate(t *testing.T) {
	cases := []struct {
		name        string
		overrides   []func(*Payment)
		wantSuccess bool
	}{
		{"rejects negative amounts", []func(*Payment){func(p *Payment) { p.AmountMinorUnits = -100; p.Currency = "GBP" }}, false},
		{"rejects amounts over limit", []func(*Payment){func(p *Payment) { p.AmountMinorUnits = 1_500_000; p.Currency = "GBP" }}, false},
		{"rejects invalid CVV", []func(*Payment){func(p *Payment) { p.CVV = "12" }}, false},
		{"accepts valid payments", nil, true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			payment := newTestPayment(t, tc.overrides...)

			if got := Validate(payment).Success; got != tc.wantSuccess {
				t.Fatalf("Success = %v, want %v", got, tc.wantSuccess)
			}
		})
	}
}
```

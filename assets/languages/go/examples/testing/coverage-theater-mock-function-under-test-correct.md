```go
func TestValidate_RejectsInvalidPayment(t *testing.T) {
	payment := newTestPayment(t, func(p *Payment) { p.AmountMinorUnits = -100; p.Currency = "GBP" })

	result := Validate(payment)

	if result.Success {
		t.Fatal("expected validation failure")
	}
	if !strings.Contains(result.Error, "amount must be positive") {
		t.Fatalf("Error = %q, want to contain %q", result.Error, "amount must be positive")
	}
}
```

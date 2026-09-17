```go
// ❌ Testing HOW (implementation detail)
func TestProcessPayment_CallsValidateAmount(t *testing.T) {
	spy := &validateAmountSpy{}

	processPayment(spy, payment)

	if !spy.called {
		t.Fatal("expected validateAmount to be called") // tests HOW, not WHAT
	}
}

// ❌ Testing unexported behavior directly
func TestValidateCVVFormat(t *testing.T) {
	result := validateCVV("123") // unexported helper, not the public contract

	if !result {
		t.Fatal("expected CVV to be valid")
	}
}

// ❌ Testing internal state
func TestProcessPayment_SetsValidatedFlag(t *testing.T) {
	p := &processor{}

	p.process(payment)

	if !p.isValidated { // internal state
		t.Fatal("expected isValidated to be true")
	}
}
```

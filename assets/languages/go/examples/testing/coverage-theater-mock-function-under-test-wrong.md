```go
func TestValidator_Validate_IsCalled(t *testing.T) {
	spy := &validateSpy{}

	spy.Validate(payment)

	if !spy.called {
		t.Fatal("expected Validate to be called") // meaningless assertion
	}
}
```

```go
func TestValidate_HappyPathOnly(t *testing.T) {
	result := Validate(newTestPayment(t))

	if !result.Success { // only happy path!
		t.Fatalf("expected success, got error: %q", result.Error)
	}
}

// Missing: negative amounts, invalid CVV, missing fields, etc.
```

```go
func TestHandlePayment_ReturnsTransactionID(t *testing.T) {
	payment := newTestPayment(t)

	result := HandlePayment(payment)

	if !result.Success {
		t.Fatalf("expected success, got error: %q", result.Error)
	}
	if result.TransactionID == "" {
		t.Fatal("expected a transaction ID")
	}
}
```

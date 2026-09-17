```go
// Real database — fresh db per test, no shared state
func TestSQLOrderRepository_RoundTripsAnOrderThroughPersistence(t *testing.T) {
	db := newTestDB(t)
	repo := NewSQLOrderRepository(db)
	order := testOrder()

	if err := repo.Save(order); err != nil {
		t.Fatalf("Save returned unexpected error: %v", err)
	}

	got, err := repo.FindByID(order.ID)
	if err != nil {
		t.Fatalf("FindByID returned unexpected error: %v", err)
	}
	if got != order {
		t.Errorf("FindByID = %+v, want %+v", got, order)
	}
}

// Real HTTP via httptest
func TestStripePaymentGateway_ReturnsSuccessOnValidCharge(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"ch_123","status":"succeeded"}`))
	}))
	defer server.Close()

	gateway := NewStripePaymentGateway(server.URL, "sk_test")

	result, err := gateway.Charge(testAmount(), testPaymentInfo())
	if err != nil {
		t.Fatalf("Charge returned unexpected error: %v", err)
	}
	if !result.Success {
		t.Errorf("Success = false, want true")
	}
}
```

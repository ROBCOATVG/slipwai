```go
func TestOrderPlacement_PlaceOrder(t *testing.T) {
	tests := []struct {
		name           string
		alwaysSucceeds bool
		alwaysFails    bool
		wantSuccess    bool
		wantSavedCount int
	}{
		{
			name:           "saves order and charges payment on success",
			alwaysSucceeds: true,
			wantSuccess:    true,
			wantSavedCount: 1,
		},
		{
			name:           "does not save order when payment fails",
			alwaysFails:    true,
			wantSuccess:    false,
			wantSavedCount: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			orderRepo := NewFakeOrderRepository()
			paymentGateway := NewFakePaymentGateway(tt.alwaysSucceeds, tt.alwaysFails)
			orderPlacement := NewOrderPlacement(orderRepo, paymentGateway)

			result, err := orderPlacement.PlaceOrder(testOrder())
			if err != nil {
				t.Fatalf("PlaceOrder returned unexpected error: %v", err)
			}

			if result.Success != tt.wantSuccess {
				t.Errorf("Success = %v, want %v", result.Success, tt.wantSuccess)
			}
			if got := len(orderRepo.SavedEntities); got != tt.wantSavedCount {
				t.Errorf("len(SavedEntities) = %d, want %d", got, tt.wantSavedCount)
			}
		})
	}
}
```

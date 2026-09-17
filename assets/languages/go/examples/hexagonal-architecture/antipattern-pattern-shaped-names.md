```go
// ❌ Names the pattern or type mechanism
type PaymentPort interface {
	Charge(ctx context.Context, amount Money, info PaymentInfo) (ChargeResult, error)
}

type PaymentGatewayImpl struct {
	apiKey string
}

func (g PaymentGatewayImpl) Charge(ctx context.Context, amount Money, info PaymentInfo) (ChargeResult, error) {
	// ...
	return ChargeResult{}, nil
}

func PlaceOrderUseCase(ctx context.Context, order NewOrder) (OrderResult, error) {
	// ...
	return OrderResult{}, nil
}

// ✅ Names the role and the concrete adapter
type PaymentGateway interface {
	Charge(ctx context.Context, amount Money, info PaymentInfo) (ChargeResult, error)
}

type StripePaymentGateway struct {
	apiKey string
}

func (g StripePaymentGateway) Charge(ctx context.Context, amount Money, info PaymentInfo) (ChargeResult, error) {
	// ...
	return ChargeResult{}, nil
}

func PlaceOrder(ctx context.Context, order NewOrder) (OrderResult, error) {
	// ...
	return OrderResult{}, nil
}
```

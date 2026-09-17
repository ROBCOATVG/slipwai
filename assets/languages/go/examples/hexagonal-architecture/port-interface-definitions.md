```go
package hexagon

import "context"

// ForPlacingOrders is the driving port — exposed by the application, called
// by driving adapters.
type ForPlacingOrders interface {
	PlaceOrder(ctx context.Context, cmd PlaceOrderCommand) (PlaceOrderResult, error)
}

// UserRepository is a driven port — application-owned because the use case
// consumes it.
type UserRepository interface {
	FindByID(ctx context.Context, id UserID) (User, bool, error)
	Save(ctx context.Context, user User) error
}

type PaymentFailure string

// PreparePaymentOutcome distinguishes the two expected results of preparing
// a payment. It is a business outcome, not an error — an unexpected gateway
// failure is still returned as an error alongside it.
type PreparePaymentOutcome int

const (
	PaymentPrepared PreparePaymentOutcome = iota
	PaymentPrepareFailed
)

type PreparePaymentResult struct {
	Outcome   PreparePaymentOutcome
	PaymentID PaymentID
	Reason    PaymentFailure
}

type PaymentOutcomeKind int

const (
	PaymentPaid PaymentOutcomeKind = iota
	PaymentDeclined
	PaymentPending
)

type PaymentOutcome struct {
	Kind     PaymentOutcomeKind
	ChargeID ChargeID
	Reason   PaymentFailure
}

// PaymentGateway is a driven port — application-owned because the use case
// consumes it. It models a two-phase prepare/complete payment conversation.
type PaymentGateway interface {
	PreparePayment(ctx context.Context, amount Money, reference OrderID, idempotencyKey OrderID) (PreparePaymentResult, error)
	CompletePayment(ctx context.Context, paymentID PaymentID, paymentInfo PaymentInfo) (PaymentOutcome, error)
}

// OrderEventPublisher is a driven port for event publishing (outbound to
// message brokers).
type OrderEventPublisher interface {
	Publish(ctx context.Context, event OrderEvent) error
}
```

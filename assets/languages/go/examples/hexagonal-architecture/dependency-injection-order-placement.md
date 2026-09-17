```go
package placement

import (
	"context"
	"os"
)

// WRONG — constructs its own dependencies inline (untestable, tightly coupled)
func createOrderWrong(ctx context.Context, order NewOrder) error {
	repo := NewPostgresOrderRepository(mustOpenDB())     // hardcoded
	gateway := NewStripeGateway(os.Getenv("STRIPE_KEY")) // hardcoded
	_, err := repo.FindOrCreatePending(ctx, order)
	_ = gateway
	return err
}

// RIGHT — dependencies injected as constructor parameters

type RecordOutcome int

const (
	Recorded RecordOutcome = iota
	Conflict
)

type RecordPaymentResult struct {
	Outcome RecordOutcome
	Order   Order
}

type RecordChargeResult struct {
	Outcome RecordOutcome
	Order   Order
}

type OrderRepository interface {
	FindByID(ctx context.Context, orderID string) (Order, bool, error)
	FindOrCreatePending(ctx context.Context, order NewOrder) (Order, error)
	RecordPayment(ctx context.Context, orderID, paymentID string, expectedVersion int) (RecordPaymentResult, error)
	RecordCharge(ctx context.Context, orderID, chargeID string, expectedVersion int) (RecordChargeResult, error)
}

// OrderResult reports the business outcome of placing an order. Reason is
// set only when Placed is false; it is never used for infrastructure
// failures, which are reported as an error instead.
type OrderResult struct {
	Placed bool
	Order  Order
	Reason string
}

// ForPlacingOrders is the driving port implemented by OrderPlacement below.
type ForPlacingOrders interface {
	PlaceOrder(ctx context.Context, order NewOrder) (OrderResult, error)
}

// OrderPlacement is the use case. Its dependencies arrive as constructor
// parameters — never constructed inside a method.
type OrderPlacement struct {
	repo    OrderRepository
	gateway PaymentGateway
}

func NewOrderPlacement(repo OrderRepository, gateway PaymentGateway) *OrderPlacement {
	return &OrderPlacement{repo: repo, gateway: gateway}
}

func (p *OrderPlacement) PlaceOrder(ctx context.Context, order NewOrder) (OrderResult, error) {
	payable, err := p.repo.FindOrCreatePending(ctx, order)
	if err != nil {
		return OrderResult{}, err
	}
	if payable.Status == "paid" {
		return OrderResult{Placed: true, Order: payable}, nil
	}

	if payable.PaymentID == "" {
		prepared, err := p.gateway.PreparePayment(ctx, payable.Total, payable.ID, payable.ID)
		if err != nil {
			return OrderResult{}, err
		}
		if prepared.Outcome == PaymentPrepareFailed {
			return OrderResult{Reason: string(prepared.Reason)}, nil
		}

		recorded, err := p.repo.RecordPayment(ctx, payable.ID, prepared.PaymentID, payable.Version)
		if err != nil {
			return OrderResult{}, err
		}
		if recorded.Outcome == Recorded {
			payable = recorded.Order
		} else {
			current, found, err := p.repo.FindByID(ctx, payable.ID)
			if err != nil {
				return OrderResult{}, err
			}
			if found && current.Status == "paid" {
				return OrderResult{Placed: true, Order: current}, nil
			}
			if !found || current.Status != "pending" || current.PaymentID == "" {
				return OrderResult{Reason: "concurrent-change"}, nil
			}
			payable = current
		}
	}

	if payable.PaymentID == "" {
		return OrderResult{Reason: "concurrent-change"}, nil
	}

	payment, err := p.gateway.CompletePayment(ctx, payable.PaymentID, payable.Payment)
	if err != nil {
		return OrderResult{}, err
	}
	if payment.Kind == PaymentPending {
		return OrderResult{Reason: "payment-pending"}, nil
	}
	if payment.Kind == PaymentDeclined {
		return OrderResult{Reason: string(payment.Reason)}, nil
	}

	recorded, err := p.repo.RecordCharge(ctx, payable.ID, payment.ChargeID, payable.Version)
	if err != nil {
		return OrderResult{}, err
	}
	if recorded.Outcome == Recorded {
		return OrderResult{Placed: true, Order: recorded.Order}, nil
	}

	current, found, err := p.repo.FindByID(ctx, payable.ID)
	if err != nil {
		return OrderResult{}, err
	}
	if found && current.Status == "paid" && current.ChargeID == payment.ChargeID {
		return OrderResult{Placed: true, Order: current}, nil
	}
	return OrderResult{Reason: "concurrent-change"}, nil
}
```

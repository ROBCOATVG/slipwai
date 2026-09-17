```go
package payments

import (
	"fmt"
	"strings"
)

// ChargeID is our domain's identity for a completed charge.
type ChargeID string

func NewChargeID(raw string) (ChargeID, error) {
	if raw == "" {
		return "", fmt.Errorf("charge id must not be empty")
	}
	return ChargeID(raw), nil
}

// Money is an amount expressed in integer minor units — never floating point.
type Money struct {
	MinorUnits int64
	Currency   string
}

func NewMoney(minorUnits int64, currency string) Money {
	return Money{MinorUnits: minorUnits, Currency: currency}
}

// StripeCharge is the external system's model, exactly as Stripe returns it.
type StripeCharge struct {
	ID       string
	Amount   int64  // integer minor units, per Stripe's contract
	Currency string // lowercase ISO code
	Status   string
}

// PaymentResult is our domain's outcome, decoupled from Stripe's vocabulary.
type PaymentResult struct {
	Success  bool
	ChargeID ChargeID
	Amount   Money
	Reason   string
}

// ToPaymentResult is the Anti-Corruption Layer: it translates Stripe's model
// into our domain's model at the boundary, so no Stripe vocabulary leaks in.
func ToPaymentResult(charge StripeCharge) (PaymentResult, error) {
	if charge.Status == "succeeded" {
		chargeID, err := NewChargeID(charge.ID)
		if err != nil {
			return PaymentResult{}, fmt.Errorf("translating stripe charge: %w", err)
		}
		return PaymentResult{
			Success:  true,
			ChargeID: chargeID,
			Amount:   NewMoney(charge.Amount, strings.ToUpper(charge.Currency)),
		}, nil
	}
	return PaymentResult{
		Success: false,
		Reason:  fmt.Sprintf("payment failed: %s", charge.Status),
	}, nil
}
```

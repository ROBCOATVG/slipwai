```go
package ddd

type OrderRejectionReason string

const (
	EmptyCart          OrderRejectionReason = "empty-cart"
	ItemOutOfStock     OrderRejectionReason = "item-out-of-stock"
	PaymentDeclined    OrderRejectionReason = "payment-declined"
	AddressInvalid     OrderRejectionReason = "address-invalid"
	DailyLimitExceeded OrderRejectionReason = "daily-limit-exceeded"
)

type CreateOrderOutcome int

const (
	OrderCreated CreateOrderOutcome = iota
	OrderRejected
)

// CreateOrderResult models every possible failure as one closed set of
// specific reasons, not a generic error class.
type CreateOrderResult struct {
	Outcome CreateOrderOutcome
	Order   Order
	Reason  OrderRejectionReason
}
```

```go
package ddd

import (
	"fmt"
	"time"
)

type OrderStatus string

const (
	OrderStatusDraft   OrderStatus = "draft"
	OrderStatusPlaced  OrderStatus = "placed"
	OrderStatusShipped OrderStatus = "shipped"
)

type OrderItem struct {
	SKU      string
	Quantity int
}

// Order models the lifecycle as one struct with a Status discriminant --
// Go has no sum types. Fields only valid for later states (PlacedAt,
// ShippedAt, TrackingNumber) stay zero-valued until the order reaches
// that state.
type Order struct {
	Status         OrderStatus
	Items          []OrderItem
	PlacedAt       time.Time
	ShippedAt      time.Time
	TrackingNumber string
}

// DescribeOrder exhaustively handles every lifecycle variant. The default
// case panics: reaching it means a variant was added to OrderStatus
// without updating this function -- a genuine programmer error, not a
// business outcome.
func DescribeOrder(order Order) string {
	switch order.Status {
	case OrderStatusDraft:
		return fmt.Sprintf("Draft with %d items", len(order.Items))
	case OrderStatusPlaced:
		return fmt.Sprintf("Placed at %s", order.PlacedAt.Format(time.RFC3339))
	case OrderStatusShipped:
		return fmt.Sprintf("Shipped: %s", order.TrackingNumber)
	default:
		panic(fmt.Sprintf("unhandled order status: %q", order.Status))
	}
}
```

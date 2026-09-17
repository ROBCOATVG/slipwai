```go
package ddd

import "time"

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

// Order models the lifecycle as a single struct with a Status discriminant;
// Go has no sum types, so fields that are only valid for later states
// (PlacedAt, ShippedAt, TrackingNumber) stay zero-valued until the order
// reaches that state. The constructors below keep each state's invariants
// honest -- construct via NewDraftOrder/NewPlacedOrder/NewShippedOrder
// rather than the struct literal directly.
type Order struct {
	Status         OrderStatus
	Items          []OrderItem
	PlacedAt       time.Time
	ShippedAt      time.Time
	TrackingNumber string
}

func NewDraftOrder(items []OrderItem) Order {
	return Order{Status: OrderStatusDraft, Items: items}
}

func NewPlacedOrder(items []OrderItem, placedAt time.Time) Order {
	return Order{Status: OrderStatusPlaced, Items: items, PlacedAt: placedAt}
}

func NewShippedOrder(items []OrderItem, placedAt, shippedAt time.Time, trackingNumber string) Order {
	return Order{
		Status:         OrderStatusShipped,
		Items:          items,
		PlacedAt:       placedAt,
		ShippedAt:      shippedAt,
		TrackingNumber: trackingNumber,
	}
}
```

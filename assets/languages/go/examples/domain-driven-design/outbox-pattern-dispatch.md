```go
package ordering

import "time"

type OrderID string

type OrderItem struct {
	SKU      string
	Quantity int
}

type OrderStatus string

const (
	StatusDraft  OrderStatus = "draft"
	StatusPlaced OrderStatus = "placed"
)

type OrderState struct {
	Status OrderStatus
	Items  []OrderItem
}

type PlaceOrderCommand struct {
	OrderID OrderID
}

type OrderEvent interface{ isOrderEvent() }

type OrderPlaced struct {
	Items    []OrderItem
	PlacedAt time.Time
}

func (OrderPlaced) isOrderEvent() {}

type OrderDecision struct {
	Accepted bool
	Events   []OrderEvent
	Reason   string
}

func Decide(command PlaceOrderCommand, state OrderState, now time.Time) OrderDecision {
	if state.Status != StatusDraft {
		return OrderDecision{Reason: "order-not-draft"}
	}
	return OrderDecision{Accepted: true, Events: []OrderEvent{OrderPlaced{Items: state.Items, PlacedAt: now}}}
}

func Evolve(state OrderState, event OrderEvent) OrderState {
	switch evt := event.(type) {
	case OrderPlaced:
		return OrderState{Status: StatusPlaced, Items: evt.Items}
	default:
		return state
	}
}

type StoredOrder struct {
	State   OrderState
	Version int
}

// PlaceOrderPersistence is the application-owned persistence port — a driven
// port when hexagonal architecture is used. It requires one atomic
// aggregate + outbox operation: a background worker publishes the outbox
// rows later, giving reliable (at-least-once) dispatch.
type PlaceOrderPersistence interface {
	FindOrderByID(orderID OrderID) (StoredOrder, bool, error)
	SaveWithOutbox(state OrderState, events []OrderEvent, expectedVersion int) (string, error) // "saved" | "conflict"
}

type PlaceOrderResult struct {
	Success bool
	Order   OrderState
	Reason  string
}

func HandlePlaceOrder(
	persistence PlaceOrderPersistence,
	command PlaceOrderCommand,
	now time.Time,
) (PlaceOrderResult, error) {
	stored, found, err := persistence.FindOrderByID(command.OrderID)
	if err != nil {
		return PlaceOrderResult{}, err
	}
	if !found {
		return PlaceOrderResult{Reason: "not-found"}, nil
	}

	decision := Decide(command, stored.State, now)
	if !decision.Accepted {
		return PlaceOrderResult{Reason: decision.Reason}, nil
	}

	newState := stored.State
	for _, event := range decision.Events {
		newState = Evolve(newState, event)
	}

	// One compare-and-save operation persists aggregate + outbox, or neither.
	saved, err := persistence.SaveWithOutbox(newState, decision.Events, stored.Version)
	if err != nil {
		return PlaceOrderResult{}, err
	}
	if saved == "conflict" {
		return PlaceOrderResult{Reason: "concurrent-change"}, nil
	}

	return PlaceOrderResult{Success: true, Order: newState}, nil
}
```

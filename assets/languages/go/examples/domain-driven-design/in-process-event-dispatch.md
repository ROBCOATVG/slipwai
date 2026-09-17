```go
package ordering

import "time"

// --- minimal supporting domain types (the Decider itself lives elsewhere in the skill) ---

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

// --- the pattern this file actually illustrates ---

type StoredOrder struct {
	State   OrderState
	Version int
}

// OrderRepository is the application-owned persistence port.
type OrderRepository interface {
	FindByID(orderID OrderID) (StoredOrder, bool, error)
	Save(state OrderState, expectedVersion int) (string, error) // "saved" | "conflict"
}

// OrderNotifier is the application-owned port for dispatching domain events.
type OrderNotifier interface {
	Notify(event OrderEvent) error
}

type PlaceOrderResult struct {
	Success bool
	Order   OrderState
	Reason  string
}

func HandlePlaceOrder(
	orderRepo OrderRepository,
	notifier OrderNotifier,
	command PlaceOrderCommand,
	now time.Time,
) (PlaceOrderResult, error) {
	stored, found, err := orderRepo.FindByID(command.OrderID)
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

	saved, err := orderRepo.Save(newState, stored.Version)
	if err != nil {
		return PlaceOrderResult{}, err
	}
	if saved == "conflict" {
		return PlaceOrderResult{Reason: "concurrent-change"}, nil
	}

	// Dispatch in-process — simple but non-durable.
	for _, event := range decision.Events {
		if err := notifier.Notify(event); err != nil {
			return PlaceOrderResult{}, err
		}
	}

	return PlaceOrderResult{Success: true, Order: newState}, nil
}
```

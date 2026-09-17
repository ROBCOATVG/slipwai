```go
package ordering

import (
	"fmt"
	"time"
)

type OrderItem struct {
	SKU      string
	Quantity int
}

// OrderCommand is the closed set of intents the Decider accepts.
type OrderCommand interface{ isOrderCommand() }

type PlaceCommand struct{}

func (PlaceCommand) isOrderCommand() {}

type ShipCommand struct {
	TrackingNumber string
}

func (ShipCommand) isOrderCommand() {}

// OrderEvent is the closed set of facts the Decider produces.
type OrderEvent interface{ isOrderEvent() }

type OrderPlaced struct {
	Items    []OrderItem
	PlacedAt time.Time
}

func (OrderPlaced) isOrderEvent() {}

type OrderShipped struct {
	TrackingNumber string
}

func (OrderShipped) isOrderEvent() {}

// OrderStatus names each lifecycle phase; OrderState only ever carries the
// fields valid for its current status, mirroring "Make Illegal States
// Unrepresentable" as closely as a single struct allows.
type OrderStatus string

const (
	StatusDraft   OrderStatus = "draft"
	StatusPlaced  OrderStatus = "placed"
	StatusShipped OrderStatus = "shipped"
)

type OrderState struct {
	Status         OrderStatus
	Items          []OrderItem
	PlacedAt       time.Time
	TrackingNumber string
}

// OrderDecision is the outcome of Decide: either accepted (carrying the
// events to append) or rejected (carrying a specific, named reason).
type OrderDecision struct {
	Accepted bool
	Events   []OrderEvent
	Reason   string // "order-not-draft" | "order-not-placed"
}

// Decide is step 1: command + current state → an explicit acceptance or rejection.
func Decide(command OrderCommand, state OrderState, now time.Time) OrderDecision {
	switch cmd := command.(type) {
	case PlaceCommand:
		if state.Status != StatusDraft {
			return OrderDecision{Reason: "order-not-draft"}
		}
		return OrderDecision{Accepted: true, Events: []OrderEvent{OrderPlaced{Items: state.Items, PlacedAt: now}}}
	case ShipCommand:
		if state.Status != StatusPlaced {
			return OrderDecision{Reason: "order-not-placed"}
		}
		return OrderDecision{Accepted: true, Events: []OrderEvent{OrderShipped{TrackingNumber: cmd.TrackingNumber}}}
	default:
		panic(fmt.Sprintf("unhandled command: %T", command))
	}
}

// Evolve is step 2: state + event → new state (pure state transformation).
func Evolve(state OrderState, event OrderEvent) OrderState {
	switch evt := event.(type) {
	case OrderPlaced:
		if state.Status != StatusDraft {
			panic(fmt.Sprintf("corrupt order history: OrderPlaced cannot follow %s", state.Status))
		}
		return OrderState{Status: StatusPlaced, Items: evt.Items, PlacedAt: evt.PlacedAt}
	case OrderShipped:
		if state.Status != StatusPlaced {
			panic(fmt.Sprintf("corrupt order history: OrderShipped cannot follow %s", state.Status))
		}
		next := state
		next.Status = StatusShipped
		next.TrackingNumber = evt.TrackingNumber
		return next
	default:
		panic(fmt.Sprintf("unhandled event: %T", event))
	}
}

// InitialState is step 3: the starting point for every new order.
var InitialState = OrderState{Status: StatusDraft, Items: nil}
```

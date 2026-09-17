```go
package ordering

import (
	"reflect"
	"testing"
	"time"
)

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
	Status   OrderStatus
	Items    []OrderItem
	PlacedAt time.Time
}

type PlaceCommand struct{}

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

func Decide(command PlaceCommand, state OrderState, now time.Time) OrderDecision {
	if state.Status != StatusDraft {
		return OrderDecision{Reason: "order-not-draft"}
	}
	return OrderDecision{Accepted: true, Events: []OrderEvent{OrderPlaced{Items: state.Items, PlacedAt: now}}}
}

func TestDecide_OrderPlacement(t *testing.T) {
	testItem := OrderItem{SKU: "mug-01", Quantity: 2}
	now := time.Date(2026, 3, 20, 0, 0, 0, 0, time.UTC)
	someDate := time.Date(2026, 3, 18, 0, 0, 0, 0, time.UTC)

	tests := []struct {
		name  string
		state OrderState
		want  OrderDecision
	}{
		{
			name:  "produces OrderPlaced event when placing a draft order",
			state: OrderState{Status: StatusDraft, Items: []OrderItem{testItem}},
			want: OrderDecision{
				Accepted: true,
				Events:   []OrderEvent{OrderPlaced{Items: []OrderItem{testItem}, PlacedAt: now}},
			},
		},
		{
			name:  "rejects placing an already-placed order with a reason",
			state: OrderState{Status: StatusPlaced, Items: []OrderItem{testItem}, PlacedAt: someDate},
			want:  OrderDecision{Reason: "order-not-draft"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Decide(PlaceCommand{}, tt.state, now)
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Decide() = %+v, want %+v", got, tt.want)
			}
		})
	}
}
```

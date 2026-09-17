```go
func newTestItem(t *testing.T, overrides ...func(*Item)) Item {
	t.Helper()
	item := Item{ID: "item-1", Name: "Test Item", WeightGrams: 100}
	for _, override := range overrides {
		override(&item)
	}
	return item
}

func newTestOrder(t *testing.T, overrides ...func(*Order)) Order {
	t.Helper()
	order := Order{
		ID:       "order-1",
		Items:    []Item{newTestItem(t)}, // ✅ Compose factories
		Customer: newTestCustomer(t),     // ✅ Compose factories
		Payment:  newTestPayment(t),      // ✅ Compose factories
	}
	for _, override := range overrides {
		override(&order)
	}
	return order
}

// Usage - override nested objects
func TestCalculateTotalWeightGrams_MultipleItems(t *testing.T) {
	order := newTestOrder(t, func(o *Order) {
		o.Items = []Item{
			newTestItem(t, func(i *Item) { i.WeightGrams = 100 }),
			newTestItem(t, func(i *Item) { i.WeightGrams = 200 }),
		}
	})

	if got := CalculateTotalWeightGrams(order); got != 300 {
		t.Fatalf("CalculateTotalWeightGrams() = %d, want 300", got)
	}
}
```

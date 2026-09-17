```go
func TestOrder_CalculateWeightGrams(t *testing.T) {
	order := CreateOrder([]Item{item1, item2})

	if got := order.CalculateWeightGrams(); got != 230 {
		t.Fatalf("CalculateWeightGrams() = %d, want 230", got)
	}
}
```

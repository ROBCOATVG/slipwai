```go
// ❌ Business rule in the route handler
func ApproveOrder(w http.ResponseWriter, r *http.Request) {
	order, _, _ := orderRepo.FindByID(r.Context(), orderID(r))
	if order.ItemCount > 100 {
		requireManagerApproval(order) // business rule!
	}
	// ...
}

// ✅ Business rule in the domain
type PlaceOrderResult struct {
	Order             Order
	RequiresApproval  bool
}

func PlaceOrder(order Order) PlaceOrderResult {
	if order.ItemCount > 100 {
		return PlaceOrderResult{RequiresApproval: true}
	}
	return PlaceOrderResult{Order: order}
}
```

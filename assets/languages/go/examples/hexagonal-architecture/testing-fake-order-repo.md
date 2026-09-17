```go
// ErrOrderNotFound is returned by any OrderRepository implementation —
// fake or real — when no order matches the given id.
var ErrOrderNotFound = errors.New("order not found")

// FakeOrderRepository is an in-memory OrderRepository for use-case tests.
// It implements the same interface a real adapter would, and exposes
// SavedEntities so tests can assert on what was actually saved.
type FakeOrderRepository struct {
	store         map[OrderID]Order
	SavedEntities []Order
}

func NewFakeOrderRepository() *FakeOrderRepository {
	return &FakeOrderRepository{store: make(map[OrderID]Order)}
}

func (r *FakeOrderRepository) FindByID(id OrderID) (Order, error) {
	order, ok := r.store[id]
	if !ok {
		return Order{}, ErrOrderNotFound
	}
	return order, nil
}

func (r *FakeOrderRepository) Save(order Order) error {
	r.store[order.ID] = order
	r.SavedEntities = append(r.SavedEntities, order)
	return nil
}
```

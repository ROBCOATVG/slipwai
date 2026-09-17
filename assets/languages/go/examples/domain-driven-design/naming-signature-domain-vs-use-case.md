```go
package ordering

type Money struct {
	MinorUnits int64
	Currency   string
}

type OrderID string

type NewOrder struct {
	OrderID OrderID
	Total   Money
}

type Order struct {
	ID    OrderID
	Total Money
}

type PlaceOrderResult struct {
	Success bool
	Reason  string
}

type PaymentResult struct {
	Success bool
	Reason  string
}

// OrderRepository and PaymentGateway are application-owned ports.
type OrderRepository interface {
	FindByID(orderID OrderID) (Order, bool, error)
	Save(order Order) error
}

type PaymentGateway interface {
	Charge(amount Money, orderID OrderID) (PaymentResult, error)
}

type Occasion struct {
	TotalPledged Money
	Budget       Money
}

type ContributorEligibility struct {
	MayPledge bool
}

type Pledge struct {
	Amount Money
}

type PledgeDecision struct {
	Accepted bool
	Reason   string
}

// PlaceOrder is a use case — it takes application-owned collaboration
// contracts (ports) as parameters.
func PlaceOrder(repo OrderRepository, gateway PaymentGateway, order NewOrder) (PlaceOrderResult, error) {
	panic("not implemented")
}

// PledgeContribution is a domain service — it takes only domain values.
func PledgeContribution(occasion Occasion, eligibility ContributorEligibility, pledge Pledge) PledgeDecision {
	panic("not implemented")
}
```

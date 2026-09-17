```go
package eventsourcing

import "fmt"

// OrderPlacedV1 is the shape OrderPlaced was originally persisted in: a
// flat total and currency.
type OrderPlacedV1 struct {
	OrderID         string
	TotalMinorUnits int64
	Currency        Currency
}

// OrderPlacedV2 is the current persisted shape: the flat total was
// restructured into a nested amount.
type OrderPlacedV2 struct {
	OrderID     string
	TotalAmount Money
}

// OrderPlaced is the shape the domain folds today.
type OrderPlaced = OrderPlacedV2

// upcastOrderPlacedV1toV2 maps the original flat shape onto the current
// nested one; only structure changes, never business meaning.
func upcastOrderPlacedV1toV2(e OrderPlacedV1) OrderPlacedV2 {
	return OrderPlacedV2{
		OrderID:     e.OrderID,
		TotalAmount: Money{MinorUnits: e.TotalMinorUnits, Currency: e.Currency},
	}
}

// UpcastOrderPlaced dispatches on whichever concrete shape the envelope was
// actually persisted as, and upcasts forward to the current shape. raw is
// deliberately typed as any: which version comes off the wire is
// determined by stored data, not by this build's type system, so an older
// deployment reading a newer envelope during a rolling upgrade is a real,
// expected occurrence — not a programmer error — and must come back as an
// error rather than a panic.
func UpcastOrderPlaced(raw any) (OrderPlaced, error) {
	switch v := raw.(type) {
	case OrderPlacedV1:
		return upcastOrderPlacedV1toV2(v), nil
	case OrderPlacedV2:
		return v, nil
	default:
		return OrderPlaced{}, fmt.Errorf("order-placed upcaster: unrecognised stored version %T", raw)
	}
}
```

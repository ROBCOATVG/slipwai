```go
package eventsourcing

import "fmt"

// BalanceViewStatus is the discriminant of BalanceView.
type BalanceViewStatus int

const (
	BalanceViewUnopened BalanceViewStatus = iota
	BalanceViewOpen
)

// BalanceView is a read-optimised row: the projection of an account's events
// into the shape a balance-enquiry query wants.
type BalanceView struct {
	Status            BalanceViewStatus
	AccountID         StreamID
	BalanceMinorUnits int64
	Currency          Currency
}

// EmptyBalanceView is the seed value the fold starts from.
var EmptyBalanceView = BalanceView{Status: BalanceViewUnopened}

// AccountProjectionEnvelope carries an account event together with the
// metadata a projection needs but the domain event itself does not: which
// stream it belongs to, and where it sits in the store-wide order.
type AccountProjectionEnvelope struct {
	StreamID       StreamID
	GlobalPosition int64
	Data           AccountEvent
}

// CorruptProjectionError reports that an event could not have followed the
// projection's current state — a corrupted or mis-ordered stream, which the
// caller must handle rather than the fold panicking mid-way.
type CorruptProjectionError struct {
	View  BalanceViewStatus
	Event AccountEvent
}

func (e *CorruptProjectionError) Error() string {
	return fmt.Sprintf("corrupt balance projection: %T cannot follow view status %d", e.Event, e.View)
}

func corruptBalanceProjection(view BalanceView, event AccountEvent) error {
	return &CorruptProjectionError{View: view.Status, Event: event}
}

// ApplyToBalanceView folds one envelope into the running BalanceView.
func ApplyToBalanceView(view BalanceView, envelope AccountProjectionEnvelope) (BalanceView, error) {
	switch e := envelope.Data.(type) {
	case AccountOpened:
		if view.Status != BalanceViewUnopened {
			return view, corruptBalanceProjection(view, envelope.Data)
		}
		return BalanceView{
			Status:    BalanceViewOpen,
			AccountID: envelope.StreamID,
			Currency:  e.Currency,
		}, nil

	case MoneyDeposited:
		if view.Status != BalanceViewOpen ||
			view.AccountID != envelope.StreamID ||
			!isPositiveMoney(e.Amount) ||
			e.Amount.Currency != view.Currency {
			return view, corruptBalanceProjection(view, envelope.Data)
		}
		balance, err := addMinorUnits(view.BalanceMinorUnits, e.Amount.MinorUnits)
		if err != nil {
			return view, corruptBalanceProjection(view, envelope.Data)
		}
		view.BalanceMinorUnits = balance
		return view, nil

	case MoneyWithdrawn:
		if view.Status != BalanceViewOpen ||
			view.AccountID != envelope.StreamID ||
			!isPositiveMoney(e.Amount) ||
			e.Amount.Currency != view.Currency ||
			e.Amount.MinorUnits > view.BalanceMinorUnits {
			return view, corruptBalanceProjection(view, envelope.Data)
		}
		balance, err := addMinorUnits(view.BalanceMinorUnits, -e.Amount.MinorUnits)
		if err != nil {
			return view, corruptBalanceProjection(view, envelope.Data)
		}
		view.BalanceMinorUnits = balance
		return view, nil

	default:
		panic(fmt.Sprintf("ApplyToBalanceView: unhandled AccountEvent %T", envelope.Data))
	}
}
```

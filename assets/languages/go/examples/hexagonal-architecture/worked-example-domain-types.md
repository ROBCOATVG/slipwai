```go
// Package domain holds the gifting bounded context's pure business types —
// no ports, no infrastructure, no async.
// gifting/hexagon/domain/types.go
package domain

import "fmt"

// OccasionID, ContributorID, and PledgeID are distinct string-based types so
// the compiler rejects passing the wrong kind of ID by mistake.
type (
	OccasionID    string
	ContributorID string
	PledgeID      string
)

type Currency string

const (
	GBP Currency = "GBP"
	USD Currency = "USD"
	EUR Currency = "EUR"
)

// Money is an immutable value: minor units of a specific currency.
type Money struct {
	MinorUnits int64
	Currency   Currency
}

// NewMoney validates and constructs a Money value.
func NewMoney(minorUnits int64, currency Currency) (Money, error) {
	if minorUnits < 0 {
		return Money{}, fmt.Errorf("invalid money: minor units must not be negative, got %d", minorUnits)
	}
	return Money{MinorUnits: minorUnits, Currency: currency}, nil
}

// Occasion is the gift-giving-event aggregate.
type Occasion struct {
	ID              OccasionID
	Name            string
	Budget          Money
	TotalPledged    Money
	IsFundingClosed bool
}

// PledgeRecorded is the domain event describing an accepted pledge.
type PledgeRecorded struct {
	ID            PledgeID
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

// RejectionReason enumerates why RecordPledge can decline to add a pledge.
type RejectionReason string

const (
	ReasonNonPositiveAmount RejectionReason = "non-positive-amount"
	ReasonCurrencyMismatch  RejectionReason = "currency-mismatch"
	ReasonExceedsBudget     RejectionReason = "exceeds-budget"
	ReasonFundingClosed     RejectionReason = "funding-closed"
)

// PledgeDecision is the result of attempting to record a pledge. Ok reports
// which case applies: true means Occasion and Events are populated; false
// means Reason explains the rejection. There is no third, "error" case here
// — record_pledge is pure and every expected outcome is a returned value.
type PledgeDecision struct {
	Ok       bool
	Occasion Occasion
	Events   []PledgeRecorded
	Reason   RejectionReason
}
```

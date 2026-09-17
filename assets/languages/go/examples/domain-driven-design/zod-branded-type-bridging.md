```go
package ddd

import (
	"errors"
	"fmt"
	"strings"
)

type Currency string

const (
	CurrencyGBP Currency = "GBP"
	CurrencyUSD Currency = "USD"
	CurrencyEUR Currency = "EUR"
)

type Money struct {
	MinorUnits int64
	Currency   Currency
}

type OccasionID string
type ContributorID string

func NewOccasionID(raw string) (OccasionID, error) {
	if strings.TrimSpace(raw) == "" {
		return "", errors.New("occasion id cannot be empty")
	}
	return OccasionID(raw), nil
}

func NewContributorID(raw string) (ContributorID, error) {
	if strings.TrimSpace(raw) == "" {
		return "", errors.New("contributor id cannot be empty")
	}
	return ContributorID(raw), nil
}

func NewMoney(minorUnits int64, currency Currency) (Money, error) {
	if minorUnits < 0 {
		return Money{}, errors.New("money cannot be negative")
	}
	return Money{MinorUnits: minorUnits, Currency: currency}, nil
}

func ParseCurrency(raw string) (Currency, error) {
	switch Currency(raw) {
	case CurrencyGBP, CurrencyUSD, CurrencyEUR:
		return Currency(raw), nil
	default:
		return "", fmt.Errorf("unsupported currency: %s", raw)
	}
}

// PledgeInput is the validated shape produced at the trust boundary.
type PledgeInput struct {
	OccasionID    OccasionID
	ContributorID ContributorID
	Amount        Money
}

// RawPledgeInput is the untrusted shape as received, e.g. decoded JSON.
type RawPledgeInput struct {
	OccasionID    string
	ContributorID string
	Amount        struct {
		MinorUnits int64
		Currency   string
	}
}

// ParsePledgeInput parses raw, untrusted input into validated domain types
// at the trust boundary. A non-nil error means the caller (e.g. an HTTP
// handler) should respond with a 4xx, not a 500.
func ParsePledgeInput(raw RawPledgeInput) (PledgeInput, error) {
	occasionID, err := NewOccasionID(raw.OccasionID)
	if err != nil {
		return PledgeInput{}, err
	}
	contributorID, err := NewContributorID(raw.ContributorID)
	if err != nil {
		return PledgeInput{}, err
	}
	if raw.Amount.MinorUnits <= 0 {
		return PledgeInput{}, errors.New("amount.minorUnits must be a positive integer")
	}
	currency, err := ParseCurrency(raw.Amount.Currency)
	if err != nil {
		return PledgeInput{}, err
	}
	amount, err := NewMoney(raw.Amount.MinorUnits, currency)
	if err != nil {
		return PledgeInput{}, err
	}
	return PledgeInput{OccasionID: occasionID, ContributorID: contributorID, Amount: amount}, nil
}

type GiftIdea struct {
	ID          string
	Description string
}

// OccasionRow is the raw persistence shape as read from storage.
type OccasionRow struct {
	ID                string
	Name              string
	BudgetMinorUnits  int64
	BudgetCurrency    string
	PledgedMinorUnits int64
	IsFundingClosed   bool
}

type Occasion struct {
	ID              OccasionID
	Name            string
	GiftIdeas       []GiftIdea
	Budget          Money
	TotalPledged    Money
	IsFundingClosed bool
}

// OccasionFromRow reconstitutes an Occasion from persistence, using the
// same validating constructors as the trust-boundary parser above. This
// runs at the integration boundary -- a driven adapter in hexagonal
// architecture loads the gift ideas alongside the row.
func OccasionFromRow(row OccasionRow, giftIdeas []GiftIdea) (Occasion, error) {
	id, err := NewOccasionID(row.ID)
	if err != nil {
		return Occasion{}, err
	}
	currency, err := ParseCurrency(row.BudgetCurrency)
	if err != nil {
		return Occasion{}, err
	}
	budget, err := NewMoney(row.BudgetMinorUnits, currency)
	if err != nil {
		return Occasion{}, err
	}
	totalPledged, err := NewMoney(row.PledgedMinorUnits, currency)
	if err != nil {
		return Occasion{}, err
	}
	return Occasion{
		ID:              id,
		Name:            row.Name,
		GiftIdeas:       giftIdeas,
		Budget:          budget,
		TotalPledged:    totalPledged,
		IsFundingClosed: row.IsFundingClosed,
	}, nil
}
```

```go
package ddd

import (
	"errors"
	"strings"
)

type Occasion struct {
	ID        OccasionID
	Name      string
	Budget    Money
	GiftIdeas []GiftIdea
}

// NewOccasion is the factory that enforces invariants on creation (the
// always-valid principle). It returns an error only for a genuine invariant
// violation — not for an expected business outcome.
func NewOccasion(id OccasionID, name string, budget Money) (Occasion, error) {
	trimmed := strings.TrimSpace(name)
	if trimmed == "" {
		return Occasion{}, errors.New("occasion name is required")
	}
	if budget.MinorUnits < 0 {
		return Occasion{}, errors.New("budget minor units must be non-negative")
	}
	return Occasion{ID: id, Name: trimmed, Budget: budget}, nil
}

// The application/driving edge creates the ID and passes the typed value in.
// Domain creation validates business invariants without a UUID dependency.

type AddGiftIdeaOutcome int

const (
	GiftIdeaAdded AddGiftIdeaOutcome = iota
	GiftIdeaRejectedCurrencyMismatch
	GiftIdeaRejectedExceedsBudget
)

type AddGiftIdeaResult struct {
	Outcome  AddGiftIdeaOutcome
	Occasion Occasion
}

// AddGiftIdea enforces the budget invariant as a state transition. It
// returns a result for the expected business outcomes, and panics only when
// the aggregate's own Money invariant has already been corrupted — a bug,
// not a business rule.
func AddGiftIdea(occasion Occasion, idea NewGiftIdea) AddGiftIdeaResult {
	mismatch := idea.EstimatedCost.Currency != occasion.Budget.Currency
	for _, item := range occasion.GiftIdeas {
		if item.EstimatedCost.Currency != occasion.Budget.Currency {
			mismatch = true
		}
	}
	if mismatch {
		return AddGiftIdeaResult{Outcome: GiftIdeaRejectedCurrencyMismatch}
	}

	totalCost := 0
	for _, item := range occasion.GiftIdeas {
		if item.EstimatedCost.MinorUnits < 0 {
			panic("invalid Money invariant")
		}
		totalCost += item.EstimatedCost.MinorUnits
	}

	if idea.EstimatedCost.MinorUnits < 0 {
		panic("invalid Money invariant")
	}
	if totalCost > occasion.Budget.MinorUnits {
		panic("invalid Occasion budget invariant")
	}
	if idea.EstimatedCost.MinorUnits > occasion.Budget.MinorUnits-totalCost {
		return AddGiftIdeaResult{Outcome: GiftIdeaRejectedExceedsBudget}
	}

	next := make([]GiftIdea, len(occasion.GiftIdeas), len(occasion.GiftIdeas)+1)
	copy(next, occasion.GiftIdeas)
	next = append(next, GiftIdea{EstimatedCost: idea.EstimatedCost})
	occasion.GiftIdeas = next
	return AddGiftIdeaResult{Outcome: GiftIdeaAdded, Occasion: occasion}
}
```

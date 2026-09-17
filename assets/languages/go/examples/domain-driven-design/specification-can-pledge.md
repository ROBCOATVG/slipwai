```go
package ddd

type Currency string

type Money struct {
	MinorUnits int64
	Currency   Currency
}

type GiftIdeaStatus string

const (
	GiftIdeaStatusProposed  GiftIdeaStatus = "proposed"
	GiftIdeaStatusSelected  GiftIdeaStatus = "selected"
	GiftIdeaStatusPurchased GiftIdeaStatus = "purchased"
)

type GiftIdea struct {
	ID     string
	Status GiftIdeaStatus
}

type Occasion struct {
	ID              string
	GiftIdeas       []GiftIdea
	Budget          Money
	TotalPledged    Money
	IsFundingClosed bool
}

type ContributorEligibility struct {
	ContributorID string
	MayPledge     bool
}

const maxSafeInteger = 1<<53 - 1

func isSafeInteger(v int64) bool {
	return v >= -maxSafeInteger && v <= maxSafeInteger
}

// CanPledge is a specification: "can this eligible contributor pledge to
// this occasion?"
func CanPledge(occasion Occasion, eligibility ContributorEligibility, amount Money) bool {
	values := []int64{amount.MinorUnits, occasion.TotalPledged.MinorUnits, occasion.Budget.MinorUnits}
	for _, v := range values {
		if !isSafeInteger(v) {
			return false
		}
	}
	if occasion.TotalPledged.MinorUnits > occasion.Budget.MinorUnits {
		return false
	}
	return eligibility.MayPledge &&
		!occasion.IsFundingClosed &&
		amount.MinorUnits > 0 &&
		amount.Currency == occasion.TotalPledged.Currency &&
		occasion.TotalPledged.Currency == occasion.Budget.Currency &&
		amount.MinorUnits <= occasion.Budget.MinorUnits-occasion.TotalPledged.MinorUnits
}

// IsGiftReady composes specifications into a more complex eligibility check.
func IsGiftReady(occasion Occasion) bool {
	if occasion.TotalPledged.MinorUnits < occasion.Budget.MinorUnits {
		return false
	}
	for _, idea := range occasion.GiftIdeas {
		if idea.Status == GiftIdeaStatusSelected {
			return true
		}
	}
	return false
}
```

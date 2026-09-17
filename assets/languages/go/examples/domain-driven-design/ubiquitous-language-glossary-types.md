```go
package ddd

// OccasionID and GiftIdeaID are distinct string types so IDs belonging to
// different entities cannot be mixed up at compile time.
type OccasionID string
type GiftIdeaID string

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

type GiftIdeaStatus string

const (
	GiftIdeaStatusProposed  GiftIdeaStatus = "proposed"
	GiftIdeaStatusSelected  GiftIdeaStatus = "selected"
	GiftIdeaStatusPurchased GiftIdeaStatus = "purchased"
)

// GiftIdea uses domain language.
type GiftIdea struct {
	ID            GiftIdeaID
	Description   string
	Occasion      OccasionID
	EstimatedCost Money
	Status        GiftIdeaStatus
}

// Item is technical jargon -- avoid this shape. ID/Text/ParentID say
// nothing about the domain, unlike GiftIdea's fields above.
type Item struct {
	ID       string
	Text     string
	ParentID string
}
```

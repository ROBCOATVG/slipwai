```go
package ddd

import "time"

// GiftItemStatus enumerates the lifecycle of a gift item.
type GiftItemStatus string

const (
	GiftItemStatusIdea      GiftItemStatus = "idea"
	GiftItemStatusSelected  GiftItemStatus = "selected"
	GiftItemStatusPurchased GiftItemStatus = "purchased"
)

// GiftItem is a minimal stand-in for the sibling type used by
// CalculateCommittedTotal below.
type GiftItem struct {
	Status     GiftItemStatus
	PricePence int
}

// FormatEventDate is pure but NOT domain -- it formats for human display.
// Belongs in presentation code; a hexagonal app may place it at the driving edge.
func FormatEventDate(eventDate *time.Time) string {
	if eventDate == nil {
		return ""
	}
	return eventDate.Format("January 2, 2006")
}

// IsPastEvent is pure AND domain -- a business rule that affects behaviour.
// The application supplies now as data; domain code does not read a clock.
// Belongs in domain policy for events.
func IsPastEvent(eventDate *time.Time, now time.Time) bool {
	if eventDate == nil {
		return false
	}
	return eventDate.Before(now)
}

// CalculateCommittedTotal is pure AND domain -- a business calculation.
// Belongs in domain policy for budgets.
func CalculateCommittedTotal(items []GiftItem) int {
	total := 0
	for _, item := range items {
		if item.Status != GiftItemStatusIdea {
			total += item.PricePence
		}
	}
	return total
}
```

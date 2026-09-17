```go
package ddd

type Currency string

type Money struct {
	MinorUnits int64
	Currency   Currency
}

type OccasionID string
type GiftIdeaID string

type GiftIdea struct {
	ID          GiftIdeaID
	Description string
}

type Occasion struct {
	ID              OccasionID
	Name            string
	GiftIdeas       []GiftIdea
	Budget          Money
	TotalPledged    Money
	IsFundingClosed bool
}

// RenameOccasion returns a new Occasion with the name changed, leaving the
// original untouched. Go has no structural spread, so the struct is
// copied by value and only the changed field is overwritten -- a shallow
// copy is safe here since GiftIdeas is never mutated in place.
func RenameOccasion(occasion Occasion, newName string) Occasion {
	renamed := occasion
	renamed.Name = newName
	return renamed
}
```

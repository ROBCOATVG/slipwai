```go
package ddd

// Occasion (WRONG) is too large: User doesn't need to be in the aggregate.
type Occasion struct {
	Organizer    User   // embedded user — wrong!
	Contributors []User // embedded users — wrong!
	GiftIdeas    []GiftIdea
}

// Occasion (RIGHT) is right-sized: only what's needed for consistency.
type Occasion struct {
	OrganizerID UserID     // reference by ID
	GiftIdeas   []GiftIdea // owned — needed for the budget invariant
	Budget      Money      // owned — needed for the budget invariant
}
```

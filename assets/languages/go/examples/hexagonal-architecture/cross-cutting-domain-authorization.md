```go
package domain

// CloseFundingReason enumerates why CloseFunding can decline to close funding.
type CloseFundingReason string

const ReasonNotOrganizer CloseFundingReason = "not-organizer"

// CloseFundingResult reports which case applies: Ok means Occasion is
// populated; otherwise Reason explains the rejection.
type CloseFundingResult struct {
	Ok       bool
	Occasion Occasion
	Reason   CloseFundingReason
}

// CloseFunding is domain logic: "only the organizer can close funding" is a
// business rule, expressed as a returned value, never a panic.
func CloseFunding(occasion Occasion, requesterID ContributorID) CloseFundingResult {
	if occasion.OrganizerID != requesterID {
		return CloseFundingResult{Reason: ReasonNotOrganizer}
	}
	updated := occasion
	updated.IsFundingClosed = true
	return CloseFundingResult{Ok: true, Occasion: updated}
}
```

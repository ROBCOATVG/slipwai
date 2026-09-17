```go
package ddd

// Occasion and PledgeRecorded are minimal stand-ins; the full definitions
// live alongside the rest of the domain model.
type Occasion struct {
	ID                     string
	TotalPledgedMinorUnits int64
	BudgetMinorUnits       int64
}

type PledgeRecorded struct {
	PledgeID      string
	OccasionID    string
	ContributorID string
	AmountMinor   int64
}

// DomainRejectionReason enumerates reasons a pure domain service can
// determine on its own.
type DomainRejectionReason string

const (
	ReasonContributorIneligible DomainRejectionReason = "contributor-ineligible"
	ReasonNonPositiveAmount     DomainRejectionReason = "non-positive-amount"
	ReasonCurrencyMismatch      DomainRejectionReason = "currency-mismatch"
	ReasonExceedsBudget         DomainRejectionReason = "exceeds-budget"
	ReasonFundingClosed         DomainRejectionReason = "funding-closed"
)

// ApplicationRejectionReason enumerates outcomes only the surrounding use
// case can detect -- e.g. the aggregate did not exist, or changed
// concurrently since it was loaded.
type ApplicationRejectionReason string

const (
	ReasonNotFound         ApplicationRejectionReason = "not-found"
	ReasonConcurrentChange ApplicationRejectionReason = "concurrent-change"
)

// PledgeDecision is what a pure domain service can determine: either the
// pledge is accepted (with the updated Occasion and raised events) or it
// is rejected for a domain-level reason.
type PledgeDecision struct {
	Success  bool
	Occasion Occasion
	Events   []PledgeRecorded
	Reason   DomainRejectionReason
}

// PledgeResult widens PledgeDecision with application-level outcomes that
// only the use case orchestrating persistence can detect. IsApplicationErr
// distinguishes an ApplicationReason from a domain Reason when Success is
// false.
type PledgeResult struct {
	Success           bool
	Occasion          Occasion
	Events            []PledgeRecorded
	Reason            DomainRejectionReason
	IsApplicationErr  bool
	ApplicationReason ApplicationRejectionReason
}

// FromDecision lifts a domain-level PledgeDecision into a PledgeResult.
func FromDecision(d PledgeDecision) PledgeResult {
	return PledgeResult{
		Success:  d.Success,
		Occasion: d.Occasion,
		Events:   d.Events,
		Reason:   d.Reason,
	}
}

// ApplicationRejection constructs a PledgeResult for an application-level
// failure (not-found, concurrent-change) that a domain service could
// never produce on its own.
func ApplicationRejection(reason ApplicationRejectionReason) PledgeResult {
	return PledgeResult{IsApplicationErr: true, ApplicationReason: reason}
}
```

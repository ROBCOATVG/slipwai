```go
package ddd

// PledgeReason enumerates the business reasons a pledge can be rejected.
type PledgeReason string

const (
	ContributorIneligible PledgeReason = "contributor-ineligible"
	NonPositiveAmount     PledgeReason = "non-positive-amount"
	CurrencyMismatch      PledgeReason = "currency-mismatch"
	ExceedsBudget         PledgeReason = "exceeds-budget"
	FundingClosed         PledgeReason = "funding-closed"
)

type PledgeDecisionOutcome int

const (
	PledgeAccepted PledgeDecisionOutcome = iota
	PledgeRejected
)

// PledgeDecision is the domain-level result: acceptance carries the updated
// aggregate and its events, rejection carries one specific business reason.
type PledgeDecision struct {
	Outcome  PledgeDecisionOutcome
	Occasion Occasion
	Events   []PledgeRecorded
	Reason   PledgeReason
}

// ApplicationReason enumerates outcomes that belong to the use case, not the
// domain: the aggregate couldn't even be found, or it changed underneath us.
type ApplicationReason string

const (
	NotFound         ApplicationReason = "not-found"
	ConcurrentChange ApplicationReason = "concurrent-change"
)

type PledgeResultKind int

const (
	PledgeResultDecision PledgeResultKind = iota
	PledgeResultApplicationFailure
)

// PledgeResult joins the domain decision with the application-level
// outcomes that only the use case layer can produce.
type PledgeResult struct {
	Kind              PledgeResultKind
	Decision          PledgeDecision
	ApplicationReason ApplicationReason
}
```

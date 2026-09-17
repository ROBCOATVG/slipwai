```go
// gifting/hexagon/application/pledging.go — driving port + application result
package application

import (
	"context"

	"gifting/hexagon/domain"
)

// AuthenticatedPledger is an opaque, provider-free principal. Only the
// authentication adapter constructs one in production; the request body
// cannot forge it.
type AuthenticatedPledger struct {
	ContributorID domain.ContributorID
}

// Extra rejection reasons that only the application layer can produce, on
// top of the ones domain.RecordPledge already returns.
const (
	ReasonNotFound         domain.RejectionReason = "not-found"
	ReasonConcurrentChange domain.RejectionReason = "concurrent-change"
)

// PledgeResult extends domain.PledgeDecision: at the application boundary,
// Reason may additionally be "not-found" or "concurrent-change".
type PledgeResult = domain.PledgeDecision

// StoredOccasion pairs an Occasion with the version used for optimistic
// concurrency control.
type StoredOccasion struct {
	Value   domain.Occasion
	Version int
}

// PledgeToOccasionCommand is the driving port's input.
type PledgeToOccasionCommand struct {
	PledgeID   domain.PledgeID
	OccasionID domain.OccasionID
	Principal  AuthenticatedPledger
	Amount     domain.Money
}

// ForPledgingToOccasions is the driving port: how the outside world asks to
// pledge to an occasion.
type ForPledgingToOccasions interface {
	PledgeToOccasion(ctx context.Context, cmd PledgeToOccasionCommand) (PledgeResult, error)
}

// SaveOutcome is the result of an atomic compare-and-save.
type SaveOutcome string

const (
	Saved    SaveOutcome = "saved"
	Conflict SaveOutcome = "conflict"
)

// PledgePersistence is the application-owned, atomic driven port: it loads a
// versioned occasion and saves it plus its outbox events in one operation.
type PledgePersistence interface {
	FindOccasionByID(ctx context.Context, id domain.OccasionID) (StoredOccasion, bool, error)
	SaveWithOutbox(ctx context.Context, occasion domain.Occasion, events []domain.PledgeRecorded, expectedVersion int) (SaveOutcome, error)
}

// PledgeProjection is the application-owned, idempotent driven port. event is
// a validated immutable log record: one ID permanently names one payload.
// Implementations must be safe against redelivery.
type PledgeProjection interface {
	RecordFrom(ctx context.Context, event domain.PledgeRecorded) error
}
```

```go
package giftpurchase

type OccasionID string

// GiftPurchaseStep is the closed set of lifecycle phases for a gift purchase.
type GiftPurchaseStep string

const (
	StepAwaitingPayment  GiftPurchaseStep = "awaiting-payment"
	StepAwaitingShipment GiftPurchaseStep = "awaiting-shipment"
	StepComplete         GiftPurchaseStep = "complete"
	StepFailed           GiftPurchaseStep = "failed"
)

// GiftPurchasePhase carries only the fields valid for its current Step.
type GiftPurchasePhase struct {
	Step           GiftPurchaseStep
	OccasionID     OccasionID // valid when Step == StepAwaitingPayment
	PaymentID      string     // valid when Step == StepAwaitingShipment
	TrackingNumber string     // valid when Step == StepComplete
	Reason         string     // valid when Step == StepFailed
}

type GiftPurchaseProcess struct {
	Phase             GiftPurchasePhase
	ProcessedEventIDs []string
}

// GiftPurchaseEvent is the closed set of facts the process manager reacts to.
type GiftPurchaseEvent interface {
	EventID() string
}

type PaymentSucceeded struct {
	ID        string
	PaymentID string
}

func (e PaymentSucceeded) EventID() string { return e.ID }

type PaymentFailed struct {
	ID string
}

func (e PaymentFailed) EventID() string { return e.ID }

type GiftShipped struct {
	ID             string
	TrackingNumber string
}

func (e GiftShipped) EventID() string { return e.ID }

// GiftPurchaseCommand is the closed set of follow-up commands the process
// manager emits.
type GiftPurchaseCommand interface{ isGiftPurchaseCommand() }

type ShipGift struct {
	PaymentID      string
	IdempotencyKey string
}

func (ShipGift) isGiftPurchaseCommand() {}

type ReleaseBudgetHold struct {
	OccasionID     OccasionID
	IdempotencyKey string
}

func (ReleaseBudgetHold) isGiftPurchaseCommand() {}

// ProcessOutcome distinguishes a real state change from a no-op — duplicates
// and out-of-order events are rejected, never silently swallowed.
type ProcessOutcome string

const (
	OutcomeApplied    ProcessOutcome = "applied"
	OutcomeDuplicate  ProcessOutcome = "duplicate"
	OutcomeOutOfOrder ProcessOutcome = "out-of-order"
)

type ProcessReaction struct {
	Outcome  ProcessOutcome
	NewState GiftPurchaseProcess
	Commands []GiftPurchaseCommand
}

// AdvanceGiftPurchase applies each event once, and only in the phase that
// can consume it.
func AdvanceGiftPurchase(state GiftPurchaseProcess, event GiftPurchaseEvent) ProcessReaction {
	for _, id := range state.ProcessedEventIDs {
		if id == event.EventID() {
			return ProcessReaction{Outcome: OutcomeDuplicate, NewState: state}
		}
	}
	processedEventIDs := append(append([]string{}, state.ProcessedEventIDs...), event.EventID())

	switch evt := event.(type) {
	case PaymentSucceeded:
		if state.Phase.Step != StepAwaitingPayment {
			return ProcessReaction{Outcome: OutcomeOutOfOrder, NewState: state}
		}
		return ProcessReaction{
			Outcome: OutcomeApplied,
			NewState: GiftPurchaseProcess{
				Phase:             GiftPurchasePhase{Step: StepAwaitingShipment, PaymentID: evt.PaymentID},
				ProcessedEventIDs: processedEventIDs,
			},
			Commands: []GiftPurchaseCommand{ShipGift{PaymentID: evt.PaymentID, IdempotencyKey: evt.ID}},
		}
	case PaymentFailed:
		if state.Phase.Step != StepAwaitingPayment {
			return ProcessReaction{Outcome: OutcomeOutOfOrder, NewState: state}
		}
		occasionID := state.Phase.OccasionID
		return ProcessReaction{
			Outcome: OutcomeApplied,
			NewState: GiftPurchaseProcess{
				Phase:             GiftPurchasePhase{Step: StepFailed, Reason: "payment-declined"},
				ProcessedEventIDs: processedEventIDs,
			},
			Commands: []GiftPurchaseCommand{ReleaseBudgetHold{OccasionID: occasionID, IdempotencyKey: evt.ID}},
		}
	case GiftShipped:
		if state.Phase.Step != StepAwaitingShipment {
			return ProcessReaction{Outcome: OutcomeOutOfOrder, NewState: state}
		}
		return ProcessReaction{
			Outcome: OutcomeApplied,
			NewState: GiftPurchaseProcess{
				Phase:             GiftPurchasePhase{Step: StepComplete, TrackingNumber: evt.TrackingNumber},
				ProcessedEventIDs: processedEventIDs,
			},
		}
	default:
		panic("unhandled gift purchase event")
	}
}
```

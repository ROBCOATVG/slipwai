```go
package eventsourcing

import (
	"errors"
	"fmt"
)

// Currency is an ISO 4217 currency code.
type Currency string

// Money is an amount expressed in integer minor units (e.g. pence, cents).
// Minor units are always an integer — never a float — so no rounding error
// can creep into a balance.
type Money struct {
	MinorUnits int64
	Currency   Currency
}

// AccountStatus is the discriminant of AccountState.
type AccountStatus int

const (
	AccountUnopened AccountStatus = iota
	AccountOpen
)

func (s AccountStatus) String() string {
	switch s {
	case AccountUnopened:
		return "unopened"
	case AccountOpen:
		return "open"
	default:
		return "unknown"
	}
}

// AccountState is the Decider's state. Balance is meaningful only once
// Status is AccountOpen.
type AccountState struct {
	Status  AccountStatus
	Balance Money
}

// InitialState is the state of a stream that has never been opened.
var InitialState = AccountState{Status: AccountUnopened}

// AccountCommand is the closed set of commands the account Decider accepts.
// It is implemented only by the types declared alongside it in this file —
// the unexported marker method keeps the set closed, standing in for
// TypeScript's discriminated union.
type AccountCommand interface {
	isAccountCommand()
}

// OpenAccount opens a new account in the given currency.
type OpenAccount struct {
	Currency Currency
}

func (OpenAccount) isAccountCommand() {}

// DepositMoney credits an open account.
type DepositMoney struct {
	Amount Money
}

func (DepositMoney) isAccountCommand() {}

// WithdrawMoney debits an open account.
type WithdrawMoney struct {
	Amount Money
}

func (WithdrawMoney) isAccountCommand() {}

// AccountEvent is the closed set of facts the account Decider can record.
type AccountEvent interface {
	isAccountEvent()
}

// AccountOpened records that an account was opened in a currency.
type AccountOpened struct {
	Currency Currency
}

func (AccountOpened) isAccountEvent() {}

// MoneyDeposited records a credit to the balance.
type MoneyDeposited struct {
	Amount Money
}

func (MoneyDeposited) isAccountEvent() {}

// MoneyWithdrawn records a debit to the balance.
type MoneyWithdrawn struct {
	Amount Money
}

func (MoneyWithdrawn) isAccountEvent() {}

// RejectionReason is the closed set of reasons Decide can refuse a command.
type RejectionReason string

const (
	ReasonAlreadyOpen       RejectionReason = "already-open"
	ReasonNotOpen           RejectionReason = "not-open"
	ReasonInvalidAmount     RejectionReason = "invalid-amount"
	ReasonCurrencyMismatch  RejectionReason = "currency-mismatch"
	ReasonBalanceOverflow   RejectionReason = "balance-overflow"
	ReasonInsufficientFunds RejectionReason = "insufficient-funds"
)

// Decision is the result of Decide: either accepted, carrying the events to
// append, or rejected, carrying the reason.
type Decision struct {
	Accepted bool
	Events   []AccountEvent
	Reason   RejectionReason
}

func accept(events []AccountEvent) Decision {
	return Decision{Accepted: true, Events: events}
}

func reject(reason RejectionReason) Decision {
	return Decision{Reason: reason}
}

func isPositiveMoney(m Money) bool {
	return m.MinorUnits > 0
}

// Decide answers "what should happen?" for a command against the current
// state. It is pure: it only returns the events to append, or a rejection —
// it never mutates state and never talks to infrastructure.
func Decide(cmd AccountCommand, state AccountState) Decision {
	switch c := cmd.(type) {
	case OpenAccount:
		if state.Status == AccountOpen {
			return reject(ReasonAlreadyOpen)
		}
		return accept([]AccountEvent{AccountOpened{Currency: c.Currency}})

	case DepositMoney:
		if state.Status != AccountOpen {
			return reject(ReasonNotOpen)
		}
		if !isPositiveMoney(c.Amount) {
			return reject(ReasonInvalidAmount)
		}
		if c.Amount.Currency != state.Balance.Currency {
			return reject(ReasonCurrencyMismatch)
		}
		if _, err := addMinorUnits(state.Balance.MinorUnits, c.Amount.MinorUnits); err != nil {
			return reject(ReasonBalanceOverflow)
		}
		return accept([]AccountEvent{MoneyDeposited{Amount: c.Amount}})

	case WithdrawMoney:
		if state.Status != AccountOpen {
			return reject(ReasonNotOpen)
		}
		if !isPositiveMoney(c.Amount) {
			return reject(ReasonInvalidAmount)
		}
		if c.Amount.Currency != state.Balance.Currency {
			return reject(ReasonCurrencyMismatch)
		}
		if c.Amount.MinorUnits > state.Balance.MinorUnits {
			return reject(ReasonInsufficientFunds)
		}
		return accept([]AccountEvent{MoneyWithdrawn{Amount: c.Amount}})

	default:
		// isAccountCommand is unexported, so every real implementation is
		// declared in this file — reaching here means a new variant was
		// added without updating Decide: a programmer error, not a
		// business outcome, so it is safe to panic.
		panic(fmt.Sprintf("Decide: unhandled AccountCommand %T", cmd))
	}
}

// CorruptHistoryError reports that a known event could not have followed the
// current state during replay. A corrupted or mis-ordered event stream is a
// real operational occurrence a caller must handle — so this is a returned
// error, never a panic.
type CorruptHistoryError struct {
	State AccountStatus
	Event AccountEvent
}

func (e *CorruptHistoryError) Error() string {
	return fmt.Sprintf("corrupt account stream: %T cannot follow status %s", e.Event, e.State)
}

func corruptHistory(state AccountState, event AccountEvent) error {
	return &CorruptHistoryError{State: state.Status, Event: event}
}

// addMinorUnits adds a signed delta to a minor-units balance, guarding
// against integer overflow and a negative result — the accounting
// invariants a corrupted or buggy delta could otherwise violate silently.
func addMinorUnits(balance, delta int64) (int64, error) {
	result := balance + delta
	if delta > 0 && result < balance {
		return 0, errors.New("minor-units overflow")
	}
	if delta < 0 && result > balance {
		return 0, errors.New("minor-units underflow")
	}
	if result < 0 {
		return 0, errors.New("negative resulting balance")
	}
	return result, nil
}

func applyDelta(balance Money, deltaMinorUnits int64) (Money, error) {
	minorUnits, err := addMinorUnits(balance.MinorUnits, deltaMinorUnits)
	if err != nil {
		return Money{}, err
	}
	balance.MinorUnits = minorUnits
	return balance, nil
}

// Evolve applies a fact to the state. An event that is structurally known
// but cannot legally follow the current state (e.g. a second AccountOpened,
// or a withdrawal that overdraws) signals corrupt history rather than being
// silently ignored or panicking mid-replay.
func Evolve(state AccountState, event AccountEvent) (AccountState, error) {
	switch e := event.(type) {
	case AccountOpened:
		if state.Status != AccountUnopened {
			return state, corruptHistory(state, event)
		}
		return AccountState{Status: AccountOpen, Balance: Money{Currency: e.Currency}}, nil

	case MoneyDeposited:
		if state.Status != AccountOpen ||
			!isPositiveMoney(e.Amount) ||
			e.Amount.Currency != state.Balance.Currency {
			return state, corruptHistory(state, event)
		}
		balance, err := applyDelta(state.Balance, e.Amount.MinorUnits)
		if err != nil {
			return state, corruptHistory(state, event)
		}
		state.Balance = balance
		return state, nil

	case MoneyWithdrawn:
		if state.Status != AccountOpen ||
			!isPositiveMoney(e.Amount) ||
			e.Amount.Currency != state.Balance.Currency ||
			e.Amount.MinorUnits > state.Balance.MinorUnits {
			return state, corruptHistory(state, event)
		}
		balance, err := applyDelta(state.Balance, -e.Amount.MinorUnits)
		if err != nil {
			return state, corruptHistory(state, event)
		}
		state.Balance = balance
		return state, nil

	default:
		panic(fmt.Sprintf("Evolve: unhandled AccountEvent %T", event))
	}
}
```

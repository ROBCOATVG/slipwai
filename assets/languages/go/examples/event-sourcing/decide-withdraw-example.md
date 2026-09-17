```go
package eventsourcing

// WithdrawRejection is the closed set of reasons DecideWithdraw can refuse a
// withdrawal, modelled as a defined string type with constants rather than
// a raw string.
type WithdrawRejection string

const (
	WithdrawRejectionNotOpen           WithdrawRejection = "not-open"
	WithdrawRejectionInsufficientFunds WithdrawRejection = "insufficient-funds"
	WithdrawRejectionInvalidAmount     WithdrawRejection = "invalid-amount"
	WithdrawRejectionCurrencyMismatch  WithdrawRejection = "currency-mismatch"
)

// DecideWithdraw is the Decide slice for WithdrawMoney: it enforces that the
// account is open, the amount is a positive value in the account's own
// currency, and that the balance covers it.
func DecideWithdraw(cmd WithdrawMoney, state AccountState) Outcome[AccountEvent, WithdrawRejection] {
	if state.Status != AccountOpen {
		return Reject[AccountEvent, WithdrawRejection](WithdrawRejectionNotOpen)
	}
	if cmd.Amount.MinorUnits <= 0 {
		return Reject[AccountEvent, WithdrawRejection](WithdrawRejectionInvalidAmount)
	}
	if cmd.Amount.Currency != state.Balance.Currency {
		return Reject[AccountEvent, WithdrawRejection](WithdrawRejectionCurrencyMismatch)
	}
	if cmd.Amount.MinorUnits > state.Balance.MinorUnits {
		return Reject[AccountEvent, WithdrawRejection](WithdrawRejectionInsufficientFunds)
	}
	return Accept[AccountEvent, WithdrawRejection]([]AccountEvent{MoneyWithdrawn{Amount: cmd.Amount}})
}
```

```go
package hexagon

// deduct_balance.go — extracted pure function

type DeductOutcome int

const (
	DeductSucceeded DeductOutcome = iota
	DeductNonPositiveAmount
	DeductCurrencyMismatch
	DeductInsufficientBalance
)

// DeductResult is a business outcome, not an error — the pure rule below
// never panics or returns an error for an expected rejection.
type DeductResult struct {
	Outcome DeductOutcome
	User    User
}

// DeductBalance is a pure domain rule: no I/O, no panics for expected outcomes.
func DeductBalance(user User, amount Money) DeductResult {
	switch {
	case amount.MinorUnits <= 0:
		return DeductResult{Outcome: DeductNonPositiveAmount}
	case amount.Currency != user.Balance.Currency:
		return DeductResult{Outcome: DeductCurrencyMismatch}
	case amount.MinorUnits > user.Balance.MinorUnits:
		return DeductResult{Outcome: DeductInsufficientBalance}
	}

	updated := user
	updated.Balance = Money{
		MinorUnits: user.Balance.MinorUnits - amount.MinorUnits,
		Currency:   user.Balance.Currency,
	}
	return DeductResult{Outcome: DeductSucceeded, User: updated}
}
```

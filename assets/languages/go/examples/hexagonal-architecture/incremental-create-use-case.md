```go
package hexagon

import (
	"context"
	"fmt"
)

// deduct_user_balance.go — driving port + use case

// AuthenticatedPrincipal is opaque proof of authentication; the request body
// cannot select a user.
type AuthenticatedPrincipal struct {
	UserID string
}

type DeductUserBalanceCommand struct {
	Principal AuthenticatedPrincipal
	Amount    Money
}

type DeductUserBalanceOutcome int

const (
	DeductUserBalanceSucceeded DeductUserBalanceOutcome = iota
	DeductUserBalanceNotFound
	DeductUserBalanceConcurrentChange
	DeductUserBalanceNonPositiveAmount
	DeductUserBalanceCurrencyMismatch
	DeductUserBalanceInsufficientBalance
)

type DeductUserBalanceResult struct {
	Outcome DeductUserBalanceOutcome
	User    User
}

// ForDeductingUserBalances is the driving port this use case satisfies.
type ForDeductingUserBalances interface {
	DeductUserBalance(ctx context.Context, cmd DeductUserBalanceCommand) (DeductUserBalanceResult, error)
}

// UserBalanceDeduction wires the pure domain rule to the repository port.
type UserBalanceDeduction struct {
	UserRepo UserRepository
}

func (d *UserBalanceDeduction) DeductUserBalance(ctx context.Context, cmd DeductUserBalanceCommand) (DeductUserBalanceResult, error) {
	stored, found, err := d.UserRepo.FindByID(ctx, cmd.Principal.UserID)
	if err != nil {
		return DeductUserBalanceResult{}, fmt.Errorf("deduct user balance: %w", err)
	}
	if !found {
		return DeductUserBalanceResult{Outcome: DeductUserBalanceNotFound}, nil
	}

	domainResult := DeductBalance(stored.Value, cmd.Amount)
	switch domainResult.Outcome {
	case DeductNonPositiveAmount:
		return DeductUserBalanceResult{Outcome: DeductUserBalanceNonPositiveAmount}, nil
	case DeductCurrencyMismatch:
		return DeductUserBalanceResult{Outcome: DeductUserBalanceCurrencyMismatch}, nil
	case DeductInsufficientBalance:
		return DeductUserBalanceResult{Outcome: DeductUserBalanceInsufficientBalance}, nil
	}

	saveOutcome, err := d.UserRepo.Save(ctx, domainResult.User, stored.Version)
	if err != nil {
		return DeductUserBalanceResult{}, fmt.Errorf("deduct user balance: %w", err)
	}
	if saveOutcome == SaveOutcomeConflict {
		return DeductUserBalanceResult{Outcome: DeductUserBalanceConcurrentChange}, nil
	}

	return DeductUserBalanceResult{Outcome: DeductUserBalanceSucceeded, User: domainResult.User}, nil
}
```

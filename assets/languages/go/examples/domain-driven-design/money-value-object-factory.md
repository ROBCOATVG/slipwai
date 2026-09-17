```go
package ddd

import "errors"

type Currency string

const (
	CurrencyGBP Currency = "GBP"
	CurrencyUSD Currency = "USD"
	CurrencyEUR Currency = "EUR"
)

// ErrMoneyOverflow and ErrMoneyNegative signal an invariant violation -- a
// bug in calling code, not a user-input problem.
var (
	ErrMoneyOverflow = errors.New("money minor units overflow safe integer range")
	ErrMoneyNegative = errors.New("money cannot be negative")
)

// maxSafeInteger mirrors JavaScript's Number.MAX_SAFE_INTEGER so the same
// class of overflow bug is caught explicitly, rather than relying on the
// much wider range of Go's int64.
const maxSafeInteger = 1<<53 - 1

type Money struct {
	MinorUnits int64
	Currency   Currency
}

// NewMoney validates and constructs a Money. Untrusted input should be
// validated at the trust boundary before this is called; a non-nil error
// here signals an invariant violation (a bug), not invalid user input.
func NewMoney(minorUnits int64, currency Currency) (Money, error) {
	if minorUnits > maxSafeInteger || minorUnits < -maxSafeInteger {
		return Money{}, ErrMoneyOverflow
	}
	if minorUnits < 0 {
		return Money{}, ErrMoneyNegative
	}
	return Money{MinorUnits: minorUnits, Currency: currency}, nil
}
```

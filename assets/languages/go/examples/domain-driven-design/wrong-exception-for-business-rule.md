```go
package ddd

import "errors"

var ErrFundingClosed = errors.New("funding is closed")

// PledgeContribution (WRONG) panics for what should be an expected business
// outcome. The failure is invisible in the signature, and every caller must
// remember to recover — nothing forces them to handle it.
func PledgeContribution(occasion Occasion, eligibility Eligibility, pledge NewPledge) Occasion {
	if occasion.IsFundingClosed {
		panic(ErrFundingClosed)
	}
	// ...
	return occasion
}
```

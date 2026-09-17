```go
package ddd

import "fmt"

// HandlePledge (WRONG) wraps an error just to prepend a message — noise,
// not clarity, when the underlying error already carries enough context.
func HandlePledge(occasion Occasion, eligibility Eligibility, pledge NewPledge) error {
	_, err := PledgeContribution(occasion, eligibility, pledge)
	if err != nil {
		return fmt.Errorf("failed to pledge: %w", err)
	}
	return nil
}
```

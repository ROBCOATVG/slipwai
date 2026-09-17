```go
package eventsourcing

import "time"

// DepositMoneyAt is a deposit command carrying an explicit timestamp, so
// that Decide stays a pure function of its arguments — it must never read
// the wall clock itself.
type DepositMoneyAt struct {
	Amount Money
	At     time.Time
}
```

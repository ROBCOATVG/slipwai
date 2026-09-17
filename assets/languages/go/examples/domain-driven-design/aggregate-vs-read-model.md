```go
package ddd

import "time"

// Route (WRONG) lets query concerns leak into the aggregate.
type Route struct {
	ID            RouteID
	Locations     []Location
	AlarmCount    int        // read concern — doesn't support any invariant
	LastAlarmDate *time.Time // read concern — no command needs this
}

// VendingMachine (RIGHT) only has what commands need to enforce invariants.
type VendingMachine struct {
	ID                  VendingMachineID
	LocationID          LocationID
	Alarms              []Alarm // needed for the max-alarms invariant
	MaxConcurrentAlarms int     // the invariant itself
}

// AlarmSummaryView (RIGHT) is a read model that answers query-side
// questions independently of the aggregate.
type AlarmSummaryView struct {
	RouteID          RouteID
	TotalAlarms      int
	LastAlarmAt      *time.Time
	ActiveAlarmCount int
}
```

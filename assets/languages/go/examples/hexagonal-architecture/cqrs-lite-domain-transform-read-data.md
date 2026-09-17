```go
package reporting

import "time"

// UrgentWithinDays is the business rule for dashboard urgency: fewer days
// remaining than this counts as urgent.
const UrgentWithinDays = 30

// DashboardCard is the display-ready DTO for the dashboard view.
type DashboardCard struct {
	Title    string
	Emoji    string
	DaysAway int
	Savings  SavingsDisplay
	IsUrgent bool
}

// ToDashboardCard is a pure, provider-free transform: no ports, no I/O.
// DashboardRow is the raw joined row produced by the driven query adapter.
//
// IsUrgent is a genuine business rule — a threshold on days until the event
// — so it belongs in the hexagon. Cosmetic formatting is out of scope here;
// BuildSavingsDisplay is a separate concern left to the driving/UI edge.
func ToDashboardCard(row DashboardRow, now time.Time) DashboardCard {
	daysAway := int(row.EventDate.Sub(now).Hours() / 24)

	return DashboardCard{
		Title:    row.EventTitle,
		Emoji:    row.OccasionEmoji,
		DaysAway: daysAway,
		Savings:  BuildSavingsDisplay(row.SavedAmount, row.TargetAmount, now),
		IsUrgent: daysAway < UrgentWithinDays,
	}
}
```

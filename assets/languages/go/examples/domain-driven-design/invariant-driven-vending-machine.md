```go
package ddd

// Route (WRONG) is a relationship-driven aggregate mirroring the entity
// hierarchy. No invariant is enforced; its methods just manage associations.
type Route struct {
	ID        RouteID
	Locations []Location // why is this here?
	// AddLocation(...)          just manages a collection
	// AttachVendingMachine(...) just manages a relationship
	// AlarmCount()              a read concern leaking in
}

// VendingMachine (RIGHT) is its own aggregate, because alarms are the
// behavioral responsibility.
type VendingMachine struct {
	ID                  VendingMachineID
	LocationID          LocationID // reference by ID
	Alarms              []Alarm
	MaxConcurrentAlarms int // invariant: can't exceed this
}

type TriggerAlarmOutcome int

const (
	AlarmTriggered TriggerAlarmOutcome = iota
	MaxAlarmsReached
)

type TriggerAlarmResult struct {
	Outcome TriggerAlarmOutcome
	Machine VendingMachine
}

// TriggerAlarm is the invariant that justifies this aggregate.
func TriggerAlarm(machine VendingMachine, alarm NewAlarm) TriggerAlarmResult {
	activeAlarms := 0
	for _, a := range machine.Alarms {
		if a.Status == "active" {
			activeAlarms++
		}
	}
	if activeAlarms >= machine.MaxConcurrentAlarms {
		return TriggerAlarmResult{Outcome: MaxAlarmsReached}
	}

	next := make([]Alarm, len(machine.Alarms), len(machine.Alarms)+1)
	copy(next, machine.Alarms)
	next = append(next, Alarm{ID: alarm.ID, Status: alarm.Status})
	machine.Alarms = next
	return TriggerAlarmResult{Outcome: AlarmTriggered, Machine: machine}
}
```

```python
from dataclasses import dataclass, replace
from typing import Literal


# WRONG — relationship-driven aggregate mirrors the entity hierarchy.
# No invariant is enforced; its methods just manage associations.
@dataclass(frozen=True)
class Route:
    id: "RouteId"
    locations: tuple["Location", ...]  # Why is this here?
    # add_location(...)                further just manages a collection
    # attach_vending_machine(...)      further just manages a relationship
    # alarm_count                      a read concern leaking in


# RIGHT — VendingMachine is its own aggregate, because alarms are the
# behavioral responsibility.
@dataclass(frozen=True)
class VendingMachine:
    id: "VendingMachineId"
    location_id: "LocationId"       # Reference by ID
    alarms: tuple["Alarm", ...]
    max_concurrent_alarms: int       # Invariant: can't exceed this


@dataclass(frozen=True)
class AlarmTriggered:
    machine: VendingMachine


@dataclass(frozen=True)
class MaxAlarmsReached:
    reason: Literal["max-alarms-reached"] = "max-alarms-reached"


TriggerAlarmResult = AlarmTriggered | MaxAlarmsReached


# The invariant that justifies this aggregate:
def trigger_alarm(machine: VendingMachine, alarm: "NewAlarm") -> TriggerAlarmResult:
    active_alarms = [a for a in machine.alarms if a.status == "active"]
    if len(active_alarms) >= machine.max_concurrent_alarms:
        return MaxAlarmsReached()
    return AlarmTriggered(machine=replace(machine, alarms=machine.alarms + (alarm,)))
```

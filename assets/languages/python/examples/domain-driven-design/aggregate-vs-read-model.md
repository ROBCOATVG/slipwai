```python
from dataclasses import dataclass
from datetime import datetime


# WRONG — query concerns leaking into the aggregate.
@dataclass(frozen=True)
class Route:
    id: "RouteId"
    locations: tuple["Location", ...]
    alarm_count: int                  # Read concern — doesn't support any invariant
    last_alarm_date: datetime | None  # Read concern — no command needs this


# RIGHT — the aggregate only has what commands need to enforce invariants.
@dataclass(frozen=True)
class VendingMachine:
    id: "VendingMachineId"
    location_id: "LocationId"
    alarms: tuple["Alarm", ...]  # Needed for the max-alarms invariant
    max_concurrent_alarms: int    # The invariant itself


# RIGHT — a read model answers query-side questions independently.
@dataclass(frozen=True)
class AlarmSummaryView:
    route_id: "RouteId"
    total_alarms: int
    last_alarm_at: datetime | None
    active_alarm_count: int
```

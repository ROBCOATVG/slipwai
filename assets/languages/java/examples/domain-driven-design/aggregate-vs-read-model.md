```java
// Query concerns leaking into the aggregate. Neither field supports an invariant, and both have to be
// maintained on every write to satisfy a screen.
public record Route(
        RouteId id,
        List<Location> locations,
        int alarmCount,              // a read concern
        Instant lastAlarmAt) { }     // a read concern

// The aggregate holds only what a command needs in order to enforce a rule.
public record VendingMachine(
        VendingMachineId id, LocationId locationId, List<Alarm> alarms, int maxConcurrentAlarms) { }

// The read model answers the query side's questions independently, and can be rebuilt from events or
// recomputed from a join — because it is derived, not authoritative.
public record AlarmSummaryView(
        RouteId routeId, int totalAlarms, Instant lastAlarmAt, int activeAlarmCount) { }
```

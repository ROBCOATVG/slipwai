```java
// RELATIONSHIP-DRIVEN — the aggregate mirrors the entity diagram and enforces nothing. Every method just
// manages an association, and the read concern has crept in at the bottom.
public record Route(RouteId id, List<Location> locations) {
    public Route addLocation(Location location) { }

    public Route attachVendingMachine(VendingMachine machine) { }

    public int alarmCount() { }
}

// INVARIANT-DRIVEN — VendingMachine is its own aggregate because the alarm limit is a rule that has to be
// true at every instant, and the machine is the smallest thing that can guarantee it.
public record VendingMachine(
        VendingMachineId id,
        LocationId locationId,        // a reference, not the Location itself
        List<Alarm> alarms,
        int maxConcurrentAlarms) {    // the invariant

    public VendingMachine {
        alarms = List.copyOf(alarms);
    }

    /** The rule that justifies the aggregate boundary. */
    public TriggerAlarmResult trigger(Alarm alarm) {
        long active = alarms.stream().filter(Alarm::isActive).count();
        if (active >= maxConcurrentAlarms) {
            return new TriggerAlarmResult.Refused("max-alarms-reached");
        }
        List<Alarm> updated = new ArrayList<>(alarms);
        updated.add(alarm);
        return new TriggerAlarmResult.Triggered(
                new VendingMachine(id, locationId, updated, maxConcurrentAlarms));
    }
}
```

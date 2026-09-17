```typescript
// ❌ RELATIONSHIP-DRIVEN — aggregate mirrors entity hierarchy
//    No invariants enforced; methods just manage associations
type Route = {
  readonly id: RouteId;
  readonly locations: ReadonlyArray<Location>;  // Why is this here?
  readonly addLocation: ...;                     // Just manages a collection
  readonly attachVendingMachine: ...;            // Just manages a relationship
  readonly getAlarmCount: ...;                   // Read concern leaking in
};

// ✅ INVARIANT-DRIVEN — VendingMachine is its own aggregate
//    because alarms are the behavioral responsibility
type VendingMachine = {
  readonly id: VendingMachineId;
  readonly locationId: LocationId;              // Reference by ID
  readonly alarms: ReadonlyArray<Alarm>;
  readonly maxConcurrentAlarms: number;         // Invariant: can't exceed this
};

// The invariant that justifies this aggregate:
const triggerAlarm = (machine: VendingMachine, alarm: NewAlarm): TriggerAlarmResult => {
  const activeAlarms = machine.alarms.filter(a => a.status === 'active');
  if (activeAlarms.length >= machine.maxConcurrentAlarms) {
    return { success: false, reason: 'max-alarms-reached' };
  }
  return { success: true, machine: { ...machine, alarms: [...machine.alarms, alarm] } };
};
```

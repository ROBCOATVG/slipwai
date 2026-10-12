```typescript
// ❌ Query concerns leaking into the aggregate
type Route = {
  readonly id: RouteId;
  readonly locations: ReadonlyArray<Location>;
  readonly alarmCount: number;        // Read concern — doesn't support any invariant
  readonly lastAlarmDate: Date | null; // Read concern — no command needs this
};

// ✅ Aggregate only has what commands need for invariant enforcement
type VendingMachine = {
  readonly id: VendingMachineId;
  readonly locationId: LocationId;
  readonly alarms: ReadonlyArray<Alarm>;      // Needed for max-alarms invariant
  readonly maxConcurrentAlarms: number;        // The invariant itself
};

// ✅ Read model answers query-side questions independently
type AlarmSummaryView = {
  readonly routeId: RouteId;
  readonly totalAlarms: number;
  readonly lastAlarmAt: Date | null;
  readonly activeAlarmCount: number;
};
```

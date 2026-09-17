```typescript
// per-account (single-stream) read-model row — version is unique within it
type BalanceRow = { readonly balanceMinorUnits: number; readonly appliedThrough: number };

// idempotent apply: ignore any event at or below the version already applied
const project = (row: BalanceRow, event: { readonly amount: Money }, version: number): BalanceRow => {
  if (version <= row.appliedThrough) return row;
  const balanceMinorUnits = row.balanceMinorUnits + event.amount.minorUnits;
  if (!Number.isSafeInteger(row.balanceMinorUnits) ||
      !Number.isSafeInteger(event.amount.minorUnits) ||
      !Number.isSafeInteger(balanceMinorUnits)) throw new Error('Invalid projection money');
  return { balanceMinorUnits, appliedThrough: version };
};

it('should not double-count a redelivered event', () => {
  const event = { type: 'MoneyDeposited', amount: money(10_000) };

  const once = project({ balanceMinorUnits: 0, appliedThrough: 0 }, event, 1);
  const twice = project(once, event, 1); // the same event, redelivered at the same version

  expect(once.balanceMinorUnits).toBe(10_000);
  expect(twice.balanceMinorUnits).toBe(10_000); // not 20_000
});
```

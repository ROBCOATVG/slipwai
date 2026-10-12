```typescript
type Currency = 'GBP' | 'USD' | 'EUR';
type Money = { readonly minorUnits: number; readonly currency: Currency };

const createMoney = (minorUnits: number, currency: Currency): Money => {
  if (!Number.isSafeInteger(minorUnits)) throw new Error('Money minor units must be a safe integer');
  if (minorUnits < 0) throw new Error('Money cannot be negative');
  return { minorUnits, currency };
};
// Factory throws = invariant violation (a bug in calling code).
// Schemas catch invalid user input at trust boundaries BEFORE
// the factory is called. If the factory throws, something
// bypassed the schema.
```

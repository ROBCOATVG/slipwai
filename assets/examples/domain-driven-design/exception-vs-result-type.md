```typescript
// ✅ Exception — invariant violation means a bug
const createMoney = (minorUnits: number, currency: Currency): Money => {
  if (!Number.isSafeInteger(minorUnits)) throw new Error('Money minor units must be a safe integer');
  if (minorUnits < 0) throw new Error('Money cannot be negative');
  return { minorUnits, currency };
};

// ✅ Result type — expected business outcome
const pledgeContribution = (...): PledgeDecision => {
  if (!eligibility.mayPledge) {
    return { success: false, reason: 'contributor-ineligible' };
  }
  ...
};
```

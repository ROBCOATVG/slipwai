```typescript
// packages/billing/hexagon/domain/src/deduct-balance.ts — extracted pure function
type DeductResult =
  | { readonly success: true; readonly user: User }
  | { readonly success: false; readonly reason: 'non-positive-amount' | 'currency-mismatch' | 'insufficient-balance' };

const deductBalance = (user: User, amount: Money): DeductResult => {
  if (!Number.isSafeInteger(amount.minorUnits) || !Number.isSafeInteger(user.balance.minorUnits)) {
    throw new Error('Invalid Money invariant');
  }
  if (amount.minorUnits <= 0) {
    return { success: false, reason: 'non-positive-amount' };
  }
  if (amount.currency !== user.balance.currency) {
    return { success: false, reason: 'currency-mismatch' };
  }
  if (amount.minorUnits > user.balance.minorUnits) {
    return { success: false, reason: 'insufficient-balance' };
  }
  return {
    success: true,
    user: {
      ...user,
      balance: createMoney(user.balance.minorUnits - amount.minorUnits, user.balance.currency),
    },
  };
};
```

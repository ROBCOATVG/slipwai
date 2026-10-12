```typescript
type PledgeDecision =
  | { readonly success: true; readonly occasion: Occasion; readonly events: readonly PledgeRecorded[] }
  | { readonly success: false; readonly reason: 'contributor-ineligible' | 'non-positive-amount' | 'currency-mismatch' | 'exceeds-budget' | 'funding-closed' };

type PledgeResult =
  | PledgeDecision
  | { readonly success: false; readonly reason: 'not-found' | 'concurrent-change' }; // application outcomes
```

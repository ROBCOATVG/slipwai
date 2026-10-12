```typescript
// packages/gifting/hexagon/domain/src/types.ts
type OccasionId = string & { readonly __brand: 'OccasionId' };
type ContributorId = string & { readonly __brand: 'ContributorId' };
type PledgeId = string & { readonly __brand: 'PledgeId' };
type Currency = 'GBP' | 'USD' | 'EUR';
type Money = { readonly minorUnits: number; readonly currency: Currency };

const createMoney = (minorUnits: number, currency: Currency): Money => {
  if (!Number.isSafeInteger(minorUnits) || minorUnits < 0) throw new Error('Invalid money');
  return { minorUnits, currency };
};

type Occasion = {
  readonly id: OccasionId;
  readonly name: string;
  readonly budget: Money;
  readonly totalPledged: Money;
  readonly isFundingClosed: boolean;
};

type PledgeRecorded = {
  readonly type: 'PledgeRecorded';
  readonly id: PledgeId;
  readonly occasionId: OccasionId;
  readonly contributorId: ContributorId;
  readonly amount: Money;
};

type PledgeDecision =
  | {
      readonly success: true;
      readonly occasion: Occasion;
      readonly events: readonly PledgeRecorded[];
    }
  | { readonly success: false; readonly reason: 'non-positive-amount' | 'currency-mismatch' | 'exceeds-budget' | 'funding-closed' };
```

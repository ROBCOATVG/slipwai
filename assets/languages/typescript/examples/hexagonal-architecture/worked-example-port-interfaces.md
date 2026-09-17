```typescript
// packages/gifting/hexagon/application/src/pledging.ts — driving port + application result
type PledgeResult =
  | PledgeDecision
  | { readonly success: false; readonly reason: 'not-found' | 'concurrent-change' };

type StoredOccasion = {
  readonly value: Occasion;
  readonly version: number;
};

declare const authenticatedPledger: unique symbol;
type AuthenticatedPledger = {
  readonly [authenticatedPledger]: true;
  readonly contributorId: ContributorId;
};

interface ForPledgingToOccasions {
  readonly pledgeToOccasion: (dto: {
    readonly pledgeId: PledgeId;
    readonly occasionId: OccasionId;
    readonly principal: AuthenticatedPledger;
    readonly amount: Money;
  }) => Promise<PledgeResult>;
}

// packages/gifting/hexagon/application/src/pledge-persistence.ts
interface PledgePersistence {
  readonly findOccasionById: (id: OccasionId) => Promise<StoredOccasion | undefined>;
  readonly saveWithOutbox: (
    occasion: Occasion,
    events: readonly PledgeRecorded[],
    expectedVersion: number,
  ) => Promise<'saved' | 'conflict'>;
}

// packages/gifting/hexagon/application/src/pledge-projection.ts
interface PledgeProjection {
  // Input is a validated immutable log record: one ID permanently names one payload.
  readonly recordFrom: (event: PledgeRecorded) => Promise<void>;
}
```
